# YouTube / yt-dlp / spotDL download research (2026-08-20)

Sandbox notes from Helsinki VPS tests. Production wiring is in **§12** (implemented 2026-08-20). Do **not** start the bot from this doc.

Related current production behavior:

- `queue_functions.py` runs `../spotdl` with `--bitrate 320k` and `--yt-dlp-args "--proxy <socks>"` (stderr discarded).
- `spotseek_queue_handler.py` calls `setup_spotdl_executable()`, which re-downloads a pinned GitHub binary (`spotdl_executable_link` in `variables.py`, currently v4.4.3).
- README already guessed the symptom: `YT-DLP` → IP probably banned by YouTube.

Those bullets are the **pre-change** command (and any still-running processes). On-disk code as of 2026-08-20 is **§12**. Live bot/queue-handler processes were **not** restarted as part of that wiring.

---

## 1. How the pipeline actually works

spotDL does **not** download audio from Spotify. Spotify is only metadata (title, artist, cover). Audio comes from **YouTube / YouTube Music via yt-dlp**.

```
Spotify URL
    → spotDL (Spotify API / partner)  →  track title/artist
    → YouTube Music search            →  watch URL
    → yt-dlp download googlevideo     →  audio stream
    → ffmpeg                          →  mp3 (if --bitrate / --format mp3)
```

`AudioProviderError: YT-DLP download error - <url>` is a **wrapper**. The URL is the matched video, not the cause. Real errors only show with `--log-level DEBUG` (or by not discarding stderr).

Typical hidden causes in 2026:

| Real yt-dlp message | Meaning |
|---|---|
| `Sign in to confirm you’re not a bot` / `LOGIN_REQUIRED` | Datacenter/VPS IP flagged |
| `Video unavailable` | Geo-block, Music-only ID, or burned proxy IP |
| `HTTP Error 403: Forbidden` on googlevideo | Bad signature / missing JS runtime / flagged CDN URL |
| `Requested format is not available` | Format selector does not match listed itags |
| `No supported JavaScript runtime` | Deno/Node not usable; some formats missing |

spotDL docs also list this exact wrapper error when **Deno is missing**. That was **not** the VPS-direct failure here (Deno was installed). It **did** matter under `proxychains4` (see §5).

---

## 2. What we tested (all in `/root/Temp`)

Test track: `https://open.spotify.com/track/7714d3sE1vuGjukNnSkAif` (AURORA — The Blade)

Public yt-dlp probe video: `https://www.youtube.com/watch?v=jNQXAC9IVRw` (Me at the zoo)

### Artifacts created in the sandbox

| Path | What |
|---|---|
| `/root/Temp/yt-dlp` | Official standalone Linux binary **2026.08.19** (~39MB) |
| `/root/Temp/spotdl` | Frozen spotDL **4.5.2** ELF (~75MB). Bundles its **own** (older) yt-dlp. Does **not** use `/root/Temp/yt-dlp`. |
| `/root/Temp/spotdl-venv/` | Python venv: **spotdl 4.5.2** + **yt-dlp 2026.08.19** + `yt-dlp-ejs` |
| `/etc/proxychains4.conf` | `strict_chain` + SOCKS5 used for tests (x-ui / remote SOCKS, not local WARP `40001`) |

Snap/system `yt-dlp` was also `2026.07.04` (older than the Temp binary). Ignore it for these notes.

Deno was installed at `/root/.deno/bin/deno` (2.5.x / 2.6.x). Direct yt-dlp saw it. Under proxychains it became unusable.

### Results

