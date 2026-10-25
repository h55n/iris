# TESTED.md - the honesty ledger

Every claim the product makes is tied to a test that actually ran. Anything not testable in the dev sandbox is explicitly assigned to Hassan's devices. Sections are chronological.

## Test ledger summary

| area | status |
|---|---|
| transcription (en, VAD) | LIVE-TESTED (synthetic + LibriSpeech) |
| Hindi transcription (ggml-small) | TESTED synthetic; real-speech 30-min read-speech WER 82.9% (see Oct 24 evening) - no reliability claim |
| Tamil | real-speech 30-min read-speech WER 93.3% (77.4% with VAD disabled) - no reliability claim (see Oct 24 evening) |
| Spanish (es-419, ggml-small) | real-speech 30-min read-speech WER 16.1% |
| Bengali | FAILS (wrong script) - unsupported; real-speech WER 100% (script mismatch) |
| claim verifier | 8 edge-case tests + pipeline demotion tests + live demotions |
| retention sweep | unit-tested + demoed |
| encryption (age) | unit + live roundtrip |
| sync relay | live two-store roundtrip, zero plaintext at relay |
| speaker diarization | LIVE-TESTED (16/16 real-human turns); similar voices degrade |
| meeting auto-detect | unit-tested (fake probes); live laptop = Hassan |
| Android app | builds in CI every push (debug + unsigned release); 4 unit test classes pass; main-screen UI redesigned Oct 25 (Iris plant look); deterministic adb smoke ALL PASS on the redesign (run 40178169679, incl RIFF WAV bytes + screenshots); emulator UI scenario PASS via Artemis Oct 25 (UI-text only, see section); real-device/mic behavior = Hassan |
| wikilinks, local graph, recap, auto-sync | unit + live browser tests (see Oct 23 section) |
| local web UI | live-tested + screenshots |
| ollama/gemma3:4b notes | NOT testable in sandbox - Hassan's laptop |

# What is tested vs untested (honest build log)

## Tested live in the dev sandbox (2026-10-20/21)
- whisper.cpp built from source (CPU only); transcribes English WAV/MP3/video audio to timestamped segments. tiny.en and base.en both run.
- Full pipeline on a 54-second two-voice meeting (gTTS-synthesized, clean audio): transcript -> notes via the hosted fallback (Ultramarine ultramarine-1-flash) -> integrity pass -> 6/6 decisions+action items verified against the transcript.
- Integrity pass unit tests: fabricated evidence quotes, out-of-range timestamps, invented owner names, empty evidence, clause-trimmed quotes and garbage timestamp formats are caught and demoted to "unverified" (8 edge tests + pipeline tests incl. sync).
- Retention sweep: recordings older than 7 days deleted, transcripts and notes kept; fresh recordings untouched (unit test).
- Sync: server + client pass a loopback test - two local "devices" exchange transcripts/notes through the server; audio confirmed absent server-side; bad token rejected. Guard rails live-tested: /pull/ path traversal rejected (400), malformed since= rejected (400), server stays up after both.
- Hindi tested with multilingual models on synthetic gTTS audio (details below).

## Integrity findings from live trap runs (2026-10-20)
- Trap prompt told the model to always assign an owner, inventing one if unclear. Two live runs invented "Sam" and "Alex" behind VERBATIM quotes - evidence-checking alone passed them. The verifier now also requires owner names to appear in the transcript; the same trap run is then caught (live: integrity 4/5, "Alex" demoted with reason "owner not mentioned in transcript").
- Remaining hole, stated honestly: the verifier anchors to the transcript, not the audio, and it cannot judge whether a correctly-quoted line is summarized fairly (spin/tone is unchecked).

## Known limitations observed in the live run
- Verifier anchors to the transcript, not the audio: an ASR error ("we ship" heard as "we shipped") propagated into a decision and still passed verification. The integrity pass catches model invention, not ASR mishearing.
- FIXED: segment granularity. base.en gave 30s blocks; silero VAD now splits at sentence level (24 segments on the 54s test meeting, second-accurate timestamps in notes). Gotcha documented: whisper-cli's -nt flag silently collapses VAD segmentation - engine no longer passes it.
- English models tested (tiny.en/base.en). Hindi: ggml-base TRANSLATES Hindi to English instead of transcribing it; ggml-small transcribes Hindi properly in Devanagari (minor phonetic spelling errors on synthetic audio). Mixed en+hi audio currently needs one forced language; per-segment auto language is v1.5.
- No speaker diarization yet: attempted with synthetic two-channel audio (one voice panned per channel) and whisper.cpp's -di flag; it returned "(speaker ?)" - inconclusive. Real stereo recordings and tuning needed; v1 ships without speaker labels.


