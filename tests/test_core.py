import os, subprocess, pytest
from src.core import (build_cues, to_srt, to_vtt, to_txt, ts, wrap, extract_audio, probe, transcribe,
                      TranscriptionError, billable_minutes, cpu_threads)

SENT = "Hello world. This is a caption test for the video converter. The quick brown fox jumps over the lazy dog."


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("m")
    speech = str(d / "speech.wav"); video = str(d / "speech.mp4"); bad = str(d / "bad.bin"); silent = str(d / "silent.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"flite=text='{SENT}':voice=slt", "-ar", "22050", speech], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15", "-i", speech,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", video], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10", "-t", "2", "-c:v", "libx264", silent], check=True)
    open(bad, "wb").write(os.urandom(2048))
    return locals()


def words(text, start=0.0, step=0.4):
    out, t = [], start
    for w in text.split():
        out.append({"word": " " + w, "start": round(t, 2), "end": round(t + step * 0.9, 2)}); t += step
    return out


def test_ts():
    assert ts(3661.5) == "01:01:01,500" and ts(0.0012, ".") == "00:00:00.001"


def test_wrap():
    assert wrap("aaa bbb ccc ddd", 7, 2) == "aaa bbb\nccc ddd"
    assert wrap("one", 42, 2) == "one"


def test_cues_respect_limits():
    seg = {"start": 0, "end": 20, "text": SENT * 2, "words": words(SENT * 2)}
    cues = build_cues([seg], max_chars=20, max_lines=2, max_cue_seconds=4)
    assert len(cues) > 3
    for c in cues:
        assert all(len(l) <= 20 or " " not in l for l in c["text"].split("\n"))
        assert len(c["text"].split("\n")) <= 2 and c["end"] - c["start"] <= 4.01
    assert all(cues[i]["end"] <= cues[i + 1]["start"] for i in range(len(cues) - 1))


def test_words_per_cue_and_no_words_fallback():
    seg = {"start": 0, "end": 5, "text": "a b c d e", "words": words("a b c d e")}
    assert [c["text"] for c in build_cues([seg], words_per_cue=2)] == ["a b", "c d", "e"]
    assert build_cues([{"start": 1, "end": 2, "text": " hi ", "words": []}])[0]["text"] == "hi"


def test_formats():
    cues = [{"start": 0, "end": 1.5, "text": "Hi"}, {"start": 2, "end": 3, "text": "There"}]
    srt, vtt = to_srt(cues), to_vtt(cues)
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,500\nHi\n") and "2\n00:00:02,000" in srt
    assert vtt.startswith("WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nHi")
    segs = [{"start": 0, "end": 1, "text": "A."}, {"start": 1.2, "end": 2, "text": "B."}, {"start": 6, "end": 7, "text": "C."}]
    assert to_txt(segs) == "A. B.\n\nC.\n"
    assert to_txt(segs, True).startswith("[00:00:00] A.")


def test_billing_and_threads(monkeypatch):
    assert billable_minutes(59) == 1 and billable_minutes(121) == 3
    monkeypatch.setenv("ACTOR_MEMORY_MBYTES", "4096"); assert cpu_threads() == 1
    monkeypatch.setenv("ACTOR_MEMORY_MBYTES", "8192"); assert cpu_threads() == min(2, os.cpu_count())


def test_extract_and_errors(media, tmp_path):
    wav = str(tmp_path / "a.wav")
    extract_audio(media["video"], wav, start=1, duration=2)
    p = probe(wav)
    assert p["audio"]["sampleRate"] == 16000 and p["audio"]["channels"] == 1 and 1.8 < p["duration"] < 2.2
    with pytest.raises(TranscriptionError): probe(media["bad"])
    with pytest.raises(TranscriptionError): extract_audio(media["silent"], str(tmp_path / "x.wav"))
    with pytest.raises(TranscriptionError): transcribe(wav, model="gigantic")


@pytest.mark.slow
def test_transcribe_tiny_end_to_end(media, tmp_path):
    wav = str(tmp_path / "s.wav")
    extract_audio(media["video"], wav)
    t = transcribe(wav, model=os.environ.get("TEST_MODEL", "tiny"))
    assert t.language == "en"
    text = " ".join(s["text"] for s in t.segments).lower()
    assert "fox" in text and "dog" in text, text
    cues = build_cues(t.segments)
    assert cues and to_srt(cues).count("-->") == len(cues)
    t2 = transcribe(wav, model="tiny", language="en", word_timestamps=False)
    assert t2.segments and not t2.segments[0]["words"]
