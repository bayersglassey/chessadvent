
from typing import Dict, NamedTuple, Optional

from .moves import MoveDir, MOVE_N, MOVE_S, MOVE_W, MOVE_E


PIECE_TYPES = 'KQBNRP'
PAWN_CHARS = '↑↓←→↟↡↞↠'


PawnDir = str
PAWN_DIRS = 'udlr'
PAWN_DIRS_TO_MOVE_DIRS: Dict[PawnDir, MoveDir] = {
    'u': MOVE_N,
    'd': MOVE_S,
    'l': MOVE_W,
    'r': MOVE_E,
}
MOVE_DIRS_TO_PAWN_DIRS: Dict[MoveDir, PawnDir] = {
    v: k for k, v in PAWN_DIRS_TO_MOVE_DIRS.items()}


# Player's team is 0, everything else is opponents
Team = int
N_TEAMS = 5


class Piece(NamedTuple):
    char: str
    team: Team = 0

    @classmethod
    def pawn_char(cls, pawn_dir: PawnDir, pawn_type: int) -> str:
        i = pawn_type * 4 + PAWN_DIRS.index(pawn_dir)
        return PAWN_CHARS[i]

    @property
    def type(self) -> str:
        """Type of chess piece, one of PIECE_TYPES, e.g. 'K', 'P', etc"""
        char = self.char
        if char in PAWN_CHARS:
            return 'P'
        elif char in PIECE_TYPES:
            return char
        else:
            raise ValueError(char)

    @property
    def pawn_dir(self) -> Optional[PawnDir]:
        """One of PAWN_DIRS, i.e. 'udlr'"""
        char = self.char
        if char in PAWN_CHARS:
            return PAWN_DIRS[PAWN_CHARS.index(char) % 4]
        return None

    @property
    def move_dir(self) -> Optional[MoveDir]:
        pawn_dir = self.pawn_dir
        return pawn_dir and PAWN_DIRS_TO_MOVE_DIRS[pawn_dir]

    @property
    def pawn_type(self) -> int:
        """0: regular pawn, 1: pawn which can move 2 spaces"""
        char = self.char
        if char not in PAWN_CHARS:
            raise ValueError(char)
        return PAWN_CHARS.index(char) // 4
