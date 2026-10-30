"""Tiny terminal helpers: colour only on a TTY, and only when NO_COLOR is unset."""

import os
import sys

CODES = {
    "bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33",
    "blue": "34", "magenta": "35", "cyan": "36", "gold": "38;5;214", "navy": "38;5;18",
}


def use_color(stream=None):
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class Painter(object):
    def __init__(self, enabled=None):
        self.enabled = use_color() if enabled is None else enabled

    def __call__(self, text, *styles):
        if not self.enabled or not styles:
            return text
        seq = ";".join(CODES[s] for s in styles)
        return "\033[{}m{}\033[0m".format(seq, text)


def bar(value, maximum, width=24):
    """A horizontal bar made of block characters, proportional to value/maximum."""
    if maximum <= 0:
        return ""
    blocks = " ▏▎▍▌▋▊▉█"
    eighths = int(round(width * 8 * float(value) / maximum))
    full, rest = divmod(eighths, 8)
    out = "█" * full
    if rest:
        out += blocks[rest]
    return out
