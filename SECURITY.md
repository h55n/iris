# Security

Last audit: 22 Oct 2026, by the author, with tests in `tests/test_security_local.py`. Not a third-party audit.

## What is protected, and how
- **Local app** (`iris/webui.py`): binds 127.0.0.1. It refuses requests whose `Host` is not loopback (DNS rebinding) and cross-site POSTs (`Origin` mismatch or `null`), so a web page you have open cannot delete notes or point Cloud sync at another server. On a network bind it needs `--token`, compared in constant time.
- **Notes rendering**: all note, title, folder and transcript text is HTML-escaped. Links in notes are not rendered. Tests feed script, img, svg, iframe and `javascript:` payloads through every page.
- **Relay and ingest servers**: constant-time token check, body size caps, reject non-object bundles, reject audio fields, reject path-like ids.
- **Cloud sync** pushes notes only. Transcripts are left out unless you opt in. Audio is never sent. Cloud URLs must be https (plain http only for localhost).
- **Android**: backups are off (tokens and the age key are not copied to Google backup). Plain http is accepted only for private-network addresses, https anywhere.
- **Secrets**: the full git history of this repo was scanned. The only key-shaped string is a labelled throwaway test vector for the age decryptor.

## Known limits (not fixed)
- Notes you sync to Iris Cloud are stored as plain text in its database unless you run `iris encrypt` first. Encrypted notes cannot be read on the website.
- The Android age key sits in the app's private storage, not the hardware keystore. The APK is debug-signed.
- The local app's access token on a network bind travels over plain http. Use it only on a network you trust.
- Recordings stay on disk for 7 days before the sweep deletes them. Anyone with access to your account on the machine can read the store.
- Running Whisper, Ollama or ffmpeg means trusting those programs. They were not audited here.

Report problems by opening a GitHub issue, or privately to the repo owner.
