#!/usr/bin/env python3
"""Play Annoying White Ball from the command line.

    python3 autoplay.py room43 -1:250,1:45,0:230

The game is opened in a headless browser with the room and plan in its URL.
The script waits for the autoplay to finish, prints a summary line (or the
whole result as JSON with --json) and gives the result to on_result() in
player.py. Put your own code there to play on with a new plan, until the level
is won or --max-calls is reached.
"""
import argparse
import json
import os
import re
import signal
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from player import on_result

DEFAULT_URL = "https://www.annoyingwhiteball.com/play"
DEFAULT_TIMEOUT = 900  # seconds; the game is played in real time
DEFAULT_MAX_CALLS = 10

EXIT_OK = 0
EXIT_FAILED = 1  # timeout, or the page could not be loaded
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130  # Ctrl+C, as shells report it

# The game is real time, so the headless browser must render without a GPU (swiftshader),
# must not slow down its timers or hidden tab, and must not wait for a click to play audio.
# --no-sandbox lets Chromium start as root, as in a container; the page it opens is the game.
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


def play(browser, url, deadline, ignore_cert_errors):
    """Open the game in a new page and return the autoplay result once the page has produced it.
    Raises PlaywrightTimeout if that takes until the deadline (a time.monotonic() value)."""
    def time_left_ms():
        # Playwright treats 0 as "no timeout", so never pass less than 1 ms.
        return max(1, int((deadline - time.monotonic()) * 1000))

    page = browser.new_context(ignore_https_errors=ignore_cert_errors).new_page()
    page.goto(url, wait_until="commit", timeout=time_left_ms())
    page.wait_for_function("window.awbAutoplayResult", timeout=time_left_ms(), polling=250)
    return page.evaluate("window.awbAutoplayResult")


def quit_on_interrupt(signum, frame):
    """Quit at once on Ctrl+C. Playwright's driver gets the signal too and starts shutting down
    on its own, which leaves this script waiting on it, so skip Playwright's own cleanup."""
    print("\nExiting...", file=sys.stderr, flush=True)
    os._exit(EXIT_INTERRUPTED)


def print_result(result, attempt, as_json):
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Game {attempt}: {result.get('status')} "
              f"({result.get('room')}, {result.get('frames')} frames)")


def play_until_done(args, plan):
    """Play the plan, then every plan that on_result() returns, until the level is won,
    on_result() returns None or --max-calls games have been played.
    --timeout limits the whole run, all games together.
    Then print the URL of the last game attempted, whatever its result, which the player can
    open to replay it."""
    deadline = time.monotonic() + args.timeout
    url = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=find_browser(), args=BROWSER_ARGS)
            for attempt in range(1, args.max_calls + 1):
                url = game_url(args.url, args.room, plan)
                result = play(browser, url, deadline, args.insecure)
                print_result(result, attempt, args.json)
                next_plan = on_result(result, attempt)
                if result.get("status") == "win" or not next_plan:
                    break
                plan = next_plan if isinstance(next_plan, str) else json.dumps(next_plan)
    finally:
        # On stderr, so that standard output stays the results only.
        if url:
            print(f"\nReplay the last game in your browser:\n{url}", file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Play Annoying White Ball and print the result (see player.py).")
    # Plans start with a direction such as -1:250: treat those as values, not options.
    # (argparse has no public way to ask for this, so this uses its private matcher.)
    parser._negative_number_matcher = re.compile(r"^-\d")
    parser.add_argument("room", help="room name (room43) or level number (44)")
    parser.add_argument("plan", help="moves as direction:ticks pairs (-1:250,1:45), "
                                     "a file with the moves, or - to read them from standard input")
    parser.add_argument("--url", default=os.environ.get("AWB_URL", DEFAULT_URL),
                        help=f"where the game is (default: $AWB_URL or {DEFAULT_URL})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, metavar="SECONDS",
                        help=f"give up after this long, all games together (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS, metavar="N",
                        help=f"play at most this many games (default: {DEFAULT_MAX_CALLS})")
    parser.add_argument("--json", action="store_true",
                        help="print the full result of every game as JSON")
    parser.add_argument("--insecure", action="store_true",
                        help="accept any HTTPS certificate (for a game served locally)")
    return parser.parse_args()


def main():
    args = parse_args()
    signal.signal(signal.SIGINT, quit_on_interrupt)
    plan = read_plan(args.plan)
    if not plan:
        print("Error: the plan is empty", file=sys.stderr)
        return EXIT_USAGE

    try:
        play_until_done(args, plan)
    except PlaywrightTimeout:
        print(f"Timeout: no result after {args.timeout} seconds", file=sys.stderr)
        return EXIT_FAILED
    except PlaywrightError as error:
        print(f"Error: {str(error).splitlines()[0]}", file=sys.stderr)
        return EXIT_FAILED

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
