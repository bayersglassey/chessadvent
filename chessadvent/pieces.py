
from typing import Tuple, NamedTuple, Optional


Dir = str
DIRS = 'uldr'
def dir_diff(from_dir: Dir, to_dir: Dir) -> Dir:
    """

        >>> dir_diff('u', 'u')
        'u'
        >>> dir_diff('u', 'l')
        'l'
        >>> dir_diff('u', 'r')
        'r'
        >>> dir_diff('u', 'd')
        'd'

        >>> dir_diff('l', 'l')
        'u'
        >>> dir_diff('l', 'd')
        'l'
        >>> dir_diff('l', 'u')
        'r'
        >>> dir_diff('l', 'r')
        'd'

        >>> dir_diff('r', 'r')
        'u'
        >>> dir_diff('r', 'u')
        'l'
        >>> dir_diff('r', 'd')
        'r'
        >>> dir_diff('r', 'l')
        'd'

    """
    from_i = DIRS.index(from_dir)
    to_i = DIRS.index(to_dir)
    return DIRS[(to_i - from_i) % 4]
def dir_rotate_coords(dir: Dir, x: int, y: int) -> Tuple[int, int]:
    if dir == 'u':
        return x, y
    elif dir == 'd':
        return -x, -y
    elif dir == 'l':
        return y, -x
    elif dir == 'r':
        return -y, x
    else:
        raise ValueError(dir)


# Player's team is 0, everything else is opponents
Team = int
OPPONENT_TEAMS = 4


class Piece(NamedTuple):
    char: str
    team: Team = 0

    TYPES = 'KQBNRP'
    PAWN_CHARS = '↑←↓→↟↞↡↠'

    @classmethod
    def pawn_char(cls, dir: Dir, pawn_type: int) -> str:
        i = pawn_type * 4 + DIRS.index(dir)
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
        """One of DIRS, i.e. 'udlr'"""
        char = self.char
        if char in self.PAWN_CHARS:
            return DIRS[self.PAWN_CHARS.index(char) % 4]
        return None

    @property
    def pawn_type(self) -> int:
        """0: regular pawn, 1: pawn which can move 2 spaces"""
        char = self.char
        if char not in self.PAWN_CHARS:
            raise ValueError(char)
        return self.PAWN_CHARS.index(char) // 4
