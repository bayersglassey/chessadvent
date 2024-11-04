import json

from typing import List, Dict, Tuple, NamedTuple, Optional, Any, Union

from .pieces import Piece, Dir, dir_diff, dir_rotate_coords


# Can we move onto a square?
# * Empty string: no
# * Non-empty string: yes
#     * The string is one or more Dir values (i.e. a set of chars in 'udlr')
Move = str


CheckMoveResult = Optional[Tuple[Move, bool, Dir]]


CanTake = int
CANNOT_TAKE = 0
CAN_TAKE = 1
MUST_TAKE = 2


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

    squares: List[Optional[Square]]
    pieces: List[Optional[Piece]]

    def __init__(self, *, w: int = 8, h: int = 8, squares=None, pieces=None):
        self.w = w
        self.h = h
        size = w * h
        self.squares = squares if squares is not None else [
            Square(Square.CHAR_NORMAL) for i in range(size)]
        self.pieces = pieces if pieces is not None else [None] * size

    def dump(self) -> Dict[str, Any]:
        def _dump_tuple(t):
            return None if t is None else list(t)
        return {
            'w': self.w,
            'h': self.h,
            'squares': [_dump_tuple(square) for square in self.squares],
            'pieces': [_dump_tuple(piece) for piece in self.pieces],
        }

    @classmethod
    def load(cls, data: Dict[str, Any]) -> 'Board':
        data = data.copy()
        def _load_tuple(d, T):
            return None if d is None else T(*d)
        data['squares'] = [_load_tuple(d, Square) for d in data['squares']]
        data['pieces'] = [_load_tuple(d, Piece) for d in data['pieces']]
        return cls(**data)

    @classmethod
    def from_file(cls, filename: str) -> 'Board':
        with open(filename) as file:
            data = json.load(file)
        return cls.load(data)

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

    def solid_at(self, x: int, y: int) -> bool:
        square = self.get_square(x, y)
        return not square or square.solid

    def get_moves(self, x: int, y: int) -> List[Move]:
        """Returns a list of moves, of length self.size, usable with
        self.get_coords_to_index."""

        moves = [''] * self.size

        piece = self.get_piece(x, y)
        if not piece:
            return moves

        piece_type = piece.type
        team = piece.team
        dir = piece.dir

        def check_move(x: int, y: int, dir: Dir = 'u', can_take: CanTake = CAN_TAKE) -> CheckMoveResult:
            """Returns (move, would_take, dir), or None if move is invalid.
            If move is truthy, also updates the corresponding element of
            moves."""
            i = self.coords_to_index(x, y)
            if i is None:
                # Can't move off the board
                return None
            move = moves[i]
            if dir in move:
                # Don't check the same square in the same direction more
                # than once!.. so we short-circuit the algorithm here
                return None
            square = self.squares[i]
            if not square or square.solid:
                # Can't move onto a solid square
                return None
            would_take = False
            piece = self.pieces[i]
            if piece:
                if piece.team == team:
                    # Can't move onto your other pieces
                    return None
                else:
                    # If we moved here, we would take a piece
                    would_take = True
            if can_take == CANNOT_TAKE and would_take:
                # We can't take, but this would be a take!
                return None
            if can_take == MUST_TAKE and not would_take:
                # We must take, but this would not be a take!
                return None
            move += dir
            moves[i] = move
            return move, would_take, dir

        def pawn_move(addx: int, addy: int, dir: Dir, can_take: CanTake) -> CheckMoveResult:
            addx, addy = dir_rotate_coords(dir, addx, addy)
            px = x + addx
            py = y + addy
            return check_move(px, py, dir, can_take)

        def check_line(x: int, y: int, addx: int, addy: int, dir: Dir):
            addx, addy = dir_rotate_coords(dir, addx, addy)
            x += addx
            y += addy
            while True:
                result = check_move(x, y, dir)
                if result is None:
                    # We can't move any further this way
                    break
                move, would_take, move_dir = result
                if would_take:
                    # We can't keep moving after taking a piece
                    break
                if move_dir and move_dir != dir:
                    addx, addy = dir_rotate_coords(
                        dir_diff(move_dir, dir), addx, addy)
                    dir = move_dir
                x += addx
                y += addy

        def check_rook():
            check_line(x, y,  0, -1, 'u')
            check_line(x, y,  0, -1, 'd')
            check_line(x, y,  0, -1, 'l')
            check_line(x, y,  0, -1, 'r')

        def check_bishop():
            check_line(x, y, -1, -1, 'u')
            check_line(x, y, -1, -1, 'd')
            check_line(x, y, -1, -1, 'l')
            check_line(x, y, -1, -1, 'r')

        if piece_type == 'K':
            # Check king's 8 possible moves
            check_move(x - 1, y - 1)
            check_move(x    , y - 1)
            check_move(x + 1, y - 1)
            check_move(x - 1, y    )
            check_move(x + 1, y    )
            check_move(x - 1, y + 1)
            check_move(x    , y + 1)
            check_move(x + 1, y + 1)
        elif piece_type == 'Q':
            check_rook()
            check_bishop()
        elif piece_type == 'R':
            check_rook()
        elif piece_type == 'B':
            check_bishop()
        elif piece_type == 'N':
            # Check knight's 8 possible moves
            check_move(x - 1, y - 2)
            check_move(x - 2, y - 1)
            check_move(x - 2, y + 1)
            check_move(x - 1, y + 2)
            check_move(x + 1, y + 2)
            check_move(x + 2, y + 1)
            check_move(x + 2, y - 1)
            check_move(x + 1, y - 2)
        elif piece_type == 'P':
            # Check if pawn can take diagonally
            pawn_move(-1, -1, dir, MUST_TAKE)
            pawn_move(+1, -1, dir, MUST_TAKE)
            # Check if pawn can move forwards
            result = pawn_move(0, -1, dir, CANNOT_TAKE)
            if result is not None:
                move, would_take, move_dir = result
                if move and piece.pawn_type == 1:
                    pawn_move(0, -2, move_dir, CANNOT_TAKE)

        return moves
