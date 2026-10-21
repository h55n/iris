# What is tested vs untested (honest build log)

## Tested live in the dev sandbox (2026-10-20/21)
- whisper.cpp built from source (CPU only); transcribes English WAV/MP3/video audio to timestamped segments. tiny.en and base.en both run.
- Full pipeline on a 54-second two-voice meeting (gTTS-synthesized, clean audio): transcript -> notes via the hosted fallback (Ultramarine ultramarine-1-flash) -> integrity pass -> 6/6 decisions+action items verified against the transcript.
- Integrity pass unit tests: fabricated evidence quotes, out-of-range timestamps and invented owner names are caught and demoted to "unverified" (7/7 tests incl. sync).
- Retention sweep: recordings older than 7 days deleted, transcripts and notes kept; fresh recordings untouched (unit test).
- Sync: server + client pass a loopback test - two local "devices" exchange transcripts/notes through the server; audio confirmed absent server-side; bad token rejected.
- Hindi tested with multilingual models on synthetic gTTS audio (details below).

## Integrity findings from live trap runs (2026-10-20)
- Trap prompt told the model to always assign an owner, inventing one if unclear. Two live runs invented "Sam" and "Alex" behind VERBATIM quotes - evidence-checking alone passed them. The verifier now also requires owner names to appear in the transcript; the same trap run is then caught (live: integrity 4/5, "Alex" demoted with reason "owner not mentioned in transcript").
- Remaining hole, stated honestly: the verifier anchors to the transcript, not the audio, and it cannot judge whether a correctly-quoted line is summarized fairly (spin/tone is unchecked).

## Known limitations observed in the live run
- Verifier anchors to the transcript, not the audio: an ASR error ("we ship" heard as "we shipped") propagated into a decision and still passed verification. The integrity pass catches model invention, not ASR mishearing.
- FIXED: segment granularity. base.en gave 30s blocks; silero VAD now splits at sentence level (24 segments on the 54s test meeting, second-accurate timestamps in notes). Gotcha documented: whisper-cli's -nt flag silently collapses VAD segmentation - engine no longer passes it.
- English models tested (tiny.en/base.en). Hindi: ggml-base TRANSLATES Hindi to English instead of transcribing it; ggml-small transcribes Hindi properly in Devanagari (minor phonetic spelling errors on synthetic audio). Mixed en+hi audio currently needs one forced language; per-segment auto language is v1.5.
- No speaker diarization yet: attempted with synthetic two-channel audio (one voice panned per channel) and whisper.cpp's -di flag; it returned "(speaker ?)" - inconclusive. Real stereo recordings and tuning needed; v1 ships without speaker labels.

## NOT tested here (Hassan must test on his devices)
- Ollama + gemma3:4b as the notes backend (default). Sandbox has no GPU/RAM for it; the hosted fallback was used instead. Test: `ollama pull gemma3:4b && python3 convo/cli.py ingest meeting.wav` (default backend is ollama).
- Real Hindi speech (sandbox test used synthetic gTTS audio, which is unnaturally clean). Use models/ggml-small.bin with -l hi.
- Microphone capture on his laptop and phone (convo/record.py written, untestable in the sandbox - no audio device).
- Long meeting (30-60 min) transcription time and notes quality on his hardware.
- Sync between two real devices (loopback test passed; real phone<->laptop sync still needs his hardware).
- Android recorder app.
- Auto-detection of Zoom/Meet/Teams (detector daemon in progress; needs his desktop for a real meeting test).

## Not built yet (honest scope)
- Encryption at rest (transcripts are plain files today; age-based encryption is v1.5).
- iOS anything.

## Meeting auto-detect (convo/detect.py) - added Oct 21
- TESTED (unit, 7 fake-probe tests): Zoom/Teams/Webex/Slack process detection, Google Meet browser window-title detection (incl. "Meet - abc-defg-hij" title form), 2-poll confirmation (a 1-poll glitch does NOT fire), meeting-end after silence, no duplicate start events, mic signal only attached when a meeting app is present.
- DETECTION ONLY: it never joins or reads the meeting. Recording still starts with a manual confirm.
- Hassan's real-device tests pending: live Zoom + Meet detection on his laptop (X11 vs Wayland - window titles only work on X11; Wayland needs process/mic signals), mic-in-use check on his audio stack.
- Phone (honest limits, built into docs not code): Android can only see the FOREGROUND app name via Usage Access - it cannot see another app's mic or audio (Play policy, May 2022). iOS: no detection possible. Android companion app will use the foreground-app signal with a "meeting? tap to record" notification.

