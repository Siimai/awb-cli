#!/usr/bin/env python3
"""Play Annoying White Ball from the command line and print the result as JSON.

    python3 autoplay.py room43 -1:250,1:45,0:230

The game is opened in a headless browser with the room and plan in its URL.
The script waits for the autoplay to finish and prints the result.
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

DEFAULT_URL = "https://www.annoyingwhiteball.com"
DEFAULT_TIMEOUT = 900  # seconds; the game is played in real time

EXIT_OK = 0
EXIT_FAILED = 1  # timeout, or the page could not be loaded
EXIT_USAGE = 2

BROWSER_ARGS = [
    "--no-sandbox",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--autoplay-policy=no-user-gesture-required",
]


def find_browser():
    """Return the browser to use: $CHROME, a Playwright headless shell, or None for the default."""
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    cache = Path.home() / ".cache" / "ms-playwright"
    shells = sorted(cache.glob("chromium_headless_shell-*/*/chrome-headless-shell"), reverse=True)
    return str(shells[0]) if shells else None


def read_plan(arg):
    """The plan is given as text, as the name of a file, or as "-" for standard input."""
    if arg == "-":
        return sys.stdin.read().strip()
    if Path(arg).is_file():
        return Path(arg).read_text().strip()
    return arg


def game_url(base_url, room, plan):
    """A number is a level as players see it; anything else is a room name."""
    key = "level" if room.isdigit() else "room"
    return f"{base_url.rstrip('/')}/index.html?" + urlencode({key: room, "plan": plan})


def play(url, timeout_s, ignore_cert_errors):
    """Open the game and return the autoplay result once the page has produced it."""
    timeout_ms = timeout_s * 1000
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=find_browser(), args=BROWSER_ARGS)
        try:
            page = browser.new_context(ignore_https_errors=ignore_cert_errors).new_page()
            page.goto(url, wait_until="commit", timeout=timeout_ms)
            page.wait_for_function("window.awbAutoplayResult", timeout=timeout_ms, polling=250)
            return page.evaluate("window.awbAutoplayResult")
        finally:
            browser.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Play Annoying White Ball and print the result as JSON.")
    # Plans start with a direction such as -1:250: treat those as values, not options.
    parser._negative_number_matcher = re.compile(r"^-\d")
    parser.add_argument("room", help="room name (room43) or level number (44)")
    parser.add_argument("plan", help="moves as direction:ticks pairs (-1:250,1:45), "
                                     "a file with the moves, or - to read them from standard input")
    parser.add_argument("--url", default=os.environ.get("AWB_URL", DEFAULT_URL),
                        help=f"where the game is (default: $AWB_URL or {DEFAULT_URL})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, metavar="SECONDS",
                        help=f"give up after this long (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--insecure", action="store_true",
                        help="accept any HTTPS certificate (for a game served locally)")
    return parser.parse_args()


def main():
    args = parse_args()
    plan = read_plan(args.plan)
    if not plan:
        print("error: the plan is empty", file=sys.stderr)
        return EXIT_USAGE

    try:
        result = play(game_url(args.url, args.room, plan), args.timeout, args.insecure)
    except PlaywrightTimeout:
        print(f"error: no result after {args.timeout} seconds", file=sys.stderr)
        return EXIT_FAILED
    except PlaywrightError as error:
        print(f"error: {str(error).splitlines()[0]}", file=sys.stderr)
        return EXIT_FAILED

    print(json.dumps(result, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
