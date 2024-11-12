import json

from typing import List, Dict, Set, NamedTuple, Optional, Any
from functools import cached_property

from .pieces import (
    Piece,
    PieceType,
    PIECE_TYPES,
    Team,
    N_TEAMS,
    PawnDir,
    MOVE_DIRS_TO_PAWN_DIRS,
)
from .moves import (
    MoveDir,
    Move,
    MOVE_N,
    MOVE_S,
    MOVE_E,
    MOVE_W,
    MOVE_NE,
    MOVE_NW,
    MOVE_SE,
    MOVE_SW,
    MOVE_DIRS_TO_COORDS,
)


EDGE_CHAR = '%'
EMPTY_SQUARE_CHAR = '╬'


CanTake = int
CANNOT_TAKE = 0
CAN_TAKE = 1
MUST_TAKE = 2


class LocatedPiece(NamedTuple):
    x: int
    y: int
    piece: Piece


class PieceMove(NamedTuple):
    piece: LocatedPiece
    move: Move


class CheckMoveResult(NamedTuple):
    would_take: bool
    bounce_dir: Optional[MoveDir]


class Square(NamedTuple):
    char: str

    CHAR_NORMAL = '.'
    CHAR_ENTER = 'E'
    CHAR_EXIT = 'X'
    CHAR_BACKSLASH = '\\'
    CHAR_SLASH = '/'
    CHAR_HYPHEN = '-'
    CHAR_PIPE = '|'
    BOUNCE_CHARS = CHAR_BACKSLASH + CHAR_SLASH + CHAR_HYPHEN + CHAR_PIPE
    CHARS = CHAR_NORMAL + CHAR_ENTER + CHAR_EXIT + BOUNCE_CHARS
    RENDER_CHARS = {
        CHAR_BACKSLASH: '╲',
        CHAR_SLASH: '╱',
        CHAR_HYPHEN: '─',
        CHAR_PIPE: '│',
    }

    _BOUNCES = {
        CHAR_BACKSLASH: {
            # \
            MOVE_N: MOVE_W,
            MOVE_E: MOVE_S,
            MOVE_NE: MOVE_SW,
            MOVE_W: MOVE_N,
            MOVE_S: MOVE_E,
            MOVE_SW: MOVE_NE,
        },
        CHAR_SLASH: {
            # /
            MOVE_N: MOVE_E,
            MOVE_W: MOVE_S,
            MOVE_NW: MOVE_SE,
            MOVE_E: MOVE_N,
            MOVE_S: MOVE_W,
            MOVE_SE: MOVE_NW,
        },
        CHAR_HYPHEN: {
            # -
            MOVE_N: MOVE_S,
            MOVE_NE: MOVE_SE,
            MOVE_NW: MOVE_SW,
            MOVE_S: MOVE_N,
            MOVE_SE: MOVE_NE,
            MOVE_SW: MOVE_NW,
        },
        CHAR_PIPE: {
            # |
            MOVE_E: MOVE_W,
            MOVE_NE: MOVE_NW,
            MOVE_SE: MOVE_SW,
            MOVE_W: MOVE_E,
            MOVE_NW: MOVE_NE,
            MOVE_SW: MOVE_SE,
        },
    }

    @property
    def is_solid(self) -> bool:
        """If solid, pieces cannot go on top of this square"""
        return self.char != self.CHAR_NORMAL

    def get_bounce_dir(self, dir: MoveDir) -> Optional[MoveDir]:
        bounces = self._BOUNCES.get(self.char)
        if bounces is None:
            return None
        return bounces.get(dir)


