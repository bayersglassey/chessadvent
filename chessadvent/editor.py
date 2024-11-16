#!/usr/bin/env python3

import json
import curses
import traceback
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Set, Tuple, Optional

from .pieces import (
    Piece,
    PawnDir,
    Team,
    PIECE_TYPES,
    N_TEAMS,
    MOVE_DIRS_TO_PAWN_DIRS,
)
from .moves import Move
from .board import Board, Square
from .ai import AI


MAX_UNDO_STACK_SIZE = 100


KEYS_TO_PIECE_TYPES: Dict[int, str] = {ord(t.lower()): t for t in PIECE_TYPES}
KEYS_TO_PAWN_DIRS: Dict[int, PawnDir] = {
    curses.KEY_UP: 'u',
    curses.KEY_DOWN: 'd',
    curses.KEY_LEFT: 'l',
    curses.KEY_RIGHT: 'r',
}
KEYS_TO_TEAMS: Dict[int, int] = {
    ord(str(i)): i for i in range(N_TEAMS)
}
KEYS_TO_SQUARE_CHARS: Dict[int, str] = {
    ord(' ' if char == '.' else char.lower()): char
    for char in Square.CHARS}

# curses color pair ids
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
    parser.add_argument('-l', '--load', default=False, action='store_true')
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

        self.filename = args.filename or 'testboard.json'
        self.board = None
        if args.load:
            # NOTE: may fail, leaving self.board as None
            self.load_board()
        if self.board is None:
            self.board = Board(w=args.width, h=args.height)
            self._init_stacks()

        self.ais = {team: AI(team) for team in range(N_TEAMS)}

    def _init_stacks(self):
        self.undo_stack = []
        self.redo_stack = []

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.board)
            self.board = self.undo_stack.pop()
            self._correct_for_modified_board()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.board)
            self.board = self.redo_stack.pop()
            self._correct_for_modified_board()

    def _correct_for_modified_board(self):
        """Should be called after modifying self.board"""
        if self.x >= self.board.w:
            self.x = self.board.w - 1
        if self.y >= self.board.h:
            self.y = self.board.h - 1

    def push_board(self):
        """Should be called before modifying the board in any way, so that
        the modification can be undone"""
        if len(self.undo_stack) >= MAX_UNDO_STACK_SIZE:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.board.copy())
        self.redo_stack.clear()

    def select_piece(self):
        # A screen of the UI which is specifically for selecting a piece
        # (in particular, allows rotating pawns w/ arrow keys)
        while True:
            screen = self.screen
            board = self.board
            message = '\n'.join([
                "Arrow keys to rotate pawn",
            ] + self._get_piece_key_message_lines() + [
                "Enter when done",
                "F1 to quit",
            ])

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
            elif key in KEYS_TO_PAWN_DIRS:
                self.pawn_dir = KEYS_TO_PAWN_DIRS[key]
                if self.piece.type == 'P':
                    self.piece = self.piece._replace(char=Piece.pawn_char(
                        self.pawn_dir, self.piece.pawn_type))
            elif self._handle_piece_key(key):
                pass

    def _get_piece_key_message_lines(self) -> List[str]:
        # Returns instructions corresponding to self._handle_piece_key
        return [
            f"{PIECE_TYPES} to choose piece",
            "(Press 'P' multiple times to change pawn type)",
            f"{''.join(str(i) for i in range(N_TEAMS))} to choose team",
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

    def _handle_move_cursor(self, key: int) -> bool:
        # Returns True if key was handled, False otherwise
        if key == curses.KEY_UP:
            if self.y > 0:
                self.y -= 1
        elif key == curses.KEY_DOWN:
            if self.y < self.board.h - 1:
                self.y += 1
        elif key == curses.KEY_LEFT:
            if self.x > 0:
                self.x -= 1
        elif key == curses.KEY_RIGHT:
            if self.x < self.board.w - 1:
                self.x += 1
        else:
            return False
        return True

    def render_board(self, *, highlights: Set[Tuple[int, int]] = None):
        screen = self.screen
        board = self.board
        i = 0
        for y in range(board.h):
            for x in range(board.w):
                square = board.squares[i]
                piece = board.pieces[i]
                attrs = 0
                if piece:
                    char = piece.char
                    attrs |= color_pair_attr_from_team(piece.team)
                else:
                    char = board.get_square_char(square, x, y)
                if highlights and (x, y) in highlights:
                    attrs |= curses.A_REVERSE
                screen.addch(y, x, char, attrs)
                i += 1

    def addstr_safe(self, s, x=None, y=None, attr=None):
        # TODO: make this actually safe, and then make use of it!..
        args = []
        if x is not None and y is not None:
            args.append(x)
            args.append(y)
        args.append(s)
        if attr is not None:
            args.append(attr)
        self.screen.addstr(*args)

    def show_message(self, msg: str):
        curses.reset_shell_mode()
        self.screen.clear()
        self.screen.refresh()
        print(msg)
        input("Press Enter...")
        curses.reset_prog_mode()

    def show_error(self, ex: Exception):
        curses.reset_shell_mode()
        self.screen.clear()
        self.screen.refresh()
        traceback.print_exception(type(ex), ex, ex.__traceback__)
        input("Press Enter...")
        curses.reset_prog_mode()

    def save_board(self):
        try:
            data = self.board.dump()
            with open(self.filename, 'w') as file:
                json.dump(data, file, indent=4)
        except Exception as ex:
            self.show_error(ex)

    def load_board(self):
        try:
            self.board = Board.from_file(self.filename)
            self._init_stacks()
            self.x = 0
            self.y = 0
        except Exception as ex:
            self.show_error(ex)

    def make_ai_move(self, team: Team):
        ai = self.ais[team]
        next_moves = ai.find_next_moves(self.board)
        if next_moves:
            next_move, score = next_moves[0]
            self.board.apply(next_move)

    def view_board(self):
        while True:
            screen = self.screen
            board = self.board
            message = '\n'.join([
                "Arrow keys to move cursor",
                "Backspace to rotate pawn",
                "Enter to add/remove piece",
                "Space to add/remove squares",
            ] + self._get_piece_key_message_lines() + [
                "S to select the piece at cursor",
                "M to enter piece-moving mode",
                "Z/Y to undo/redo",
                "F3 to resize/scroll board",
                f"F5/F7 to save/load board (to/from {self.filename})",
                "F6 to change filename",
                "F1 to quit",
            ])

            screen.clear()
            self.render_board()
            screen.addstr(board.h + 1, 0, "Selected piece: ")
            screen.addstr(self.piece.char, color_pair_attr_from_team(self.piece.team))
            screen.addstr(board.h + 3, 0, message)
            screen.move(self.y, self.x)
            screen.refresh()
            key = screen.getch()
            if key == curses.KEY_F1:
                raise QuitEditor
            elif key == ord('z'):
                self.undo()
            elif key == ord('y'):
                self.redo()
            elif key == ord('s'):
                piece = board.get_piece(self.x, self.y)
                if piece:
                    self.piece = piece
            elif key == ord('m'):
                self.push_board()
                self.move_pieces()
            elif key == curses.KEY_F3:
                self.push_board()
                self.resize_board()
            elif key == curses.KEY_F5:
                self.save_board()
                self.show_message(f"Saved to: {self.filename}")
            elif key == curses.KEY_F6:
                curses.reset_shell_mode()
                screen.clear()
                screen.refresh()
                print(f"Old filename: {self.filename}")
                self.filename = input("Enter new filename: ")
                curses.reset_prog_mode()
            elif key == curses.KEY_F7:
                self.load_board()
                self.show_message(f"Loaded from: {self.filename}")
            elif key == curses.KEY_BACKSPACE:
                self.select_piece()
            elif key in KEYS_TO_SQUARE_CHARS:
                # Add/remove square
                self.push_board()
                char = KEYS_TO_SQUARE_CHARS[key]
                square = board.get_square(self.x, self.y)
                if square:
                    if square.char == char:
                        square = None
                    else:
                        square = square._replace(char=char)
                else:
                    square = Square(char)
                board.set_square(self.x, self.y, square)
                if not square or square.is_solid:
                    board.set_piece(self.x, self.y, None)
            elif key == ord('\n'):
                # Add/remove piece
                self.push_board()
                if not board.is_solid_at(self.x, self.y):
                    piece = board.get_piece(self.x, self.y)
                    if piece == self.piece:
                        board.set_piece(self.x, self.y, None)
                    else:
                        board.set_piece(self.x, self.y, self.piece)
            elif self._handle_piece_key(key):
                pass
            elif self._handle_move_cursor(key):
                pass

    def resize_board(self):
        scrolling = False
        while True:
            screen = self.screen
            board = self.board
            message = '\n'.join([
                f"Arrow keys to {'scroll' if scrolling else 'resize'}",
                f"Backspace to {'resize' if scrolling else 'scroll'}",
                "Enter when finished",
                "F1 to quit",
            ])

            screen.clear()
            self.render_board()
            screen.addstr(board.h + 1, 0, message)
            screen.move(self.y, self.x)
            screen.refresh()
            key = screen.getch()
            if key == curses.KEY_F1:
                raise QuitEditor
            elif key == curses.KEY_BACKSPACE:
                scrolling = not scrolling
            elif key == ord('\n'):
                return
            elif key == curses.KEY_UP:
                if scrolling:
                    board.scroll(0, -1)
                elif board.h > 0:
                    board.resize(0, -1)
                    self._correct_for_modified_board()
            elif key == curses.KEY_DOWN:
                if scrolling:
                    board.scroll(0, 1)
                else:
                    board.resize(0, 1)
                    self._correct_for_modified_board()
            elif key == curses.KEY_LEFT:
                if scrolling:
                    board.scroll(-1, 0)
                elif board.w > 0:
                    board.resize(-1, 0)
                    self._correct_for_modified_board()
            elif key == curses.KEY_RIGHT:
                if scrolling:
                    board.scroll(1, 0)
                else:
                    board.resize(1, 0)
                    self._correct_for_modified_board()

    def move_pieces(self):
        ai_on = False
        screen = self.screen
        board = self.board
        my_team = self.piece.team

        x0, y0, selected_piece = None, None, None
        def select_piece():
            nonlocal x0, y0, selected_piece
            x0 = self.x
            y0 = self.y
            selected_piece = self.board.get_piece(x0, y0)
            if selected_piece and ai_on and selected_piece.team != my_team:
                selected_piece = None
        def unselect_piece():
            nonlocal selected_piece
            selected_piece = None

        while True:
            message = '\n'.join([
                "Arrow keys to move cursor",
                f"Backspace to {'turn off' if ai_on else 'turn on'} AI players",
                f"Enter to {'move piece' if selected_piece else 'select piece to move'}",
                "M to exit piece-moving mode",
                "F1 to quit",
            ])

            highlights = None
            hx, hy = (x0, y0) if selected_piece else (self.x, self.y)
            highlight_piece = board.get_piece(hx, hy)
            if highlight_piece:
                highlight_moves = board.get_moves(hx, hy)
                highlights = {(move.x, move.y) for move in highlight_moves}

            screen.clear()
            self.render_board(highlights=highlights)
            if selected_piece:
                screen.addstr(board.h + 1, 0, "Moving piece: ")
                screen.addstr(selected_piece.char, color_pair_attr_from_team(selected_piece.team))
            else:
                screen.addstr(board.h + 1, 0, "No piece selected!")
                if ai_on:
                    screen.addstr(" You are team: ")
                    screen.addstr("K", color_pair_attr_from_team(my_team))
            screen.addstr(board.h + 3, 0, message)
            screen.move(self.y, self.x)
            screen.refresh()
            key = screen.getch()
            if key == curses.KEY_F1:
                raise QuitEditor
            elif key == ord('\n'):
                if selected_piece:
                    moves = board.get_moves(x0, y0)
                    move_dirs = {
                        dir for dir in range(8)
                        if Move(self.x, self.y, dir) in moves}
                    if move_dirs:
                        move_dir = None
                        if selected_piece.type == 'P':
                            if len(move_dirs) == 1:
                                move_dir = next(iter(move_dirs))
                            else:
                                raise Exception(f"TODO: make user choose a dir!.. out of: {move_dirs}")
                        self.board.move(x0, y0, self.x, self.y, move_dir)
                        unselect_piece()
                        if ai_on:
                            for i in range(N_TEAMS - 1):
                                ai_team = (my_team + 1 + i) % N_TEAMS
                                self.make_ai_move(ai_team)
                else:
                    select_piece()
            elif key == curses.KEY_BACKSPACE:
                ai_on = not ai_on
            elif key == ord('m'):
                if selected_piece:
                    unselect_piece()
                else:
                    return
            elif self._handle_move_cursor(key):
                pass


def main(screen: curses.window, args: Namespace):
    screen.timeout(500)

    curses.def_prog_mode()

    # Set up opponent teams' colours
    for team, fgcolor in zip(range(1, N_TEAMS), OPPONENT_TEAM_COLORS):
        curses.init_pair(team, fgcolor, 0)

    editor = Editor(args=args, screen=screen)
    try:
        editor.view_board()
    except QuitEditor:
        pass


if __name__ == '__main__':
    args = parse_args()
    #curses.def_shell_mode()
    curses.wrapper(main, args)
