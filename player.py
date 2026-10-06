"""Your code goes here.

autoplay.py calls on_result() after every game, with the result the game gave.
By default it prints the result and stops.

To play on until the level is solved, return a new plan from on_result().
autoplay.py then plays it, and calls on_result() again with the new result.
It stops when the level is won, when you return None, or after --max-calls games.

Example: ask an AI (such as Jev) what to try next, using the result as its input:

    def on_result(result, attempt):
        print(f"Game {attempt}: {result['status']}")
        if result["status"] == "win":
            return None
        return ask_jev(result["state"])  # your function; returns e.g. "-1:250,1:45"
"""
import json


def on_result(result, attempt):
    """Handle one result and decide what to play next.

    result:  the game's result as a dict (status, room, level, frames, plan, state)
    attempt: how many games have been played so far, starting from 1

    Return the next plan, as text ("-1:250,1:45") or as a list ([[-1, 250], [1, 45]]),
    or None to stop.
    """
    print(json.dumps(result, indent=2))
    return None