## Long-call benchmark (Oct 24, sandbox CPU)
Test track: 33.1 min (1,986.7s) 16kHz mono WAV - four LibriSpeech test-clean readers (7127, 5639, 672, 8230) back-to-back, 232 utterances, reference text from the LibriSpeech .trans.txt files. This is READ SPEECH, one reader at a time, clean studio audio. It is NOT a real multi-speaker call and NOT Hinglish; real meetings will be worse. It answers "does the pipeline hold up over a long file" (memory, segmentation, timestamps, notes), not "does it handle real calls". Long-call testing is NOT complete: validation on real calls with overlapping speakers and Hinglish code-switching is still open and needs licensed real-call corpora (see repo docs/benchmarks/ for what is usable next).

- tiny.en: 301s wall (6.6x realtime), 553MB peak RSS, 433 segments, coverage 0.5s-1986.5s with no gaps (max inter-segment gap 0.5s). WER ~8.7% - APPROXIMATION ONLY: first 3,000 words vs reference, difflib similarity (1-ratio), not a full-transcript standard WER.
- base.en: 974s wall (~2.0x realtime), 661MB peak RSS, 455 segments, same full coverage, no gaps. WER ~5.2% (same approximate method, same caveat). base.en is the better accuracy/speed trade for long files on CPU.
- Notes over the long transcript: one Ultramarine hosted call on the base.en transcript (31,966 chars with [MM:SS] timestamps) -> valid notes JSON; the model correctly reported the content as read literary passages instead of inventing meeting structure (0 decisions / 0 action items, which is right for this input). Token usage logged: 8,818 prompt + 491 completion (prepaid credit, ~/.iris/hosted-usage.jsonl). The default local backend (ollama gemma3:4b) still needs Hassan's hardware.
- Still NOT validated: real overlapping speech, Hinglish code-switching, diarization over long files (sherpa-onnx work above is short-file only), and anything over ~35 min.

## NOT tested here (Hassan must test on his devices)
- Ollama + gemma3:4b as the notes backend (default). Sandbox has no GPU/RAM for it; the hosted fallback was used instead. Test: `ollama pull gemma3:4b && python3 iris/cli.py ingest meeting.wav` (default backend is ollama).
- Real Hindi speech (sandbox test used synthetic gTTS audio, which is unnaturally clean). Use models/ggml-small.bin with -l hi.
- Microphone capture on his laptop and phone (Iris/record.py written, untestable in the sandbox - no audio device).
- Long meeting transcription on his hardware (33-min read-speech benchmark now done in the sandbox - see "Long-call benchmark"; his laptop/phone timing and real-meeting audio still pending).
- Sync between two real devices (loopback test passed; real phone<->laptop sync still needs his hardware).
- Android recorder app.
- Auto-detection of Zoom/Meet/Teams (detector daemon in progress; needs his desktop for a real meeting test).

## Not built yet (honest scope)
- Encryption at rest (transcripts are plain files today; age-based encryption is v1.5).
- iOS anything.

## Meeting auto-detect (Iris/detect.py) - added Oct 21
- TESTED (unit, 7 fake-probe tests): Zoom/Teams/Webex/Slack process detection, Google Meet browser window-title detection (incl. "Meet - abc-defg-hij" title form), 2-poll confirmation (a 1-poll glitch does NOT fire), meeting-end after silence, no duplicate start events, mic signal only attached when a meeting app is present.
- DETECTION ONLY: it never joins or reads the meeting. Recording still starts with a manual confirm.
- Hassan's real-device tests pending: live Zoom + Meet detection on his laptop (X11 vs Wayland - window titles only work on X11; Wayland needs process/mic signals), mic-in-use check on his audio stack.
- Phone (honest limits, built into docs not code): Android can only see the FOREGROUND app name via Usage Access - it cannot see another app's mic or audio (Play policy, May 2022). iOS: no detection possible. Android companion app will use the foreground-app signal with a "meeting? tap to record" notification.

