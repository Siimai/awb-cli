# awb-cli

Sample application for [Annoying White Ball](https://github.com/Siimai/annoyingwhiteball)
(issue #46): `autoplay.py` plays a level through the URL autoplay of the player web build
and prints the result as JSON.

## Setup

Needs Python 3 and [Playwright for Python](https://playwright.dev/python/):

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    # or: uv venv && uv pip install -r requirements.txt

The browser is found in this order: `$CHROME`, the newest `chrome-headless-shell` in
`~/.cache/ms-playwright` (where the game repository's Node tools keep their Chromium), then
Playwright's own browser (`playwright install chromium`).

## Usage

    python3 autoplay.py [--url URL] [--timeout SECONDS] [--insecure] ROOM PLAN

- `ROOM`: a room name (`room43`) or a level number as players see it (`44`).
- `PLAN`: `direction:ticks` pairs (`-1:250,1:45,0:230`), the JSON `[[dir, ticks], ...]` of
  `tools/solutions/` in the game repository, a file containing either, or `-` for standard input.
- `--url` or `$AWB_URL`: the game URL. It must be a build with autoplay (PR #41), for now a
  development build such as `https://192.168.252.2:8443/` served by `tools/web_dev.sh`; the
  public site does not have it yet.
- `--insecure`: ignore HTTPS certificate errors, for the development certificate
  (`tools/make_dev_cert.sh`). Without it the browser needs a CA that it trusts.
- `--timeout` or `$AWB_TIMEOUT`: seconds to wait for the result (default 900); the page plays
  in real time.

Example:

    AWB_URL=https://192.168.252.2:8443/ python3 autoplay.py --insecure room43 -1:250,1:45,0:230

Standard output is the autoplay result (`window.awbAutoplayResult`: `status`, `room`, `level`,
`frames`, `plan`, `state`). Exit code 0 means a result was received, whatever its `status`
(`win`, `died`, `settled`); 1 means a timeout or a page that failed to load; 2 is a usage error.
Nothing is saved and no files are written: the game does not save when given a plan.
