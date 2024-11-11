from typing import List, Tuple, Set

from .pieces import Team, N_TEAMS, PIECE_SCORES
from .board import Board, BoardState, LocatedPiece
from .moves import Move


# Default worth of each available move we have when scoring a board state
MOBILITY_WEIGHT = .1


class AI:
    """

        >>> board = Board.from_file('boards/basic.json')
        >>> board.print()
        %%%%%%%%%%%%
        %##########%
        %#RNBKQBNR#%
        %#↡↡↡↡↡↡↡↡#%
        %#........#%
        %#........#%
        %#........#%
        %#........#%
        %#↟↟↟↟↟↟↟↟#%
        %#RNBKQBNR#%
        %##########%
        %%%%%%%%%%%%

        An AI for team 1, i.e. team North in the board above.
        >>> ai = AI(1)

        The AI considers this board state to be neutral.
        >>> state = board.get_state()
        >>> ai.score(state)
        0.0

        Now the AI makes a move!..
        >>> board.move(4, 2, 4, 4)
        >>> board.print()
        %%%%%%%%%%%%
        %##########%
        %#RNBKQBNR#%
        %#↡↡↡.↡↡↡↡#%
        %#........#%
        %#...↓....#%
        %#........#%
        %#........#%
        %#↟↟↟↟↟↟↟↟#%
        %#RNBKQBNR#%
        %##########%
        %%%%%%%%%%%%

        The AI considers this board state to be an improvement!..
        (Due to increased mobility, now that AI's pawn isn't blocking
        some of its pieces)
        >>> state = board.get_state()
        >>> ai.score(state)
        1.0

    """

    piece_scores = PIECE_SCORES

    def __init__(self, team: Team):
        self.team = team

        # How much we like for each team to have material
        self.material_weight_by_team = {
            other_team: 1 if other_team == team else -1
            for other_team in range(N_TEAMS)}

        # How much we like for each team to have mobility
        self.mobility_weight_by_team = {
            other_team: MOBILITY_WEIGHT * (1 if other_team == team else -1)
            for other_team in range(N_TEAMS)}

    def score(self, state: BoardState) -> float:

        piece_scores = self.piece_scores
        material_score = sum(
            piece_scores[piece_type] * piece_count * material_weight
            for team, material_weight in self.material_weight_by_team.items()
            if team in state.material_by_team
            for piece_type, piece_count in state.material_by_team[team].items())

        mobility_score = sum(
            state.mobility_by_team[team] * mobility_weight
            for team, mobility_weight in self.mobility_weight_by_team.items()
            if team in state.mobility_by_team)

        return material_score + mobility_score
