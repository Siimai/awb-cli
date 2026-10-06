# awb-cli

Play [Annoying White Ball](https://www.annoyingwhiteball.com) from the command line.
Give it a level and a list of moves. It plays them in the game and prints what happened as JSON.

## Install

You need Python 3.

    pip install -r requirements.txt
    playwright install chromium

## Use

    python3 autoplay.py LEVEL MOVES

For example, play level 1 (`room0`):

    python3 autoplay.py room0 -1:107,1:679

- **LEVEL** is a room name like `room0`, or a level number like `44`.
- **MOVES** is a list of `direction:ticks` pairs. Direction is `-1` (left), `1` (right) or `0` (no push).
  You can also give a file with the moves, or `-` to read them from standard input.

The result is printed as JSON:

    {
      "status": "win",
      "room": "room0",
      "level": 1,
      "frames": 785,
      ...
    }

`status` is `win`, `died` or `settled` (the moves ended and the ball is still in play).
`state` has a description of the final game state.

## Play on with your own code

After every game, `autoplay.py` calls `on_result()` in [`player.py`](player.py). By default it
prints the result and adds one random key press to the plan, so the plan grows by one move per
game. It stops when the player dies, the level is won, or the games run out.

This is the place for your own code. For example, send the result to an AI such as Jev, ask it
for a better plan, and return that plan. `autoplay.py` then plays it and calls `on_result()`
again. This repeats until the level is won, you return `None`, or the maximum number of games
is reached.

    def on_result(result, attempt):
        if result["status"] == "win":
            return None
        return ask_jev(result["state"])  # your function; returns e.g. "-1:250,1:45"

The plan can be text (`"-1:250,1:45"`) or a list (`[[-1, 250], [1, 45]]`).

## Options

| Option | Meaning |
| --- | --- |
| `--url URL` | Where the game is. Default: `https://www.annoyingwhiteball.com` (or `$AWB_URL`). |
| `--timeout SECONDS` | Give up after this long. Default: 900. The game plays in real time. |
| `--max-calls N` | Play at most this many games. Default: 10. |
| `--insecure` | Accept any HTTPS certificate, for a game you run on your own computer. |

When it is done, the script prints a link to replay the last game. Open it in your browser to
watch the same moves being played.

The script exits with 0 when it gets a result, whatever the status, and with 1 on a timeout or if the page does not load.
Nothing is saved, in the game or on disk.
