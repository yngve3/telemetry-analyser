"""Turn direction for mission script steps."""

from enum import StrEnum


class TurnDirection(StrEnum):
    """Supported turn directions."""

    LEFT = "left"
    RIGHT = "right"

