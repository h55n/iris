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