## Encryption at rest (convo/crypto.py + store wiring) - added Oct 21
- age v1.2.1 (X25519, vendored binary in vendor/), key at ~/.convo/key.txt (chmod 600), ASCII-armored .age files.
- TESTED (7 unit tests): keygen + 600 perms + age1 pubkey, refuses overwrite, byte/file roundtrip, wrong key fails, store-level: encrypt_meeting removes plaintext and keeps only .age, decrypt_meeting roundtrip, meta.encrypted flag.
- TESTED LIVE: demo meeting encrypted via `convo encrypt`, plaintext gone from disk, `convo read` roundtrips the real transcript.
- Behavior: `convo ingest` auto-encrypts when a key exists. Sync carries only .age ciphertext (relay never sees plaintext).
- Hassan's tests pending: key pair across 2 devices (copy key file, confirm same pubkey fingerprint), passphrase-protected key variant, sync roundtrip of encrypted meetings.

## Export & encrypted share (convo/export.py) - added Oct 21
- export: one markdown bundle (notes + full transcript + meta), plaintext, audio never included.
- share: same bundle encrypted to a RECIPIENT'S age public key - sharing = re-encrypting to their key, nothing uploaded.
- TESTED (3 unit tests): bundle contents, plaintext export, share only opens with the recipient's key (owner key correctly fails).
- TESTED LIVE: `convo export` on the encrypted demo meeting produced a readable bundle.
- Hassan's tests pending: share a real meeting with a second person (they run `age -d` with their key), PDF export if he wants it.

## Android app (android/) - added Oct 21
- Kotlin, zero third-party deps, minSdk 26 (age decrypt needs 33, gated at runtime).
- RecorderService: foreground service, 16kHz mono WAV, persistent visible notification with Stop. Recording is ALWAYS visible - no background listening.
- MeetingNudge: the only detection Android allows - foreground-app polling via UsageStats (Zoom, Meet, Teams, Webex, Slack) -> "meeting? tap to record" notification. Needs Usage Access granted by the user. CANNOT see other apps' mic/audio (OS + Play policy May 2022).
- SyncClient: pulls meeting bundles from the user's own relay; posts recordings to the user's own laptop ingest endpoint over LAN. Nothing third-party.
- AgeDecrypt: full age v1 decryption in-app (bech32 key import, X25519 via API 33 platform crypto, HKDF-SHA256, ChaCha20-Poly1305, STREAM chunks) - the phone reads encrypted notes with the user's own key.
- TESTED: compiles to a working APK (app-debug.apk builds clean). NOT testable in sandbox - Hassan's on-device list: mic recording quality, nudge firing in a real Zoom/Meet call, LAN upload to laptop, encrypted notes read on phone, Android 13+ gate message on older phones.
- Laptop ingest server (convo/ingest_server.py): phone -> laptop over LAN, full pipeline runs on the laptop, results sync back encrypted via relay.

## Multi-language transcription (ggml-small multilingual, synthetic gTTS speech) - tested Oct 21
Real whisper.cpp runs, one utterance each. Synthetic TTS input - clean studio speech; real meetings are harder. Hassan's real-speech tests still pending.

- Hindi: STRONG. "हमने फैसला किया की रिकॉर्डिंग सात दिन बाद अपने आप डिलीट हो जाएगी। प्रिया सिंक सर्वर संभालेगी।" - minor word errors (सवर for सर्वर), correct script, no unwanted translation. Code-mixed Hinglish words (रिकॉर्डिंग, सिंक) handled.
- Spanish: PERFECT on the test sentence.
- Tamil: GOOD - meaning preserved, some consonant doubling errors (வெள்ளிக்கிளமை).
- Bengali: SCRIPT FAILURE - Whisper heard the Bengali words but wrote them in Devanagari script, not Bengali script. Documented limitation: treat Bengali as unsupported until the large model or a fine-tune fixes it.
- Reminder (tested earlier): ggml-base TRANSLATES Hindi to English instead of transcribing - always use ggml-small or better for non-English. English meetings use base.en (2x faster).
