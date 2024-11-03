
from typing import List, Tuple, NamedTuple, Optional

from .pieces import Piece


class Square(NamedTuple):
    char: str

    CHAR_NORMAL = '.'
    CHAR_ENTER = 'E'
    CHAR_EXIT = 'X'
    CHAR_BACKSLASH = '\\'
    CHAR_SLASH = '/'
    CHAR_HYPHEN = '-'
    CHAR_PIPE = '|'
    CHARS = (
        CHAR_NORMAL + CHAR_ENTER + CHAR_EXIT
        + CHAR_BACKSLASH + CHAR_SLASH
        + CHAR_HYPHEN + CHAR_PIPE
    )

    @property
    def solid(self) -> bool:
        """If solid, pieces cannot go on top of this square"""
        return self.char != self.CHAR_NORMAL


class Board:

    def __init__(self, *, w: int = 8, h: int = 8):
        self.w = w
        self.h = h
        self.squares: List[Optional[Square]] = [
            Square(Square.CHAR_NORMAL) for i in range(self.size)]
        self.pieces: List[Optional[Piece]] = [None] * self.size

    @property
    def size(self):
        return self.w * self.h

    def render_simple(self) -> str:
        s = ''
        i = 0
        for y in range(self.h):
            for x in range(self.w):
                square = self.squares[i]
                piece = self.pieces[i]
                if piece:
                    s += piece.char
                elif square:
                    s += square.char
                else:
                    s += '#'
                i += 1
            s += '\n'
        return s.strip('\n')

    def print_simple(self):
        print(self.render_simple())

    def scroll(self, addx: int, addy: int):
        w = self.w
        h = self.h
        addx = addx % w
        addy = addy % h

        pieces_lines = [None] * h
        squares_lines = [None] * h
        for y in range(h):
            i0 = y * w
            i1 = i0 + w - addx
            i2 = i0 + w
            y1 = (y + addy) % h
            pieces_lines[y1] = self.pieces[i1:i2] + self.pieces[i0:i1]
            squares_lines[y1] = self.squares[i1:i2] + self.squares[i0:i1]

        self.pieces = []
        for line in pieces_lines:
            self.pieces += line

        self.squares = []
        for line in squares_lines:
            self.squares += line

    def resize(self, add_w: int, add_h: int):
        old_w = self.w
        old_h = self.h
        new_w = old_w + add_w
        new_h = old_h + add_h

        pieces_lines = []
        squares_lines = []
        for y in range(new_h):
            i0 = y * old_w
            i1 = i0 + min(new_w, old_w)
            pieces_lines.append(self.pieces[i0:i1])
            squares_lines.append(self.squares[i0:i1])
        for i in range(add_h):
            pieces_lines.append([None] * new_w)
            squares_lines.append([None] * new_w)

        add_to_line = [None] * add_w

        self.pieces = []
        for line in pieces_lines:
            line += add_to_line
            self.pieces += line

        self.squares = []
        for line in squares_lines:
            line += add_to_line
            self.squares += line

        self.w = new_w
        self.h = new_h

    def coords_to_index(self, x: int, y: int) -> Optional[int]:
        if x < 0 or x >= self.w or y < 0 or y >= self.h:
            return None
        return y * self.w + x

    def get_piece(self, x: int, y: int) -> Optional[Piece]:
        i = self.coords_to_index(x, y)
        return self.pieces[i] if i is not None else None

    def set_piece(self, x: int, y: int, piece: Optional[Piece]):
        i = self.coords_to_index(x, y)
        if i is None:
            raise IndexError(x, y)
        self.pieces[i] = piece

    def get_square(self, x: int, y: int) -> Optional[Square]:
        i = self.coords_to_index(x, y)
        return self.squares[i] if i is not None else None

    def set_square(self, x: int, y: int, square: Optional[Square]):
        i = self.coords_to_index(x, y)
        if i is None:
            raise IndexError(x, y)
        self.squares[i] = square

    @classmethod
    def load(cls, filename: str) -> 'Board':
        raise NotImplementedError

    def save(self, filename: str):
        raise NotImplementedError
