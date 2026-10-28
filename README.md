# Video to Captions (SRT, VTT, TXT) - Whisper AI

Video to SRT, VTT and plain-text transcripts in one API call: send a video or audio URL and ENT-E's Whisper transcription API returns ready-to-upload caption files with word-level timestamps in 99 languages. Nothing to install and no API key from a third party.

## Video to SRT and VTT subtitles with a Whisper transcription API

Each file gives you four downloads:
- an `.srt` file for YouTube, Premiere, DaVinci Resolve or any editor
- a `.vtt` file for HTML5 players
- a clean `.txt` transcript that's ready for an LLM
- a `.json` file with every segment and word, with start/end times and confidence

The transcript text is also returned in the dataset row, so an agent can read it without downloading anything.

Captions are line-broken for reading out of the box: 42 characters per line, 2 lines per cue and at most 6 s per cue. Every setting is adjustable, down to 1–4 words per cue for TikTok-style pop-on captions.

## What you get

- **Auto captions API for any media URL.** MP4, MOV, MKV, WebM, MP3, WAV, M4A and anything else FFmpeg reads, up to 2 GB.
- **Whisper models** run with faster-whisper. Pick by speed or accuracy:
  - `tiny`, `base` and `small` (the default), at the standard rate.
  - English-only variants `tiny.en`, `base.en` and `small.en`.
  - `large-v3-turbo` for accented, noisy, technical or non-English speech, at the HQ rate.
- **Auto language detection** (or set `language` to an ISO 639-1 code such as `en`, `es`, `de`), and **translate to English** with `"task": "translate"`.
- **Trim before you pay.** `startSeconds` and `durationSeconds` transcribe only the part you need. Timestamps stay relative to the original file, so the captions still line up.
- **Voice-activity filter** (`vadFilter`, on by default). It skips silence and music, so Whisper doesn't invent text there.
- **Vocabulary hints.** `initialPrompt` helps the model spell names of products, brands and jargon.
- **Batch** with `files`, with per-file overrides.
- **Failed files are free.**

## Use cases

### Video to SRT for YouTube uploads

```json
{
  "url": "https://example.com/videos/launch-keynote.mp4",
  "language": "en"
}
```

Upload `srtUrl` as the subtitle track. Setting `language` explicitly is faster than auto-detect and avoids misdetection on short clips.

### VTT subtitles for a web player

```json
{
  "url": "https://example.com/videos/onboarding-01.mp4",
  "maxCharsPerLine": 37,
  "maxLinesPerCue": 2
}
```

Use `vttUrl` in an HTML5 `<track>` element.

### Word-level timestamps for editing, search and short-form captions

The `.json` output lists every word with `start`, `end` and confidence. For bold one-to-three-word captions:

```json
{
  "url": "https://example.com/clips/interview-cut.mp4",
  "wordsPerCue": 3,
  "maxLinesPerCue": 1,
  "maxCueSeconds": 2
}
```

### Transcribe video API for LLM pipelines (RAG, summaries, show notes)

```json
{
  "url": "https://example.com/podcast/ep-88.mp3",
  "model": "small",
  "txtTimestamps": false
}
```

Read `text` from the row, or fetch `txtUrl`. The text is in clean paragraphs that break after pauses longer than 2 s. Set `"txtTimestamps": true` for `[HH:MM:SS]` lines.

### Whisper transcription API for hard audio, with English translation

```json
{
  "url": "https://example.com/videos/field-report-es.mp4",
  "model": "small",
  "task": "translate",
  "initialPrompt": "ENT-E, Kubernetes, PyTorch, Acme Robotics"
}
```

`translate` outputs English captions for non-English speech. Use it with `tiny`, `base` or `small`; the English-only models and `large-v3-turbo` aren't trained for it. For the best same-language accuracy on noisy, accented or technical audio, use `"model": "large-v3-turbo"`.

### Batch captions for a course or channel back catalog

```json
{
  "model": "small",
  "language": "en",
  "files": [
    "https://example.com/course/lesson-01.mp4",
    "https://example.com/course/lesson-02.mp4",
    { "url": "https://example.com/course/lesson-03.mp4", "startSeconds": 30, "durationSeconds": 600 }
  ]
}
```

## Pricing (pay per event)

