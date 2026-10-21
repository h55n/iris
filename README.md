# convo (working name)

Private, local-first meeting notes. Records when you tell it to, transcribes on your
own machine, writes notes you can trust, deletes the audio after a week.

- **Local transcription** - whisper.cpp (tiny/base/small, English + Hindi tested)
- **Notes with receipts** - every decision and action item quotes the exact transcript
  lines it came from, with a timestamp. A verifier checks each claim; anything the
  model invented (a task, a name, a quote) is demoted to "unverified" instead of
  landing silently in your to-do list.
- **Recording retention** - audio auto-deletes after 7 days; transcripts and notes stay.
- **Local-first notes** - default backend is Ollama (gemma3:4b) on your machine;
  a hosted fallback exists for machines too small to run a model.
- **Sync without audio** - a tiny self-hostable server moves transcripts/notes/meta
  between your devices. Recordings never leave the device they were made on.

## Run it

```sh
# build whisper.cpp
git clone --depth 1 https://github.com/ggml-org/whisper.cpp vendor/whisper.cpp
cd vendor/whisper.cpp && cmake -B build && cmake --build build -j --config Release && cd ../..

# models (English)
curl -L -o models/ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
curl -L -o models/ggml-silero-v6.2.0.bin https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin
# Hindi / multilingual: ggml-small.bin from the same repo (see TESTED.md for why not base)

# notes backend (default, local): ollama pull gemma3:4b
python3 convo/cli.py ingest meeting.wav                      # local notes
python3 convo/cli.py ingest meeting.wav --backend ultramarine  # hosted fallback
python3 convo/cli.py sweep                                   # delete >7-day recordings
python3 convo/cli.py list
python3 convo/cli.py sync --server http://YOUR-SERVER:8471   # sync notes between devices

# sync server (self-host, stdlib only)
python3 convo/sync_server.py --dir syncdata --token S3CRET --port 8471
```

## Layout

- `convo/transcribe.py` - whisper.cpp wrapper (VAD sentence segmentation)
- `convo/backends.py` - notes backends (ollama default, hosted fallback)
- `convo/verify.py` - integrity pass (evidence quotes + timestamps + owner names)
- `convo/store.py` - local meeting store + 7-day recording retention
- `convo/sync.py` / `convo/sync_server.py` - device sync (never audio)
- `convo/record.py` - laptop mic capture
- `tests/` - `python3 tests/test_engine.py`
- `TESTED.md` - what is actually tested vs untested, honestly

License: MIT.


## Components

| piece | file | what it does |
|---|---|---|
| CLI | `convo/cli.py` | ingest / sweep / list / sync / key / encrypt / read / export / share |
| transcription | `convo/transcribe.py` | whisper.cpp + silero VAD, sentence timestamps |
| notes backends | `convo/backends.py` | Ollama gemma3:4b (local default) or Ultramarine (hosted fallback) |
| claim verifier | `convo/verify.py` | every decision/action item must quote the transcript; invented claims demoted |
| retention | `convo/store.py` | recordings auto-delete after 7 days; transcripts/notes stay |
| encryption | `convo/crypto.py` | age X25519 at rest; key at ~/.convo/key.txt (600) |
| sync | `convo/sync.py` + `sync_server.py` | tiny self-hostable relay; moves ciphertext, NEVER audio |
| LAN ingest | `convo/ingest_server.py` | phone posts recordings to your own laptop for transcription |
| speaker labels | `convo/diarize.py` | sherpa-onnx: pyannote-seg + ERes2Net, `ingest --diarize` |
| meeting detect | `convo/detect.py` | laptop: Zoom/Meet/Teams/Webex via process+window+mic signals, debounced |
| local web UI | `convo/webui.py` | browse meetings at 127.0.0.1:8473 (localhost only, serves decrypted content) |
| Android app | `android/` | recorder, meeting nudges, relay sync, on-device age decryption |
| DEV post draft | `post/draft.md` | Hacktoberfest Week 3 submission (unpublished) |

## Quick start

```
python3 convo/cli.py key init                 # one-time: encryption key
python3 convo/cli.py ingest meeting.wav       # record/transcribe/verify/encrypt
python3 convo/webui.py                        # browse at 127.0.0.1:8473
python3 convo/sync_server.py --token T &      # relay (your own box)
python3 convo/cli.py sync --server http://... # move notes between devices
```
