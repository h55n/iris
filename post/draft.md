# WORKING TITLE (name TBD - Baithak?): I take 6 meetings a day across 3 devices, so I built a notetaker that can't leak them

*(DEV submission draft - UNPUBLISHED. Fill remaining [SLOT]s before Hassan reviews.)*

## What I Built

[Name] is a local-first meeting notetaker for people whose meetings don't happen in one place. Phone call on the way in, a Google Meet at the desk, an in-person chat in the hallway - it records (when you tell it to), transcribes on your own machine with open-weight Whisper, and writes the notes with a local open-weight model. Recordings delete themselves after 7 days; transcripts and notes stay on your devices, encrypted, syncing only between hardware you own.

The part that makes it trustworthy: every decision and action item in the notes must quote the exact transcript lines it came from, with a timestamp. A small verifier checks every claim against the transcript before the note is saved. If the model invents a task or a name, the claim is demoted to an "unverified" section instead of silently becoming your to-do list.

## Demo

### 1. Ingest a meeting (54 seconds of audio, base model, CPU only)

```text
$ python3 convo/cli.py ingest standup.wav
meeting: 20261020-2337-d78dfa
backend: ultramarine (hosted fallback - dev sandbox has no GPU; on a laptop this is ollama/gemma3:4b, local)
integrity: {'checked': 6, 'passed': 6}
```

transcript.md (sentence-level, VAD segmentation):
```text
[00:14] We shipped the Android recorder on Friday.
[00:23] Priya will own the sync server. And it should only move transcripts and notes. Never the audio.
[00:31] We also decided recordings delete themselves after seven days. Transcripts stay local only.
[00:39] I will write the retention sweep tonight.
[00:48] Hassan tests the Hindi transcript on his phone before we post anything.
```

notes.md (every claim carries its receipt):
```text
## Decisions
- Recordings delete themselves after seven days, and transcripts stay local only.
  > "We also decided recordings delete themselves after seven days. Transcripts stay local only." [00:31]

## Action items
- [ ] Own the sync server, moving only transcripts and notes (never audio). (Priya)
  > "Priya will own the sync server. And it should only move transcripts and notes. Never the audio." [00:23]

_integrity: 6/6 claims verified against transcript_
```

### 2. The verifier catching the model inventing a person (live, unscripted)

I told the notes model to always assign an owner, inventing one if unclear - the thing every notes AI does quietly. Two runs, two invented people ("Sam", then "Alex") - each attached to a quote that really is in the transcript, so quote-checking alone passed them. The verifier now checks owners too:

```text
integrity: {'checked': 5, 'passed': 4}
DEMOTED: Alex -> owner not mentioned in transcript
```

The invented task does not make it into your to-do list. It lands in an "unverified" section, with the reason.

### 3. Retention sweep

```text
$ python3 convo/cli.py sweep
deleted store/20261013-0915-a1b2c3/audio.wav     # 8 days old
# transcript.md and notes.md for the same meeting: untouched
```

[SCREENSHOT: same notes file synced on phone + laptop]

## Code

[REPO LINK - private until Hassan approves]

## Why open innovation matters for this build

Meetings are the most private audio most people produce: client names, salaries, health, unreleased plans. The dominant notetakers (Otter, Fireflies) work by uploading that audio to someone else's cloud. [Name] exists because the models are open: Whisper's weights are MIT, Gemma's are open, so the whole pipeline - record, transcribe, summarize - runs where the audio already is. No vendor to trust, no per-minute bill, works on a plane. [Also honest: iOS 18 call recording, Pixel Recorder and Galaxy AI each do pieces of this, but only inside their own silo - open models are what let one archive span an Android phone, a Linux laptop and everything between.]

## The honest limits (tested vs untested)

Read the demo transcript above again: the speaker said "we ship on Friday" and Whisper heard "we shipped". The verifier passed that line - correctly, because the quote really is in the transcript - but the transcript itself misheard. That is the honest limit of this design: the integrity pass stops the MODEL from inventing things; it cannot stop the EARS from mishearing. Also real, also unfixed today: no speaker labels yet, Hindi needs the small multilingual model (base translates instead of transcribing - tested), and mixed Hindi-English audio needs per-segment language detection. Full list in TESTED.md in the repo.

## Prize Categories

- Best Use of Gemma - notes written by gemma3:4b running locally via Ollama
- Best Use of Ultramarine - hosted fallback notes backend ($X.XX spent, Y runs)
- Best Use of Temporal - [if it lands: durable ingest pipeline]
- Best Use of MongoDB Atlas - [if it lands: sync store]
- Best Use of a .tech Domain - [demo page if deployed]

*Built with: whisper.cpp (MIT), Whisper tiny/base/small (MIT), Gemma 3 via Ollama, Python. License: MIT.*