| Event | Price |
|---|---|
| Transcript created (per successful file) | $0.005 |
| Audio minute: `tiny`, `base`, `small` and `.en` models (per started minute transcribed) | $0.02 |
| Audio minute HQ: `large-v3-turbo` (per started minute, **instead of** the standard rate) | $0.06 |
| Actor start (per run, one event per GB of memory, minimum one; default 4 GB = 4 events) | $0.00005 per event |

There are no platform usage fees on top. Failed files are free.

**Worked example: captions for a 9 min 40 s video**
- The video is 580 s, which is 10 started minutes.
- With `small`: $0.005 + 10 × $0.02 = **$0.205**.
- With `large-v3-turbo`: $0.005 + 10 × $0.06 = **$0.605**.

**A one-hour podcast:** $0.005 + 60 × $0.02 = **$1.205** with `small`, or **$3.605** with `large-v3-turbo`.

**Trim to save:** captioning only a 2-minute highlight (`"startSeconds": 1200, "durationSeconds": 120`) costs $0.005 + 2 × $0.02 = **$0.045**.

Billing counts **started** minutes of the audio that's actually transcribed: the trimmed range if you set one, otherwise the whole file. It rounds up, ignoring up to 0.5 s of padding, with a minimum of 1. Files with no detected speech are free. Set a spending limit on the run to cap the total.

## Input reference

| Field | Type | Default | Notes |
|---|---|---|---|
| `url` | string | (none) | Direct link to a video or audio file, up to 2 GB |
| `files` | array | (none) | Batch. Items are `{ "url": ..., <any setting below> }` or plain URL strings. |
| `model` | string | `small` | `tiny`, `base`, `small`, `large-v3-turbo` (HQ rate), `tiny.en`, `base.en`, `small.en` |
| `language` | string | `auto` | ISO 639-1 code or `auto` (detected from the first 30 s) |
| `task` | string | `transcribe` | `transcribe` or `translate` (to English) |
| `startSeconds` | number | (none) | Start of the range to transcribe |
| `durationSeconds` | number | (none) | Length of the range to transcribe (min 1) |
| `maxCharsPerLine` | integer | `42` | 10–120 |
| `maxLinesPerCue` | integer | `2` | 1–4 |
| `maxCueSeconds` | number | `6` | 1–30 |
| `wordsPerCue` | integer | (none) | 1–20, a fixed number of words per caption |
| `vadFilter` | boolean | `true` | Skip non-speech |
| `beamSize` | integer | `5` | 1–10. Higher is slightly more accurate but slower. |
| `initialPrompt` | string | (none) | Vocabulary and spelling hints |
| `txtTimestamps` | boolean | `false` | Adds `[HH:MM:SS]` lines to the `.txt` |
| `maxDurationSeconds` | integer | `10800` | Longer audio is rejected (free). Trim with `durationSeconds`. |

You must provide either `url` or `files`.

## Output reference

Each file produces one dataset row (URLs and text shortened):

```json
{
  "sourceUrl": "https://example.com/videos/launch-keynote.mp4",
  "model": "small",
  "task": "transcribe",
  "srtUrl": "https://api.apify.com/v2/key-value-stores/<storeId>/records/d6a78644e2db.srt?signature=<sig>",
  "vttUrl": "https://api.apify.com/v2/key-value-stores/<storeId>/records/d6a78644e2db.vtt?signature=<sig>",
  "txtUrl": "https://api.apify.com/v2/key-value-stores/<storeId>/records/d6a78644e2db.txt?signature=<sig>",
  "jsonUrl": "https://api.apify.com/v2/key-value-stores/<storeId>/records/d6a78644e2db.json?signature=<sig>",
  "status": "ok",
  "language": "en",
  "languageProbability": 0.996,
  "durationSeconds": 580.17,
  "segmentCount": 162,
  "cueCount": 210,
  "wordCount": 1812,
  "text": "Welcome to the launch. Today we are going to walk through…",
  "input": { "format": "mov,mp4,m4a,3gp,3g2,mj2", "duration": 580.125, "sizeBytes": 57432329, "video": { "codec": "h264", "width": 854, "height": 480 }, "audio": { "codec": "aac", "sampleRate": 44100, "channels": 2 } },
  "billedMinutes": 10
}
```

`text` is capped at 200,000 characters in the row; the full transcript is always in `txtUrl`. If no speech is found (silence or music only), the row has `status: "no-speech"`, `billedMinutes: 0` and a `warning`, and **nothing is charged**. A failed file returns `sourceUrl`, `model`, `task`, `status: "error"` and `error`. The Output tab also has a "text" view with only `sourceUrl`, `language` and `text`.

