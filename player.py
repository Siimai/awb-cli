"""Your code goes here.

autoplay.py calls on_result() after every game, with the result the game gave.
Return a new plan to play it next, or None to stop. It stops by itself when the
level is won, or after --max-calls games.

By default this adds one random key press to the plan that was just played, so
the plan grows by one move per game. It stops when the player dies, the level is
won, or the games run out.

Example: ask an AI (such as Jev) what to try next, using the result as its input:

    def on_result(result, attempt):
        print(f"Game {attempt}: {result['status']}")
        if result["status"] == "win":
            return None
        return ask_jev(result["state"])  # your function; returns e.g. "-1:250,1:45"
"""
import random


def on_result(result, attempt):
    """Handle one result and decide what to play next.

    result:  the game's result as a dict (status, room, level, frames, plan, state)
    attempt: how many games have been played so far, starting from 1

    Return the next plan, as text ("-1:250,1:45") or as a list ([[-1, 250], [1, 45]]),
    or None to stop.
    """
    if result.get("status") == "died":
        return None
    return result["plan"] + "," + random_key_press()


def random_key_press():
    """One move as direction:ticks: push left (-1), right (1) or not at all (0) for a while."""
    return f"{random.choice([-1, 0, 1])}:{random.randint(10, 300)}"
