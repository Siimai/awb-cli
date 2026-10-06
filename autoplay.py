#!/usr/bin/env python3
"""Play Annoying White Ball through the URL autoplay of the player web build.

Opens URL/index.html?room=ROOM&plan=PLAN in headless Chromium, waits for
window.awbAutoplayResult and prints it as JSON on standard output.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

EXIT_NO_RESULT = 1
EXIT_USAGE = 2


def find_chrome():
    """CHROME, else the newest chrome-headless-shell in the Playwright cache, else None
    (Playwright then uses its own default browser)."""
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    base = Path.home() / ".cache" / "ms-playwright"
    for d in sorted(base.glob("chromium_headless_shell-*"), reverse=True):
        for p in sorted(d.glob("*/chrome-headless-shell")):
            return str(p)
    return None


def read_plan(arg):
    """PLAN is the plan itself, a file name, or - for standard input."""
    if arg == "-":
        return sys.stdin.read().strip()
    if arg and Path(arg).is_file():
        return Path(arg).read_text().strip()
    return arg


def page_url(base, room, plan):
    # A bare number is the level as players see it, anything else a room name.
    key = "level" if room.isdigit() else "room"
    return base.rstrip("/") + "/index.html?" + urlencode({key: room, "plan": plan})


def play(url, timeout_s, insecure, chrome):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chrome,
            args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                  "--ignore-gpu-blocklist", "--disable-background-timer-throttling",
                  "--disable-renderer-backgrounding", "--autoplay-policy=no-user-gesture-required"],
        )
        try:
            page = browser.new_context(ignore_https_errors=insecure).new_page()
            page.goto(url, wait_until="commit", timeout=timeout_s * 1000)
            page.wait_for_function("window.awbAutoplayResult", timeout=timeout_s * 1000, polling=250)
            return page.evaluate("window.awbAutoplayResult")
        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    # Plans start with a direction like -1:250; let argparse take those as values, not options.
    ap._negative_number_matcher = re.compile(r"^-\d")
    ap.add_argument("room", metavar="ROOM", help="room name (room43) or level number (44)")
    ap.add_argument("plan", metavar="PLAN",
                    help="direction:ticks pairs (-1:250,1:45,0:230), JSON [[dir, ticks], ...], "
                         "a file containing either, or - for standard input")
    ap.add_argument("--url", default=os.environ.get("AWB_URL"),
                    help="game URL of a build with autoplay (default: $AWB_URL)")
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("AWB_TIMEOUT", 900)),
                    metavar="SECONDS", help="give up after this long; plays in real time (default 900)")
    ap.add_argument("--insecure", action="store_true",
                    help="ignore HTTPS certificate errors (development certificate)")
    args = ap.parse_args()
    if not args.url:
        ap.error("no game URL: use --url or set AWB_URL")
    plan = read_plan(args.plan)
    if not plan:
        ap.error("empty plan")

    try:
        result = play(page_url(args.url, args.room, plan), args.timeout, args.insecure, find_chrome())
    except PlaywrightTimeout:
        print(f"error: no autoplay result within {args.timeout} s", file=sys.stderr)
        return EXIT_NO_RESULT
    except PlaywrightError as e:
        print(f"error: {str(e).splitlines()[0]}", file=sys.stderr)
        return EXIT_NO_RESULT
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
