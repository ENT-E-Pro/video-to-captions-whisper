"""Apify Actor entrypoint: Video/Audio to Captions (faster-whisper, CPU), pay-per-event."""
import asyncio, json, os, tempfile, uuid
import httpx
from apify import Actor
from .core import (probe, extract_audio, transcribe, build_cues, to_srt, to_vtt, to_txt, billable_minutes,
                   TranscriptionError, MODELS)

MAX_DOWNLOAD = 2 * 1024**3
HQ_MODELS = {"large-v3-turbo"}


async def download(url: str, dest: str) -> None:
    if not str(url).startswith(("http://", "https://")):
        raise TranscriptionError("url must be an http(s) URL")
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as c:
        async with c.stream("GET", url) as r:
            r.raise_for_status()
            n = 0
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes(1 << 20):
                    n += len(chunk)
                    if n > MAX_DOWNLOAD:
                        raise TranscriptionError("File larger than 2 GB limit")
                    f.write(chunk)


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}
        files = list(inp.get("files") or [])
        if inp.get("url"):
            files.append({"url": inp["url"]})
        if not files:
            raise ValueError("Provide 'url' or 'files' [{url, ...}]")
        keys = ["model", "language", "task", "maxCharsPerLine", "maxLinesPerCue", "maxCueSeconds", "wordsPerCue",
                "vadFilter", "beamSize", "initialPrompt", "startSeconds", "durationSeconds", "txtTimestamps"]
        defaults = {"model": "small", "language": "auto", "task": "transcribe", "maxCharsPerLine": 42, "maxLinesPerCue": 2,
                    "maxCueSeconds": 6, "wordsPerCue": None, "vadFilter": True, "beamSize": 5, "initialPrompt": None,
                    "startSeconds": None, "durationSeconds": None, "txtTimestamps": False}
        defaults.update({k: inp[k] for k in keys if inp.get(k) is not None})
        max_dur = float(inp.get("maxDurationSeconds", 10800))
        kvs = await Actor.open_key_value_store()
        for item in files:
            item = item if isinstance(item, dict) else {"url": item}
            o = {**defaults, **{k: v for k, v in item.items() if v is not None and k in keys}}
            url = item.get("url")
            row = {"sourceUrl": url, "model": o["model"], "task": o["task"]}
            with tempfile.TemporaryDirectory() as td:
                try:
                    if o["model"] not in MODELS:
                        raise TranscriptionError(f"Unknown model '{o['model']}'. Use one of: {', '.join(MODELS)}")
                    src = os.path.join(td, "input")
                    await download(url, src)
                    info = probe(src)
                    if not info["audio"]:
                        raise TranscriptionError("Input has no audio stream")
                    eff = info["duration"] or 0
                    if o["startSeconds"]:
                        eff = max(0, eff - float(o["startSeconds"]))
                    if o["durationSeconds"]:
                        eff = min(eff, float(o["durationSeconds"])) if eff else float(o["durationSeconds"])
                    if eff > max_dur:
                        raise TranscriptionError(f"Audio to transcribe is {eff:.0f}s, above maxDurationSeconds={max_dur:.0f}; trim with durationSeconds")
                    wav = os.path.join(td, "a.wav")
                    await asyncio.to_thread(extract_audio, src, wav, o["startSeconds"], o["durationSeconds"])
                    eff = probe(wav)["duration"] or eff
                    Actor.log.info(f"Transcribing {eff:.0f}s with model={o['model']}")
                    t = await asyncio.to_thread(transcribe, wav, o["model"], o["language"], o["task"], bool(o["vadFilter"]),
                                                int(o["beamSize"]), o["initialPrompt"], True)
                    off = float(o["startSeconds"] or 0)
                    if off:  # timestamps relative to the original file
                        for s in t.segments:
                            s["start"] = round(s["start"] + off, 3); s["end"] = round(s["end"] + off, 3)
                            for w in s["words"]:
                                w["start"] = round(w["start"] + off, 3); w["end"] = round(w["end"] + off, 3)
                    cues = build_cues(t.segments, int(o["maxCharsPerLine"]), int(o["maxLinesPerCue"]), float(o["maxCueSeconds"]),
                                      int(o["wordsPerCue"]) if o["wordsPerCue"] else None)
                    base = uuid.uuid4().hex[:12]
                    text = to_txt(t.segments, bool(o["txtTimestamps"]))
                    payload = {"language": t.language, "languageProbability": t.language_probability, "durationSeconds": eff,
                               "model": o["model"], "task": o["task"], "segments": t.segments, "cues": cues}
                    outs = {"srt": (to_srt(cues), "application/x-subrip"), "vtt": (to_vtt(cues), "text/vtt"),
                            "txt": (text, "text/plain; charset=utf-8"), "json": (json.dumps(payload, ensure_ascii=False), "application/json")}
                    for ext, (body, mime) in outs.items():
                        k = f"{base}.{ext}"
                        await kvs.set_value(k, body.encode("utf-8"), content_type=mime)
                        row[f"{ext}Url"] = await kvs.get_public_url(k)
                    minutes = billable_minutes(eff)
                    row.update(status="ok", language=t.language, languageProbability=t.language_probability,
                               durationSeconds=round(eff, 2), segmentCount=len(t.segments), cueCount=len(cues),
                               wordCount=sum(len(s["text"].split()) for s in t.segments),
                               text=text if len(text) < 200_000 else text[:200_000] + "…(truncated; see txtUrl)",
                               input=info, billedMinutes=minutes)
                    if not t.segments:  # nothing transcribed: free, distinct status
                        row.update(status="no-speech", billedMinutes=0,
                                   warning="No speech detected; not charged")
                        await Actor.push_data(row)
                        continue
                    hq = o["model"] in HQ_MODELS
                    await Actor.charge(event_name="transcript-created", count=1)
                    r = await Actor.charge(event_name="audio-minute-hq" if hq else "audio-minute", count=minutes)
                    await Actor.push_data(row)
                    if getattr(r, "event_charge_limit_reached", False):
                        Actor.log.info("Spending limit reached; stopping.")
                        break
                except Exception as e:  # never-fail: error rows are free
                    row.update(status="error", error=str(e)[:500])
                    await Actor.push_data(row)
