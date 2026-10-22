# Test Iris on your phone and laptop

Set up (laptop, once):
1. `python3 iris/cli.py doctor` and fix what it flags (ffmpeg, whisper model, age).
2. `python3 iris/cli.py key init`
3. Start the receiver the phone talks to: `python3 iris/ingest_server.py --token S3CRET --port 8472` and note the laptop's LAN IP.
4. Open the web UI: `python3 iris/webui.py`, then http://127.0.0.1:8473

Phone:
1. Download the APK from the latest GitHub release, install it (allow unknown apps).
2. Enter the laptop address and token, tap Record, say a few sentences, stop, tap Send.
3. Confirm: the meeting shows up in the web UI with a transcript and notes with receipts.
4. Paste your age key on the phone and check notes decrypt there.

Checks that only a real device can answer (not tested by us):
- [ ] Mic recording quality and the always-visible notification
- [ ] Meeting nudge via Usage Access
- [ ] Upload over your Wi-Fi
- [ ] Hindi/English mix ("Hinglish") transcript on real speech
- [ ] Naming a speaker (`iris enroll Name sample.wav`, or click a speaker chip in the web UI)
- [ ] Web UI at phone width (390px), tablet (~820px) and laptop; light and dark
- [ ] Folders, pins, drag reorder, Ctrl/Cmd+K, slash menu, Trash restore