| Test | Result |
|---|---|
| `/root/Temp/yt-dlp` **direct** (no proxy) on `jNQXAC9IVRw` | Fail: `Sign in to confirm you’re not a bot` (`LOGIN_REQUIRED`) |
| Same yt-dlp **simulate** of Music URL `mjvPT3jJhLs` direct | Fail: bot check |
| Same simulate with **yt-dlp `--proxy socks5://…`** | Fail: `Video unavailable` (different error, still no download) |
| Frozen `./spotdl` + `--yt-dlp-args "--proxy socks5://…"` | Fail: `AudioProviderError` on a Music URL |
| Frozen `./spotdl` via **`proxychains4`** (no extra `--proxy`) | Search/metadata OK, then **HTTP 403** on googlevideo |
| Frozen `./spotdl` + proxychains + `--yt-dlp-args "-f 140"` | Still **403** → bundled extractor is the problem, not only the format flag |
| `/root/Temp/yt-dlp` via **`proxychains4`**, `-f worst[ext=mp4]/worst` | Past bot check; fail: `Requested format is not available` (no progressive mp4) |
| Same, `-F` then **`-f 140`** | **Success** (~302KB m4a for zoo; ~4.2MB m4a for the AURORA match) |
| **venv** `spotdl` + **`proxychains4`** + `--yt-dlp-args "-f 140"` + `--bitrate 320k` | **Success**: `AURORA - The Blade.mp3` (~11MB, tagged 320 kbps) |

Local WARP SOCKS `127.0.0.1:40001` (commented in `variables.py`) was **not** a working exit: `Socks5Error: all offered authentication methods were rejected`.

### Working sandbox command (copy this)

```bash
export PATH="/root/.deno/bin:$PATH"

# 1) yt-dlp only (sanity)
cd /root/Temp
proxychains4 ./yt-dlp --no-playlist --no-mtime -f 140 \
  -o "yt-dlp-test.%(ext)s" \
  "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# 2) spotDL using the venv yt-dlp 2026.08.19 (this is the one that worked)
mkdir -p /root/Temp/spotdl-venv-test
cd /root/Temp/spotdl-venv-test
proxychains4 /root/Temp/spotdl-venv/bin/spotdl \
  --log-level DEBUG \
  --bitrate 320k \
  --yt-dlp-args "-f 140" \
  --output "{track-id}/" \
  download "https://open.spotify.com/track/7714d3sE1vuGjukNnSkAif"
```

Recreate the venv if it is gone:

```bash
python3 -m venv /root/Temp/spotdl-venv
/root/Temp/spotdl-venv/bin/pip install -U pip
/root/Temp/spotdl-venv/bin/pip install -U "yt-dlp[default,curl-cffi]" spotdl
/root/Temp/spotdl-venv/bin/python -c "import yt_dlp,spotdl; print(yt_dlp.version.__version__, spotdl.__version__)"
```

---

## 3. Why `--proxy` on yt-dlp-args was weaker than `proxychains4`

`--yt-dlp-args "--proxy socks5://…"` only affects **yt-dlp**. spotDL’s own YouTube Music search (`ytmusicapi`) and Spotify HTTP still leave from the **Helsinki VPS IP**. YouTube then sees two identities (search from datacenter, media from SOCKS) and/or still bot-checks the VPS.

`proxychains4` `LD_PRELOAD`s the process so **every** TCP connect (Spotify, YT Music, googlevideo, lyrics sites) uses `/etc/proxychains4.conf`. That is what cleared `LOGIN_REQUIRED` on this host.

**Do not combine them.** proxychains + `--proxy` is a double tunnel and caused extra failures.

spotDL also has its own `--proxy`, which is HTTP(S)-oriented in the help text; SOCKS via proxychains was the path that actually worked here.

---

## 4. Why the frozen `./spotdl` binary is a dead end (for now)

spotDL **imports** `yt_dlp` as a Python library. The PyInstaller/ELF binary has a **frozen** copy. It will never call `/root/Temp/yt-dlp`.

On the matched video, latest yt-dlp + proxychains + `-f 140` downloaded fine. Frozen spotDL + the same proxychains + `-f 140` still got **403**. So the bundled extractor, not only the proxy wrapping, was stale.

Use a **pip venv** (or otherwise the same Python env) so `import yt_dlp` is 2026.08.19+ (or whatever current release is at implementation time). Re-check with:

```bash
/root/Temp/spotdl-venv/bin/python -c "import yt_dlp; print(yt_dlp.version.__version__)"
```

`setup_spotdl_executable()` wiping and re-fetching v4.4.3 would undo a “replace `../spotdl`” approach. If production switches to the venv, stop using that helper for the downloader or point it somewhere else.

---

## 5. Deno vs proxychains (format lock)

Modern yt-dlp solves YouTube JS challenges with **Deno** (EJS). Direct run: `JS runtimes: deno-2.x`.

Under `proxychains4`: `JS runtimes: deno-unknown (unsupported)` and `deno (unavailable)`. `LD_PRELOAD` breaks Deno’s version probe / execution. Warning: extraction without a JS runtime is deprecated; many formats vanish.

That is why `-f 140` was required in the working tests. Default `bestaudio` often pointed at streams that 403 without nsig/PO-token solving.

Future options if you want 251/better formats **and** proxychains:

- Run Deno **outside** the proxychains namespace (hard; child processes inherit preload).
- Get a residential/mobile IP so you might skip proxychains.
- Cookies + a cleaner IP (see §8).
- Re-test each yt-dlp release; this interaction may change.

---

## 6. What itag 140 is, and quality vs the old bot

spotDL default `--format mp3` asks yt-dlp for:

```text
bestaudio/best
```

(see `spotdl/providers/audio/base.py`). It does **not** download 320 kbps from YouTube. `--bitrate 320k` is **ffmpeg re-encode after** the download.

### YouTube audio itags (typical free video)

| itag | Codec | Typical rate | Role |
|---|---|---|---|
| **251** | Opus (webm) | ~160 kbps VBR | Usual `bestaudio` winner when extraction is healthy |
| **140** | AAC-LC `mp4a.40.2` (m4a) | ~128–130 kbps | Standard AAC; what we locked |
| 141 | AAC ~256 kbps | rare | YT Music premium / cookies |
| 250 / 249 / 139 | lower Opus/AAC | worse | not what we want |

**Before `-f 140` (when downloads still worked):** source was YouTube’s best listed audio, **usually 251 Opus ~160k**, sometimes 140 if 251 was missing. Never a studio 320k/FLAC. spotDL’s own docs round “regular” to 128k and “premium cookies” to 256k.

**With `-f 140`:** always AAC ~128k. Slightly worse than healthy 251 (Opus keeps more treble; 140 often rolls off ~16 kHz). Not a drop to 48k junk. Both are already YouTube re-encodes.

**`--bitrate 320k` on top of 140:** ffmpeg inflates ~128k AAC into a larger 320k **MP3**. File size goes up; detail does not. Extra generation loss. Telegram/bot already used this flag, so user-facing files were already transcoded MP3s, not the raw YouTube itag.

If implementing without fake 320k: `--format m4a --bitrate disable` keeps AAC as-is (smaller, one less encode). Bot today expects mp3 + Telegram metadata flow in `queue_functions.py`.

---

## 7. Suggested production wiring (when you decide to)

Keep changes in `queue_functions.py` only after a fresh sandbox replay. Do **not** also pass `--proxy`.

Sketch (paths as of 2026-08-20):

```python
command = [
    "proxychains4", "-f", proxychains4_config_file,
    "/root/Temp/spotdl-venv/bin/spotdl",  # or a venv inside this repo
    "--bitrate", "320k",                  # optional; see quality notes
    "--yt-dlp-args", "-f 140",            # drop if Deno works under the chosen network path
    "--output", "{track-id}/",
    "download",
]
```

Also worth doing at the same time:

1. Stop swallowing stdout/stderr (or log them). Otherwise you only see “no mp3” and rotate proxies blindly.
2. Raise the 300s timeout if batches stay at `simultaneous_downloads = 8` (one track was ~100s in the working test).
3. Do not let `setup_spotdl_executable()` replace the venv with GitHub 4.4.3.
4. Pin/upgrade **yt-dlp in the venv** when YouTube breaks again (`pip install -U "yt-dlp[default]"`). Nightlies fix extractors faster than spotDL releases.
5. Prefer wrapping **the whole** spotDL process with proxychains over `--yt-dlp-args --proxy`.
6. `{track-id}/` output layout is required by the cover/mp3 folder logic that follows `download_tracks()`.