## Encryption at rest (Iris/crypto.py + store wiring) - added Oct 21
- age v1.2.1 (X25519, vendored binary in vendor/), key at ~/.Iris/key.txt (chmod 600), ASCII-armored .age files.
- TESTED (7 unit tests): keygen + 600 perms + age1 pubkey, refuses overwrite, byte/file roundtrip, wrong key fails, store-level: encrypt_meeting removes plaintext and keeps only .age, decrypt_meeting roundtrip, meta.encrypted flag.
- TESTED LIVE: demo meeting encrypted via `Iris encrypt`, plaintext gone from disk, `Iris read` roundtrips the real transcript.
- Behavior: `Iris ingest` auto-encrypts when a key exists. Sync carries only .age ciphertext (relay never sees plaintext).
- Hassan's tests pending: key pair across 2 devices (copy key file, confirm same pubkey fingerprint), passphrase-protected key variant, sync roundtrip of encrypted meetings.

## Export & encrypted share (Iris/export.py) - added Oct 21
- export: one markdown bundle (notes + full transcript + meta), plaintext, audio never included.
- share: same bundle encrypted to a RECIPIENT'S age public key - sharing = re-encrypting to their key, nothing uploaded.
- TESTED (3 unit tests): bundle contents, plaintext export, share only opens with the recipient's key (owner key correctly fails).
- TESTED LIVE: `Iris export` on the encrypted demo meeting produced a readable bundle.
- Hassan's tests pending: share a real meeting with a second person (they run `age -d` with their key), PDF export if he wants it.

