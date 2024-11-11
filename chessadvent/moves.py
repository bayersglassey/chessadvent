
from typing import NamedTuple


MoveDir = int
MOVE_N  = 0
MOVE_NE = 1
MOVE_E  = 2
MOVE_SE = 3
MOVE_S  = 4
MOVE_SW = 5
MOVE_W  = 6
MOVE_NW = 7

MOVE_DIRS_TO_COORDS = (
    ( 0, -1), # N
    ( 1, -1), # NE
    ( 1,  0), # E
    ( 1,  1), # SE
    ( 0,  1), # S
    (-1,  1), # SW
    (-1,  0), # W
    (-1, -1), # NW
)


class Move(NamedTuple):
    x: int
    y: int
    dir: MoveDir