Optional later: `--threads 1` for cleaner logs; skip lyrics providers if Genius/AZLyrics/Musixmatch 403/429 through the SOCKS (lyrics failed in tests and are not required for the mp3).

---

## 8. Pros and cons of the working approach

### proxychains4 around all of spotDL

**Pros**

- Cleared YouTube bot-check on this VPS where direct and `--proxy`-only failed.
- One exit IP for search + download.
- Matches how standalone yt-dlp was proven.

**Cons**

- Breaks Deno → fewer formats, 403 on `bestaudio`, need `-f 140` (or similar).
- Depends on `/etc/proxychains4.conf`. A burned or datacenter SOCKS still fails (`Video unavailable`, 403).
- Extra latency; lyrics/Genius/etc. also go through the proxy (429/403 seen).
- `LD_PRELOAD` can surprise other child binaries (Deno, maybe others).

### venv spotDL + new yt-dlp (not frozen ELF)

**Pros**

- Same yt-dlp release that actually downloaded.
- `pip install -U yt-dlp` without waiting for a new spotDL binary.
- Frozen 4.5.2 still 403’d after format lock.

**Cons**

- Another runtime to keep on disk and in PATH.
- Easy to accidentally keep using `../spotdl` or the 4.4.3 bootstrap.

### `-f 140`

**Pros**

- Reliable under proxychains-without-Deno.
- Known itag, HTTPS DASH, worked on both test URLs.

**Cons**

- Slightly below typical old `bestaudio` (251).
- If 140 is missing on a video, the download fails unless you add fallbacks, e.g. `-f 140/139/bestaudio[ext=m4a]/bestaudio`.

### Cookies / residential IP / WARP (not proven in this sandbox)

YouTube’s own message for the VPS was cookies (`--cookie-file` / `--cookies-from-browser`). That is often **easier than a new IP**, but:

- Use a throwaway Google account; volume downloading flags accounts.
- Cookies + datacenter IP is still hit-or-miss.
- Residential/mobile egress is what YouTube treats as a person. Cheap SOCKS and shared WARP ranges are often already listed.
- You cannot “set” a trusted IP; you only egress through a network YouTube already trusts.

spotDL: `--cookie-file cookies.txt` (and/or yt-dlp cookie args). Export notes: [yt-dlp FAQ cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp), [exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).

### IP rotation among current `socks_proxies`

Rotating more **datacenter** SOCKS is unlikely to fix bot-check. The tested remote SOCKS still needed proxychains + new yt-dlp + format 140. Direct `--proxy` to that host was not enough.

---

## 9. Implementation checklist

When you want this in the bot:

- [ ] Replay §2 working commands on a couple of tracks (including one that failed last week).
- [ ] Confirm venv `yt-dlp` version ≥ the release that worked (2026.08.19 at the time of this note).
- [ ] Switch the subprocess to `proxychains4` + venv `spotdl`; **remove** `--yt-dlp-args --proxy`.
- [ ] Keep `-f 140` until Deno works in that network mode; then try dropping it and compare itags in DEBUG logs.
- [ ] Log spotDL stderr.
- [ ] Disable or redirect `setup_spotdl_executable()` so it cannot overwrite the downloader.
- [ ] Decide mp3+320k vs keep m4a (quality vs Telegram/bot assumptions).
- [ ] Watch SOCKS reputation; have a way to change **network type**, not only the numeric IP.

---

## 10. References (from this research)