## Use it from AI agents and automations

**MCP (Claude, Cursor, other MCP clients).** Add `https://mcp.apify.com?tools=ent-e/video-to-captions-whisper` as a remote MCP server and sign in with OAuth. The agent calls the Actor with a URL, then reads `text` from the dataset, or passes `srtUrl` to the next step. With `small` at the default memory, a 9.7-minute video took about 6 minutes to transcribe in testing, so the agent should wait for the run to finish before reading results.

**n8n.** Use the Apify node (`@apify/n8n-nodes-apify`):
- **Run an Actor and get dataset** for short clips.
- For longer files, use **Run an Actor** followed by **Get Dataset Items**.

**Make.** Use the Apify app:
- **Run an Actor** with *Run synchronously* waits up to 120 s, which suits short clips.
- For longer videos, use the **Watch Actor Runs** trigger, then **Get Dataset Items**.

**Zapier.** Use the Apify app:
- **Run Actor and Fetch Results** for runs under 5 minutes.
- Otherwise, use **Run Actor**, then the **Finished Actor Run** trigger and **Fetch Dataset Items**.

**API.**

```bash
curl -X POST "https://api.apify.com/v2/acts/ent-e~video-to-captions-whisper/runs?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/videos/launch-keynote.mp4","language":"en"}'
# then: GET https://api.apify.com/v2/datasets/<defaultDatasetId>/items?token=$APIFY_TOKEN
```

Short clips can use `/run-sync-get-dataset-items`, which waits up to 5 minutes.

## FAQ

**Can I paste a YouTube or TikTok page link?**
No. The Actor needs a direct link to the media file itself (for example a `.mp4` or `.mp3` in cloud storage, a CDN or a file host). To get audio out of something else first, use [Media Converter (FFmpeg)](https://apify.com/ent-e/media-converter-ffmpeg) on the direct file.

**Which model should I pick?**
- Start with `small`.
- Use `tiny` or `base` for fast rough drafts.
- Use `large-v3-turbo` for accents, noise, crosstalk, technical terms or non-English speech. It costs three times as much per minute and gives the most accurate same-language captions.

**Does it label speakers?**
No, there's no speaker diarization. You get timed text, not "Speaker 1 / Speaker 2."

**Are the timestamps accurate enough for word-by-word captions?**
Every word in the `.json` output has its own start and end time and a confidence value. Use `wordsPerCue` (1–4) for pop-on captions, or feed the JSON to your own renderer. Or let [Video to Shorts](https://apify.com/ent-e/video-to-shorts-captions) burn them in for you.

**How do I cut cost on long videos?**
- Transcribe only the part you need with `startSeconds` + `durationSeconds`. You're billed for that range only.
- Stay on `small` unless you need `large-v3-turbo`.

**How many languages?**
Whisper covers 99 languages, with auto-detect or a fixed `language` code. Accuracy varies by language and audio quality, so use `large-v3-turbo` for harder languages.

**Am I charged if a file fails?**
No. Download errors, unreadable files and over-length files return a free error row.

## ENT-E media toolkit

Every tool takes a public file URL, needs nothing installed, charges per file, doesn't charge for failures, and works from MCP, n8n, Make, Zapier and the API.

- **[Media Converter for AI Agents (FFmpeg)](https://apify.com/ent-e/media-converter-ffmpeg)**: audio/video to MP3, Whisper-ready 16 kHz WAV, MP4, WebM, GIF or thumbnails, with trim and batch.
- **[Image Converter & Compressor](https://apify.com/ent-e/image-converter-compressor)**: convert to WebP or AVIF, compress to a target file size, resize, strip EXIF/GPS.
- **[Podcast Loudness Normalizer](https://apify.com/ent-e/podcast-loudness-normalizer)**: normalize to -16, -14, -23 or -24 LUFS with a true-peak ceiling, plus a before/after report.
- **[Video to Captions](https://apify.com/ent-e/video-to-captions-whisper)**: SRT, VTT, TXT and word-level JSON from any video or audio URL, with Whisper.
- **[Video to Shorts](https://apify.com/ent-e/video-to-shorts-captions)**: vertical 9:16 clips with burned-in animated captions for TikTok, Reels and Shorts.