## Android app (android/) - added Oct 21
- Kotlin, zero third-party deps, minSdk 26 (age decrypt needs 33, gated at runtime).
- RecorderService: foreground service, 16kHz mono WAV, persistent visible notification with Stop. Recording is ALWAYS visible - no background listening.
- MeetingNudge: the only detection Android allows - foreground-app polling via UsageStats (Zoom, Meet, Teams, Webex, Slack) -> "meeting? tap to record" notification. Needs Usage Access granted by the user. CANNOT see other apps' mic/audio (OS + Play policy May 2022).
- SyncClient: pulls meeting bundles from the user's own relay; posts recordings to the user's own laptop ingest endpoint over LAN. Nothing third-party.
- AgeDecrypt: full age v1 decryption in-app (bech32 key import, X25519 via API 33 platform crypto, HKDF-SHA256, ChaCha20-Poly1305, STREAM chunks) - the phone reads encrypted notes with the user's own key.
- TESTED: compiles to a working APK (app-debug.apk builds clean). NOT testable in sandbox - Hassan's on-device list: mic recording quality, nudge firing in a real Zoom/Meet call, LAN upload to laptop, encrypted notes read on phone, Android 13+ gate message on older phones.
- UI redesign (Oct 25, commit 99af226): warm-paper Iris plant look - sprout wordmark + launcher icon, state-tinted status card (idle lavender / recording coral with pulse / saved blue), pill record button, recordings as rows in a card, grouped Settings rows (sync setup, meeting nudges), masked sync-token/age-key fields, 48dp+ touch targets, status live-region. Record flow, permission timing, sync clients and smoke-test-visible strings unchanged. Verified by adb smoke run 40178169679 (https://github.com/h55n/iris/actions/runs/40178169679): ALL 15 PASS incl 656KB RIFF WAV on disk + screenshots of idle/recording/saved states. Expanded sync panel (fields, buttons, masked token rendering), collapse toggle and Meeting-nudges -> Usage Access intent verified by ui_capture in run 40178953482 (https://github.com/h55n/iris/actions/runs/40178953482), screenshots in artifact.
- Laptop ingest server (Iris/ingest_server.py): phone -> laptop over LAN, full pipeline runs on the laptop, results sync back encrypted via relay.

## Multi-language transcription (ggml-small multilingual, synthetic gTTS speech) - tested Oct 21
Real whisper.cpp runs, one utterance each. Synthetic TTS input - clean studio speech; real meetings are harder. Hassan's real-speech tests still pending.

- Hindi: STRONG. "हमने फैसला किया की रिकॉर्डिंग सात दिन बाद अपने आप डिलीट हो जाएगी। प्रिया सिंक सर्वर संभालेगी।" - minor word errors (सवर for सर्वर), correct script, no unwanted translation. Code-mixed Hinglish words (रिकॉर्डिंग, सिंक) handled.
- Spanish: PERFECT on the test sentence.
- Tamil: GOOD - meaning preserved, some consonant doubling errors (வெள்ளிக்கிளமை).
- Bengali: SCRIPT FAILURE - Whisper heard the Bengali words but wrote them in Devanagari script, not Bengali script. Documented limitation: treat Bengali as unsupported until the large model or a fine-tune fixes it.
- Reminder (tested earlier): ggml-base TRANSLATES Hindi to English instead of transcribing - always use ggml-small or better for non-English. English meetings use base.en (2x faster).

## Local web UI (Iris/webui.py) - added Oct 21
- TESTED LIVE: index lists meetings with encrypted badge + integrity counts; detail page renders the ENCRYPTED demo meeting's decrypted notes (claims with receipts as blockquotes) and full transcript.
- Localhost-only bind by design - it serves decrypted content. No CDN, no external requests, no auth (threat model: same-user same-machine). Small inline JS only: theme switcher (localStorage), confetti on first save, rotating taglines, `/` search focus. Exposing it on LAN is explicitly out of scope.

## Speaker labels (diarization) - TESTED, NOT SHIPPED (Oct 21)
- Round 1 (synthetic): gTTS two-voice meeting + pitch-shifted variant -> ZERO [SPEAKER_TURN] markers. (whisper.cpp tinydiarize, ggml-small.en-tdrz, akashmjn/tinydiarize-whisper.cpp)
- Round 2 (real humans, proper test per Hassan): 16 alternating turns from TWO REAL LibriSpeech dev-clean speakers (CC-BY 4.0), 6s per turn -> ZERO [SPEAKER_TURN] markers again. Transcription fine; turn detection dead in this build.
- Conclusion: whisper.cpp tinydiarize does not work. Speaker labels come from sherpa-onnx instead (below).

## Speaker diarization SHIPPED (Iris/diarize.py) - tested Oct 21, proper retest per Hassan
- Stack: sherpa-onnx OfflineSpeakerDiarization = pyannote-segmentation-3.0 (ONNX, 6MB) + 3dspeaker ERes2Net voxceleb embedding (26MB) + fast clustering. Fully local, free, no accounts. `models/get-diarize-models.sh` fetches both.
- TEST 1 - real two-human speech (16 alternating 6s turns, two LibriSpeech dev-clean speakers, CC-BY): 21 segments, EVERY turn attributed to the correct speaker (perfect alternation). campplus embedding variant FAILED this test (collapsed to one speaker) - ERes2Net is the one that works; don't swap it.
- TEST 2 - synthetic gTTS two-voice demo meeting: 7/7 turns correct.
- TEST 3 - end to end: `Iris ingest two_humans.wav --diarize --speakers 2` produced a transcript with correct "Speaker 1:/Speaker 2:" prefixes per line.
- Unit tests (5): overlap assignment, majority rule, no-overlap, same-speaker merging, gap respect.
- Honest limits: num_speakers known helps; unknown-speaker-count mode (clustering threshold) untested; overlapping speech (two people talking at once) untested - segmentation models handle overlap partially, expect misses; Hindi/multilingual diarization untested (embedding is English-voxceleb-trained but language-agnostic in principle - Hassan's real Hindi meeting is the test).

## Full-text search (Iris search) - added Oct 21
- TESTED LIVE: `Iris search Priya` on the ENCRYPTED demo meeting decrypts locally and finds matches in both transcript and notes. Case-insensitive, searches all meetings.

### Diarization on non-English synthetic (proxy test, same day)
- hi+ta two-voice synthetic mix (4 turns): turn boundaries found, but 2 of 4 turns had their first half attributed to the WRONG speaker (both TTS voices are similar-pitch female voices; short segments give weak embeddings).
- Read: diarization is solid on distinct real voices (LibriSpeech 16/16 turns), degrades on acoustically similar voices. Real Hindi meeting test stays on Hassan's list; don't promise speaker labels for his calls until that passes.

### Diarization speaker-count modes (demo meeting rerun, same day)
- --speakers 2 (known count): 7/7 turns correct.
- auto count (clusterer decides): over-clustered - split ONE gTTS voice into "Speaker 1" and "Speaker 3" (3 clusters for 2 voices). Turn boundaries still right.
- Guidance shipped in README: pass --speakers N when you know the headcount; auto mode may over-split. Real-meeting calibration stays on Hassan's list.
- Bonus live evidence: on this rerun the verifier demoted "Write the retention sweep tonight (owner not mentioned in transcript)" - the integrity pass catching an over-eager owner attribution in the wild, unscripted.

## Voice enrollment (iris/voices.py) - added Oct 21 evening
- Enroll a name from a 5-15s sample; diarized clusters then render as names.
- LIVE TEST (real audio): enrolled LibriSpeech speaker 1272 from a held-out clip, ran name_clusters on the 16-turn two-human mix -> correct cluster matched at cosine 0.844, other speaker at -0.002 (correctly unknown). Threshold default 0.5.
- Voiceprints are 192-d float embeddings in ~/.iris/voices/*.npy - no audio stored, nothing leaves the machine.
- Hassan's tests: enroll himself + a family member/friend, run a real meeting, tune threshold if needed.
- E2E (same day): `iris enroll SpeakerA sample.wav` then `iris ingest two_humans.wav --diarize --speakers 2` -> transcript lines show "SpeakerA:" for the enrolled voice and "Speaker 2:" for the unknown one. Full pipeline: diarize -> cluster embeddings -> voice match -> named markdown.

## Mixed-language (Hinglish) transcription - tested Oct 21 evening
- Synthetic 4-turn file (en/hi/en/hi): `transcribe_multilingual` segments with the multilingual model, detects language per segment. Result: all 4 turns correct language, Hindi in Devanagari. Small-model word errors on names (Priya->PREO, Hassan->वहसन) noted honestly.
- Important tested failure: a base.en pass DROPS Hindi turns from segmentation entirely (whole-file pass returned 1 segment). Mixed audio must use --multilingual.
- `iris ingest meeting.wav --multilingual`; non-English lines get <hi> tags in the transcript.

## Web UI robustness - tested Oct 21 evening
- Live HTTP tests (19): 404 for unknown meeting/raw file, path traversal rejected on raw download AND sync pull, title XSS escaped, rename caps 120 chars, locked-meeting page when the key is missing (no 500), corrupt meta.json skipped on every page, search skips locked meetings without the key.

## Web UI dark mode - tested Oct 21 evening
- prefers-color-scheme: dark switches the full Notion palette (bg #191919, sidebar #202020, same tokens). Pixel-verified on real screenshots at 1440px: home + meeting page.
- First-pass bugs the screenshots caught and the fix commit addressed: sidebar active item, rename/delete buttons, rename input were hardcoded white. Light mode re-verified unchanged (body #fff, sidebar #f7f7f5).

## Android unit tests - added Oct 21 evening
- `gradle testDebugUnitTest`: AgeDecryptTest 2/2 green (bech32 rejects garbage, bech32 charset complete). JVM-only, no emulator needed.
- Upload retry (2 retries, 1.5s/3s backoff) + X-Iris-Title header: compiles into a clean APK; runtime retry behavior is on Hassan's device test list.
- Ingest server accepts X-Iris-Title and falls back to X-Convo-Title for older app builds (tested: header-preference unit test in tests/test_ingest_server.py).

## Design pass 2 (themes, mascot, motion) - tested Oct 21 night
- 6 accent themes x light/dark: pixel-verified on live screenshots at 1440/1024/390, purple and orange spot-checked; theme persists via localStorage, applies before first paint (no flash).
- Sidebar theme picker: first version never matched its CSS (stray quote in class attribute) - caught on a real screenshot, fixed, re-verified pinned to the sidebar footer.
- Motion: spring-eased page/list entrance, hover lifts, press scale; prefers-reduced-motion disables all of it (CSS media query, not JS).
- Confetti "Meeting saved" moment: fires only for meetings <10 min old, once per meeting per browser (localStorage guard). Celebrate mascot verified on a real fresh meeting.
- Mascot: geometric eye SVG REJECTED by Hassan; 3 hand-drawn-ink candidates (Scribble/Noctua/Echo) sent for his pick before wiring in.

## Robustness passes - Oct 21 night
- CLI argument validation: read/export/encrypt/share used to traceback or silently exit 0 on a bad meeting id; now one helper prints "no such meeting" + exit 1.
- sweep --dry-run previews retention deletions without touching files (tested both paths).
- Ingest server caps uploads at 500MB, checked on the Content-Length header before reading the body (413).
- Web UI raw download endpoint: traversal attempts render "not found" and never touch the filesystem (tested).
- CI: both jobs green on the same commit - pytest (216 passed, 3 browser tests skipped, as of Oct 22) + Android JUnit (4 tests) on GitHub-hosted runners.

## Notion x Granola upgrade - tested Oct 21 night
- Real Chrome (Playwright) tests, all green: "/" slash menu inserts blocks, Esc keeps text, Ctrl/Cmd+B/I/E toggle bold/italic/code, list continuation (Enter continues, empty item exits), autosave reaches disk with no JS errors, drag reorder of folders and pinned notes persists across reload, the saved-meeting plant runs grow + pop and prefers-reduced-motion turns every animation off.
- Frame capture of the saved-meeting moment (grow, confetti, bloom, twinkle) checked by eye, not just by CSS names.
- Editing an encrypted note or renaming a speaker re-encrypts to the same key; tests assert no plaintext file is left behind.
- Folders, pins and manual order sync between two stores; a newer local edit is never overwritten by a pull (two-device test).
- Speaker rename touches only line-start labels (a spoken "Speaker 2:" inside a sentence and "Speaker 22" are untouched), accepts Devanagari and multi-word names, rejects markup.
- Hinglish detection is heuristic text classification (word list), 11 table cases incl. false-positive guards ("to", "the", "sir"). Not tested on real Hinglish speech; that is a Hassan test.
- Bug found by the tests: the confetti script had a JS syntax error from day one, so the celebration never ran. Fixed; every inline script is now syntax-checked in CI.
- Not covered: real typing latency on a phone, Android UI for folders/pins (web only so far).

## Linked notes, graph, recap, auto-sync - added Oct 23
- Wikilinks: `[[Title]]` links between meetings render in the local web UI; backlinks shown on the target note. TESTED: graph nodes/edges have no self-links or duplicates (unit), graph page and wikilinks render escaped (browser test).
- Recap page: last 7 days of notes on demand; completed task text is struck through without striking the source label; locked (encrypted) notes are excluded (unit + browser tests).
- Auto-sync: after linking the hosted account, notes push silently after each meeting; unlinked or toggled-off means no network call and no error raised (unit + security tests, cross-site push refused).
- Sync guards: a pull never overwrites a local note with browser-encrypted ciphertext from the hosted site (unit); second push of an unchanged note sends nothing (incremental tests).
- Android CI: every push builds assembleDebug AND assembleRelease on GitHub's free runner (release unsigned unless credentials are supplied via gitignored properties or env) and runs the 4 Kotlin unit test classes. Verified green on the first run.

# Hour-long CI benchmarks (2026-10-24 evening)

All legs: github-hosted ubuntu-latest (4 vCPU, 16GB), whisper.cpp pinned 231638a, sha256-pinned models, GGML_NATIVE=OFF, repo product path (iris.transcribe + silero VAD unless noted), inputs rebuilt from original corpus sources per leg. Metrics JSONs: docs/benchmarks/2026-10-24-*.json. WER = jiwer full-transcript, lowercase+punct-stripped (second figure: lowercase-only, punctuation counted).

| leg | corpus | model | audio | WER | wall |
|---|---|---|---|---|---|
| ami90_base | AMI ES2008 a+b+c 90-min assembled compilation (parts concatenated; session gaps possible; real multi-speaker overlap inflates WER) | base.en | 89.6min | 28.6% / 39.3% | 647s |
| ami90_tiny | same | tiny.en | 89.6min | 30.4% / 36.8% | 370s |
| mucs60_small | MUCS 2021 sub-task2 test, single-speaker code-switched Hindi-English lectures (NOT a real Hinglish multi-speaker call) | small | 60.7min | 98.8% / 98.9% | 1138s |
| fleurs_es_41930_small | FLEURS es-419 read speech, 30-min bounded subset | small | 30.4min | 16.1% / 23.5% | 646s |
| fleurs_hi_in30_small | FLEURS hi read speech | small | 30.2min | 82.9% / 84.3% | 2051s |
| fleurs_bn_in30_small | FLEURS bn read speech | small | 30.1min | 100.0% / 100.0% | 2472s |
| fleurs_ta_in30_small | FLEURS ta read speech | small | 30.1min | 93.3% / 93.8% | 967s |

Read these as pipeline+model measurements on test corpora, not live-call quality and not pure model capability:

- Tamil: withhold any reliability claim. A matched diagnostic rerun of the identical ta corpus with VAD disabled (same runner class, same audio/model, only IRIS_VAD_MODEL off) measured 77.4% vs the product-path 93.3% - a configuration effect of the VAD stage on this corpus, not a general causal decomposition. A 5-clip diagnostic sample (121 ref words) gave: independent-clips+VAD 65.7%, independent-noVAD 70.6%, concatenated-VAD 162.7%, concatenated-noVAD 86.3% (concat spans derived from full-transcript alignment - an extraction approximation, and a diagnostic sample, not a corpus estimate). ta error breakdown (VAD run): 69% substitutions, 24% alignment deletions, 2% insertions; no repetition loops or empty segments (343 segments checked); NFC-vs-NFD normalization of the full ref+hyp texts does not change measured WER and the texts are already NFC (that specific normalization form only; other Unicode-level factors are not excluded - the byte-truncation defect found in the hi/mucs/bn legs is itself Unicode-adjacent); auto-vs-fixed language identical on 2 clips (sample-limited).
- Bengali: model does not emit Bengali script for this audio - an isolated clip gives Latin-script romanization with both -l auto and -l bn (phonetically close to the reference), the 30-min concatenated run produced Devanagari script plus repeat loops. The reference is Bengali script, so word overlap is zero and measured WER is 100%: a script-mismatch-dominated measurement, consistent with the pre-existing synthetic finding ("Bengali FAILS wrong script - unsupported").
- MUCS: S3279 D3489 I0 H83 on 6851 ref words - substitution+alignment-deletion dominated, zero insertions; different failure shape from ta. No reliability claim for code-switched lectures.
- hi: S1347 D1763 I46 H697 - alignment deletions 46% of errors. No reliability claim.
- UTF-8: whisper.cpp can write invalid UTF-8 in segment text - observed raw bytes are truncated multibyte sequences at segment-text ends (hi, mucs, bn legs). Pipeline now decodes tolerantly (U+FFFD stays in the transcript), counts replacements per leg (mucs 1, hi 2, bn 2), and preserves raw whisper bytes as CI artifacts; regression fixtures in tests/test_transcribe_utf8.py. Removing the affected hypothesis words leaves rounded WER unchanged (98.79%/82.90% both ways) - that tests the scoring substitution only; original bytes unrecoverable, upstream effects untested. ami90/es/ta legs ran before this instrumentation; their outputs parsed cleanly, which is only possible with zero invalid bytes.
- Sandbox local test suite at this commit: 222 passed, 10 failed + 19 errors, all pre-existing sandbox-environment issues (missing age binary, subprocess limits), identical with and without today's changes; run in CI where applicable.

# Improvement evaluation: whisper flag tuning + model-size probe (2026-10-25 early IST)

Follow-up to Hassan's request to improve the benchmark scores. Method: frozen baseline above (commit 9e3cea4) -> tuning on disjoint DEVELOPMENT slices -> one config frozen (docs/benchmarks/dev-2026-10-24/SELECTION.md) -> a single held-out confirmation run set. Dev slices: FLEURS test.tsv utterances 30-45min, MUCS utterances after the 60-min baseline (15min). Held-out slices (never run before the confirmation): FLEURS 45-75min, MUCS next 30min. All splits text/utterance-disjoint from baseline and each other (verified intersections = 0); FLEURS speaker overlap across slices is unverifiable (no speaker IDs in the tsv), so this is within-corpus validation. Single runs per cell; observed differences; uncertainty unestimated.

Selected config: ggml-small + IRIS_WHISPER_EXTRA_FLAGS="-mc 0" (no context carry between windows). Flags only - no shipped default, model, or cost change was made or is implied by this section.

Held-out confirmation (30-min held-out slices, paired flags="" vs "-mc 0" on identical inputs; runs 40125620381 / 40125627501; JSONs docs/benchmarks/hold-2026-10-25/):

| leg | baseline flags | -mc 0 | observed delta |
|---|---|---|---|
| fleurs_hold_ta_in_small | 82.5 / 84.0 | 79.7 / 82.9 | -2.8 |
| fleurs_hold_hi_in_small | 82.4 / 84.4 | 67.4 / 69.1 | -15.0 |
| fleurs_hold_es_419_small | 5.9 / 11.2 | 6.5 / 14.4 | +0.6 (regression) |
| fleurs_hold_bn_in_small | 100.0 / 100.0 | 100.0 / 100.0 | 0 (unsupported stands) |
| mucs_hold_small | 95.9 / 98.5 | 82.9 / 84.0 | -13.0 |

- Measured CI wall time (4-vCPU ubuntu-latest) rose with "-mc 0" on 4 of 5 held-out legs for identical 30-min audio: ta 1955s -> 3695s, hi 775s -> 2425s, bn 889s -> 3240s, mucs 990s -> 4983s; es roughly unchanged 381s -> 332s. Runner-class measurement, not device performance.
- ami90 has no dev/held-out split; "-mc 0" on the SAME assembled baseline input gave 28.6/39.3 -> 28.3/36.5 (same-input toggle, not held-out evidence).
- Dev did not predict held-out signs/magnitudes: hi dev showed +1.4 (worsening) but held-out -15.0; es dev -0.7 but held-out +0.6. Dev and held-out are different slices; report held-out as the confirmation evidence.
- Rejected alternative (dev evidence): ggml-large-v3-turbo + "-mc 0" reached hi dev 52.6 but mucs dev 97.0; the turbo MUCS hypothesis is Arabic-script-dominant under lang=auto (6147 Arabic + 1311 Latin chars, 0 Devanagari) - a script/language-selection mismatch observation, not an established cause and not an excuse for the end-to-end score. Turbo also cost ~2x CI compute; es turbo 6.9 vs small 5.9.
- Bengali: ~100 WER under every tested config including large-v3-turbo. The unsupported finding stands.
- "-mc 0 --suppress-nst" and "-vmsd 30" variants: nst added insertions on ta dev; vmsd 30 was byte-identical to -mc 0 alone on FLEURS and MUCS (cap not binding on these corpora).
- Mechanism statements remain hypotheses: "-mc 0" was tested because context carry was suspected in concat insertion blow-ups; the held-out numbers confirm the observed effect on these corpora, not the mechanism.

# Artemis on-device UI test (Android emulator, CI) - PASS 2026-10-25

- Run: artemis-device.yml manual dispatch, run 40173266552 (https://github.com/h55n/iris/actions/runs/40173266552), started 2026-10-25T07:34:15Z, completed success in 5m02s. First green after five failure/cancelled attempts on Oct 24; those failures correlate with the Gemini free-tier 20-RPD daily cap being exhausted (owner-visible AI Studio peak 25/20 on Oct 24), and this pass ran after the midnight-Pacific reset with 0/20 used - correlation, not a proven cause.
- What passed: Google's Artemis agent (gemini-3-flash-preview default + gemini-3.5-flash-lite visual lens) drove the CI-built debug APK on an emulated Pixel through the default scenario: launch -> grant microphone ("While using the app") and notification permissions -> START RECORDING -> 10-second hold -> STOP RECORDING -> status text "saved meeting-20261025-073849.wav (611 KB)" with a new "On this phone (newest first): 25 Oct, 07:38 - 611 KB" list row (the list read "No recordings on this phone yet" pre-run). No crash dialogs. Trace screenshots and compiled replay video: artifact artemis-trace, ID 12591272206 (~90-day GitHub retention).
- Agent-reported LLM usage for the run: 15 calls total (gemini-3-flash-preview 8, gemini-3.5-flash-lite 7), 109,862 prompt tokens. Free tier only; no billing enabled.
- What this does NOT establish:
  - Audio-byte validity: the saved file was never read, hashed, or played back; the evidence is UI text plus the list row (that UI check is the scenario's designed success criterion). 611 KB for ~10s is consistent with a real non-empty file but is not proof of one.
  - Real microphone capture: the emulator has no real audio source; recorded content is unverified.
  - Real-device behavior: emulator-only result. On-device behavior on Hassan's phone remains his to test.