class Board:
    """

        >>> b = Board(w=4, h=4)
        >>> b.print()
        %%%%%%
        % ░ ░%
        %░ ░ %
        % ░ ░%
        %░ ░ %
        %%%%%%

        >>> data = b.dump()
        >>> data['w'], data['h']
        (4, 4)
        >>> data['pieces'][:3]
        [None, None, None]
        >>> data['squares'][:3]
        [['.'], ['.'], ['.']]

        >>> b2 = Board.load(data)
        >>> b2.squares == b.squares, b2.pieces == b.pieces
        (True, True)

        >>> b.set_square(2, 1, None)
        >>> b.set_piece(1, 2, Piece('K'))
        >>> b.print()
        %%%%%%
        % ░ ░%
        %░ ╬ %
        % K ░%
        %░ ░ %
        %%%%%%

        >>> b.get_state_id()
        '......#...0K......'

        >>> b.get_square(0, 0)
        Square(char='.')
        >>> b.get_square(2, 1)

        >>> b.get_piece(0, 0)
        >>> b.get_piece(1, 2)
        Piece(char='K', team=0)

        >>> b.scroll(1, 1)
        >>> b.print()
        %%%%%%
        % ░ ░%
        %░ ░ %
        % ░ ╬%
        %░ K %
        %%%%%%

        >>> b.resize(1, 1)
        >>> b.print()
        %%%%%%%
        % ░ ░╬%
        %░ ░ ╬%
        % ░ ╬╬%
        %░ K ╬%
        %╬╬╬╬╬%
        %%%%%%%

        >>> b.list_pieces()
        [LocatedPiece(x=2, y=3, piece=Piece(char='K', team=0))]

        >>> moves = b.get_moves(2, 3)
        >>> for move in sorted(moves): print(move)
        Move(x=1, y=2, dir=7)
        Move(x=1, y=3, dir=6)
        Move(x=2, y=2, dir=0)
        Move(x=3, y=3, dir=2)

    """

    squares: List[Optional[Square]]
    pieces: List[Optional[Piece]]

    def __init__(self, *, w: int = 8, h: int = 8, squares=None, pieces=None):
        self.w = w
        self.h = h
        size = w * h
        self.squares = squares if squares is not None else [
            Square(Square.CHAR_NORMAL) for i in range(size)]
        self.pieces = pieces if pieces is not None else [None] * size

    def copy_for_trying_out_moves(self) -> 'Board':
        """Create a copy of self, for trying out moves, e.g. to see how a
        board state's score will be changed by making some move"""
        return Board(
            w=self.w,
            h=self.h,
            squares=self.squares,
            # We need to copy self.pieces, since that's what might be
            # affected by moves being made
            pieces=self.pieces.copy(),
        )

    def get_state_id(self) -> str:
        """Generates a string uniquely identifying this board's current
        state. Usable as a cache key for BoardState objects."""
        return ''.join(
            '#' if square is None else
                square.char + ('' if piece is None else f'{piece.team}{piece.char}')
            for square, piece in zip(self.squares, self.pieces))

    def get_state(self) -> 'BoardState':
        return BoardState(self)

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

    @staticmethod
    def get_square_char(square: Square, x: int, y: int) -> str:
        if square:
            char = square.char
            if char == '.':
                return '░' if x % 2 ^ y % 2 else ' '
            else:
                return Square.RENDER_CHARS.get(char, char)
        else:
            return EMPTY_SQUARE_CHAR

    def render_simple(self) -> str:
        s = EDGE_CHAR * (self.w + 2)
        i = 0
        for y in range(self.h):
            s += f'\n{EDGE_CHAR}'
            for x in range(self.w):
                square = self.squares[i]
                piece = self.pieces[i]
                if piece:
                    s += piece.char
                else:
                    s += self.get_square_char(square, x, y)
                i += 1
            s += EDGE_CHAR
        s += '\n' + EDGE_CHAR * (self.w + 2)
        return s

    def print(self):
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

    def list_pieces(self, team: int = None) -> List[LocatedPiece]:
        return [
            LocatedPiece(i % self.w, i // self.w, piece)
            for i, piece in enumerate(self.pieces)
            if piece is not None
            and (team is None or piece.team == team)]

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

    def is_solid_at(self, x: int, y: int) -> bool:
        square = self.get_square(x, y)
        return not square or square.is_solid

    def move(self, x0: int, y0: int, x1: int, y1: int, dir: MoveDir = None):
        piece = self.get_piece(x0, y0)
        if piece.type == 'P':
            if dir is not None:
                pawn_dir = MOVE_DIRS_TO_PAWN_DIRS[dir]
            else:
                pawn_dir = piece.pawn_dir
            piece = piece._replace(char=Piece.pawn_char(pawn_dir, 0))
        self.set_piece(x0, y0, None)
        self.set_piece(x1, y1, piece)

    def apply(self, piece_move: PieceMove):
        piece, move = piece_move
        self.move(piece.x, piece.y, move.x, move.y, move.dir)

    def get_moves(self, x: int, y: int) -> Set[Move]:

        piece = self.get_piece(x, y)
        if not piece:
            raise Exception(f"No piece at {(x, y)}")

        x0 = x
        y0 = y
        piece_type = piece.type
        team = piece.team

        # Whether we have already checked this move for validity
        checked: Set[Move] = set()

        # Valid moves to be returned
        moves: Set[Move] = set()

        def check_move(x: int, y: int, dir: MoveDir, can_take: CanTake = CAN_TAKE) -> Optional[CheckMoveResult]:
            """Returns (would_take, dir) or None, and updates "checked" and
            "moves".
            A return value of None indicates that either the move is invalid,
            or we have already checked for it, so any looping algorithm (such
            as that for R/B/Q movement) should now terminate.
            If returned dir is different than the dir passed in, that means
            that this is not itself a valid move, but rather should result in
            a bounce in the indicated direction."""
            i = self.coords_to_index(x, y)
            if i is None:
                # Can't move off the board
                return None
            move = Move(x, y, dir)
            if move in checked:
                # Don't check the same square in the same direction more
                # than once!.. so we short-circuit the algorithm here
                return None
            checked.add(move)
            square = self.squares[i]
            bounce_dir = square and square.get_bounce_dir(dir)
            if bounce_dir is not None:
                # NOTE: this move is not itself valid, so we don't add to
                # the "moves" set, but we do return a result which indicates
                # how we should bounce
                return CheckMoveResult(False, bounce_dir)
            if not square or square.is_solid:
                # Can't move onto a solid square
                return None
            would_take = False
            piece = self.pieces[i]
            if piece and not (x == x0 and y == y0):
                if piece.team == team:
                    # Can't move onto other pieces on your team
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
            moves.add(move)
            return CheckMoveResult(would_take, None)

        def check_line(dir: MoveDir, max_moves: int = None, can_take: CanTake = CAN_TAKE):
            addx, addy = MOVE_DIRS_TO_COORDS[dir]
            x = x0 + addx
            y = y0 + addy
            n_moves = 0
            while True:
                result = check_move(x, y, dir, can_take)
                if result is None:
                    # We can't move any further this way
                    # (or we already checked this move, so need to stop the
                    # algorithm now to avoid infinite loop)
                    break
                if result.would_take:
                    # We can't keep moving after taking a piece
                    break
                if result.bounce_dir is not None:
                    addx, addy = MOVE_DIRS_TO_COORDS[result.bounce_dir]
                    dir = result.bounce_dir
                else:
                    # Found a valid move
                    n_moves += 1
                if max_moves is not None and n_moves >= max_moves:
                    # If we've moved the maximum number of times (e.g. 1 for
                    # K, 1 or 2 for P), then stop
                    break
                x += addx
                y += addy

        def check_rook():
            check_line(MOVE_N)
            check_line(MOVE_S)
            check_line(MOVE_E)
            check_line(MOVE_W)

        def check_bishop():
            check_line(MOVE_NW)
            check_line(MOVE_NE)
            check_line(MOVE_SW)
            check_line(MOVE_SE)

        if piece_type == 'K':
            # Check king's 8 possible moves
            check_line(MOVE_N , 1)
            check_line(MOVE_S , 1)
            check_line(MOVE_E , 1)
            check_line(MOVE_W , 1)
            check_line(MOVE_NW, 1)
            check_line(MOVE_NE, 1)
            check_line(MOVE_SW, 1)
            check_line(MOVE_SE, 1)
        elif piece_type == 'Q':
            check_rook()
            check_bishop()
        elif piece_type == 'R':
            check_rook()
        elif piece_type == 'B':
            check_bishop()
        elif piece_type == 'N':
            # Check knight's 8 possible moves
            check_move(x - 1, y - 2, MOVE_N)
            check_move(x - 2, y - 1, MOVE_W)
            check_move(x - 2, y + 1, MOVE_W)
            check_move(x - 1, y + 2, MOVE_S)
            check_move(x + 1, y + 2, MOVE_S)
            check_move(x + 2, y + 1, MOVE_E)
            check_move(x + 2, y - 1, MOVE_E)
            check_move(x + 1, y - 2, MOVE_N)
        elif piece_type == 'P':
            dir = piece.move_dir
            # Check if pawn can take diagonally
            addx, addy = MOVE_DIRS_TO_COORDS[(dir - 1) % 8]
            check_move(x + addx, y + addy, dir, MUST_TAKE)
            addx, addy = MOVE_DIRS_TO_COORDS[(dir + 1) % 8]
            check_move(x + addx, y + addy, dir, MUST_TAKE)
            # Check if pawn can move forwards
            check_line(dir, 1 + piece.pawn_type, CANNOT_TAKE)

        return moves


class BoardState:
    """Represents the board at a specific position.
    For use by the AIs, e.g. when scoring a board position.
    NOTE: Board.get_state_id() should be usable as a cache key for board
    states.

        >>> board = Board.from_file('boards/basic.json')
        >>> board.move(4, 2, 4, 4)
        >>> board.print()
        %%%%%%%%%%%%
        %╬╬╬╬╬╬╬╬╬╬%
        %╬RNBKQBNR╬%
        %╬↡↡↡ ↡↡↡↡╬%
        %╬ ░ ░ ░ ░╬%
        %╬░ ░↓░ ░ ╬%
        %╬ ░ ░ ░ ░╬%
        %╬░ ░ ░ ░ ╬%
        %╬↟↟↟↟↟↟↟↟╬%
        %╬RNBKQBNR╬%
        %╬╬╬╬╬╬╬╬╬╬%
        %%%%%%%%%%%%

        >>> state = board.get_state()

        Team 0 (i.e. South)'s available moves:
        >>> print(' '.join(f'{p.piece.char}x{len(moves)}'
        ...     for p, moves in state.pieces_and_moves_by_team[0] if moves))
        ↟x2 ↟x2 ↟x2 ↟x2 ↟x2 ↟x2 ↟x2 ↟x2 Nx2 Nx2

        Team 1 (i.e. North)'s available moves:
        >>> print(' '.join(f'{p.piece.char}x{len(moves)}'
        ...     for p, moves in state.pieces_and_moves_by_team[1] if moves))
        Nx3 Bx5 Kx1 Qx4 Nx2 ↡x2 ↡x2 ↡x2 ↡x2 ↡x2 ↡x2 ↡x2 ↓x1

        >>> for team, material in state.material_by_team.items():
        ...     print(f'{team}: {material}')
        0: {'K': 1, 'Q': 1, 'B': 2, 'N': 2, 'R': 2, 'P': 8}
        1: {'K': 1, 'Q': 1, 'B': 2, 'N': 2, 'R': 2, 'P': 8}

    """

    def __init__(self, board: Board):

        self.state_id = board.get_state_id()

        # self.pieces_and_moves_by_team[team] = (located_piece, moves)
        self.pieces_and_moves_by_team = pieces_and_moves_by_team = {
            team: [] for team in range(N_TEAMS)}
        for piece in board.list_pieces():
            piece_and_moves = (piece, board.get_moves(piece.x, piece.y))
            pieces_and_moves_by_team[piece.piece.team].append(piece_and_moves)

        # self.teams: teams with any pieces on the board
        self.teams = teams = {team for team in range(N_TEAMS)
            if pieces_and_moves_by_team[team]}
        for team in range(N_TEAMS):
            if team not in teams:
                del pieces_and_moves_by_team[team]

        def get_material(pieces_and_moves) -> Dict[PieceType, int]:
            material = {piece_type: 0 for piece_type in PIECE_TYPES}
            for piece, moves in pieces_and_moves:
                material[piece.piece.type] += 1
            return material

        # self.material_by_team[team][piece] = count
        self.material_by_team = material_by_team = {}
        for team, pieces_and_moves in pieces_and_moves_by_team.items():
            material_by_team[team] = get_material(pieces_and_moves)
