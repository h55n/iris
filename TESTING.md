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

## Install as an app (PC and phone, the same web app)

PC (Windows/Mac/Linux): run `run-iris.bat` (Windows) or `./run-iris.sh`, open http://127.0.0.1:8473 in Chrome or Edge, then menu > "Install Iris". Record page: /record (microphone works on localhost).

Phone or tablet: start the server for the network with a token, e.g. `python3 iris/webui.py --host 0.0.0.0 --token PICKONE`. Browsers only allow the microphone on https or localhost, so put it behind a free https tunnel (for example `cloudflared tunnel --url http://localhost:8473` or Tailscale Serve), open the https link once with `?t=PICKONE`, then "Add to Home screen" / "Install app".

What the web app cannot do (this is why the Android APK still exists): detect that Zoom/Meet opened and nudge you, record with the screen off or in the background, or capture other apps' audio. Browsers don't allow those.
