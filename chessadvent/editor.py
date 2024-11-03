#!/usr/bin/env python3

import curses
from argparse import ArgumentParser, Namespace
from typing import Dict, List

from .pieces import Piece, Dir, Team, OPPONENT_TEAMS
from .board import Board, Square


KEYS_TO_PIECE_TYPES: Dict[int, str] = {ord(t.lower()): t for t in Piece.TYPES}
KEYS_TO_DIRS: Dict[int, Dir] = {
    curses.KEY_UP: 'u',
    curses.KEY_DOWN: 'd',
    curses.KEY_LEFT: 'l',
    curses.KEY_RIGHT: 'r',
}
KEYS_TO_TEAMS: Dict[int, int] = {
    ord(str(i)): i for i in range(OPPONENT_TEAMS + 1)
}

OPPONENT_TEAM_COLORS = (1, 2, 3, 4)


def color_pair_id_from_team(team: Team) -> int:
    """Returns the number of a curses color pair."""
    # NOTE: team 0 corresponds to pair 0, which is hardcoded by curses
    # to be white-on-black.
    # We assume we've called curses.init_pair to set up color pairs for
    # the other teams.
    return team

def color_pair_attr_from_team(team: Team) -> int:
    """Returns a curses attribute (for use with addstr, etc)."""
    return curses.color_pair(color_pair_id_from_team(team))


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--width', default=8)
    parser.add_argument('--height', default=8)
    parser.add_argument('-f', '--filename', default=None)
    return parser.parse_args()


class QuitEditor(Exception):
    """Raise this within Editor class to quit."""


class Editor:

    def __init__(self, *, args: Namespace, screen: curses.window):
        self.args = args
        self.screen = screen

        self.x = 0
        self.y = 0

        self.piece = Piece('K')
        self.pawn_dir = 'u'

        if args.filename:
            self.board = Board.load(filename)
        else:
            self.board = Board(w=args.width, h=args.height)

    def select_piece(self):
        # A screen of the UI which is specifically for selecting a piece
        # (in particular, allows rotating pawns w/ arrow keys)
        screen = self.screen
        board = self.board
        message = '\n'.join([
            "Arrow keys to rotate pawn",
        ] + self._get_piece_key_message_lines() + [
            "Enter when done",
            "F1 to quit",
        ])
        while True:
            screen.clear()
            screen.addstr(0, 0, "Selected piece: ")
            screen.addstr(self.piece.char, color_pair_attr_from_team(self.piece.team))
            if self.piece.type != 'P':
                screen.addstr(1, 0, f"(Pawn direction: {Piece.pawn_char(self.pawn_dir, 0)})")
            screen.addstr(3, 0, message)
            screen.refresh()
            key = screen.getch()
            if key == curses.KEY_F1:
                raise QuitEditor
            elif key == ord('\n'):
                return
            elif key in KEYS_TO_DIRS:
                self.pawn_dir = KEYS_TO_DIRS[key]
                if self.piece.type == 'P':
                    self.piece = self.piece._replace(char=Piece.pawn_char(
                        self.pawn_dir, self.piece.pawn_type))
            else:
                self._handle_piece_key(key)

    def _get_piece_key_message_lines(self) -> List[str]:
        # Returns instructions corresponding to self._handle_piece_key
        return [
            f"{Piece.TYPES} to choose piece",
            "(Press 'P' multiple times to change pawn type)",
            f"{''.join(str(i) for i in range(OPPONENT_TEAMS + 1))} to choose team",
        ]

    def _handle_piece_key(self, key: int) -> bool:
        # Returns True if key was handled, False otherwise
        if key in KEYS_TO_PIECE_TYPES:
            piece_type = KEYS_TO_PIECE_TYPES[key]
            if piece_type == 'P':
                if self.piece.type == 'P':
                    if self.piece.pawn_type == 0:
                        pawn_type = 1
                    else:
                        pawn_type = 0
                else:
                    pawn_type = 0
                self.piece = self.piece._replace(
                    char=Piece.pawn_char(self.pawn_dir, pawn_type))
            else:
                self.piece = self.piece._replace(char=piece_type)
        if key in KEYS_TO_TEAMS:
            self.piece = self.piece._replace(team=KEYS_TO_TEAMS[key])
        else:
            return False
        return True

    def view_board(self):
        screen = self.screen
        board = self.board
        message = '\n'.join([
            "Arrow keys to move",
            "Backspace to select piece",
            "Enter to add/remove piece",
            "Space to add/remove squares",
        ] + self._get_piece_key_message_lines() + [
            "F1 to quit",
        ])
        while True:
            screen.clear()

            i = 0
            for y in range(board.h):
                for x in range(board.w):
                    square = board.squares[i]
                    piece = board.pieces[i]
                    if piece:
                        attrs = color_pair_attr_from_team(piece.team)
                        screen.addch(y, x, piece.char, attrs)
                    else:
                        char = square.char if square else '#'
                        screen.addch(y, x, char)
                    i += 1

            screen.addstr(board.h + 1, 0, "Selected piece: ")
            screen.addstr(self.piece.char, color_pair_attr_from_team(self.piece.team))
            screen.addstr(board.h + 3, 0, message)
            screen.move(self.y, self.x)
            screen.refresh()
            key = screen.getch()
            if key == curses.KEY_F1:
                raise QuitEditor
            elif key == curses.KEY_BACKSPACE:
                self.select_piece()
            elif key == ord(' '):
                square = board.get_square(self.x, self.y)
                if square:
                    square = None
                else:
                    square = Square(Square.CHAR_NORMAL)
                board.set_square(self.x, self.y, square)
            elif key == ord('\n'):
                square = board.get_square(self.x, self.y)
                if square and not square.solid:
                    piece = board.get_piece(self.x, self.y)
                    if piece == self.piece:
                        board.set_piece(self.x, self.y, None)
                    else:
                        board.set_piece(self.x, self.y, self.piece)
            elif key == curses.KEY_UP:
                if self.y > 0:
                    self.y -= 1
            elif key == curses.KEY_DOWN:
                if self.y < board.h - 1:
                    self.y += 1
            elif key == curses.KEY_LEFT:
                if self.x > 0:
                    self.x -= 1
            elif key == curses.KEY_RIGHT:
                if self.x < board.w - 1:
                    self.x += 1
            else:
                self._handle_piece_key(key)


def main(screen: curses.window, args: Namespace):
    screen.timeout(500)

    # Set up opponent teams' colours
    for team, fgcolor in zip(range(1, OPPONENT_TEAMS + 1), OPPONENT_TEAM_COLORS):
        curses.init_pair(team, fgcolor, 0)

    editor = Editor(args=args, screen=screen)
    try:
        editor.view_board()
    except QuitEditor:
        pass


if __name__ == '__main__':
    args = parse_args()
    curses.wrapper(main, args)