- spotDL wrapper error / Deno: <https://spotdl.github.io/spotify-downloader/troubleshooting/>
- spotDL issues: [#2263](https://github.com/spotDL/spotify-downloader/issues/2263), [#2516](https://github.com/spotDL/spotify-downloader/issues/2516), [#2575](https://github.com/spotDL/spotify-downloader/issues/2575)
- yt-dlp JS runtimes (EJS / Deno): <https://github.com/yt-dlp/yt-dlp/wiki/EJS>
- yt-dlp PO tokens: <https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide>
- Default format selection: `spotdl/providers/audio/base.py` (`bestaudio/best` for mp3)

---

## 11. Higher quality follow-up (itag 251, same day)

Full command/result table: `/root/Temp/QUALITY_EXPERIMENTS.md`. Production command still not wired.

**Winner: itag 251 works.** 140 is not the ceiling on this host.

Deno 2.5.3 **does** run under `proxychains4` when `/root/.deno/bin` is on `PATH` (`JS runtimes: deno-2.5.3`). Earlier §5 `deno-unknown` was the reason we locked `-f 140`; that probe now succeeds. `--js-runtimes deno:/root/.deno/bin/deno` also works if PATH is empty.

Standalone yt-dlp `--proxy socks5://…@HOST:PORT` (no proxychains) downloads **251** for normal `youtube.com` watch URLs (zoo + AURORA `S6glMinQdUA` / `aCVMXtgudn8`). Same files via proxychains. `ffprobe`: Opus 48 kHz stereo. Music-only IDs can still be `Video unavailable`.

spotDL still needs **proxychains around the whole process**. `--yt-dlp-args --proxy` without proxychains searched from the VPS IP and failed (`GN-6IOHemPE` unavailable). venv spotDL + proxychains **without** `-f 140`:

- `--format opus --bitrate disable` → ~4.5MB Opus (251 remux)
- `--format mp3 --bitrate 320k` → ~11MB mp3 transcoded from bestaudio/251

itag 141 was not listed. No cookies.txt on disk. Nightly yt-dlp also got 251. Extractor-args `tv` / `android,ios` / `mweb` were worse (UNPLAYABLE / SABR / PO token).

**If implementing:** drop `-f 140` from the §2 venv+proxychains recipe; keep Deno on PATH. Optional safety: `-f 251/140/bestaudio`. Do not add `--proxy` beside proxychains.

---

## 12. Production wiring (implemented)

Wired into `/root/Storage/spot-seek-bot` on 2026-08-20. **Do not start/restart/kill** `spotseek.py`, `spotseek_queue_handler.py`, or live spotDL processes from this work. Older instances may still be running until someone restarts them on purpose.

What changed (no `/root/Temp` dependency):

- In-repo venv: `.venv/` with pip **spotdl 4.5.2** + **yt-dlp 2026.08.19** (`requirements-spotdl.txt`). GitHub ELF bootstrap retired (`setup_spotdl_executable()` no longer wgets `spotdl_executable_link`).
- `variables.py`: `spotdl_bin` → `{repo}/.venv/bin/spotdl` (absolute; independent of `cwd=./output/`).
- `queue_functions.py` wraps the **whole** process with `proxychains4 -f /etc/proxychains4.conf`. Removed `--yt-dlp-args --proxy` (double tunnel). No `-f 140`. Default yt-dlp `bestaudio` (typically itag **251**). Still `--bitrate 320k` mp3 + `{track-id}/`.
- Subprocess `env` prepends `.venv/bin` and `/root/.deno/bin` so Deno is on PATH under proxychains. `spotdl` library `download_deno()` placed Deno **2.9.5** in `.venv/bin` (hardlinked from `~/.config/spotdl/deno`; `~/.spotdl` is still wiped each download). System Deno 2.5.3 remains at `/root/.deno/bin` as fallback.
- Restart scripts export that PATH for cron `@reboot`. They were **not** executed.

Exact download command (plus Spotify track URLs):

```text
proxychains4 -f /etc/proxychains4.conf /root/Storage/spot-seek-bot/.venv/bin/spotdl --bitrate 320k --output {track-id}/ download …
```
