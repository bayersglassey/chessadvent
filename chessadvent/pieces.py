
from typing import NamedTuple, Optional


Dir = str

# Player's team is 0, everything else is opponents
Team = int
OPPONENT_TEAMS = 4


class Piece(NamedTuple):
    char: str
    team: Team = 0

    TYPES = 'KQBNRP'
    DIRS = 'udlr'
    PAWN_CHARS = '↑↓←→↟↡↞↠'

    @classmethod
    def pawn_char(cls, dir: Dir, pawn_type: int) -> str:
        i = pawn_type * 4 + cls.DIRS.index(dir)
        return cls.PAWN_CHARS[i]

    @property
    def type(self) -> str:
        """Type of chess piece, one of self.TYPES, e.g. 'K', 'P', etc"""
        char = self.char
        if char in self.PAWN_CHARS:
            return 'P'
        elif char in self.TYPES:
            return char
        else:
            raise ValueError(char)

    @property
    def dir(self) -> Optional[Dir]:
        """One of self.DIRS, i.e. 'udlr'"""
        char = self.char
        if char in self.PAWN_CHARS:
            return self.DIRS[self.PAWN_CHARS.index(char) % 4]
        return None

    @property
    def pawn_type(self) -> int:
        """0: regular pawn, 1: pawn which can move 2 spaces"""
        char = self.char
        if char not in self.PAWN_CHARS:
            raise ValueError(char)
        return self.PAWN_CHARS.index(char) // 4
