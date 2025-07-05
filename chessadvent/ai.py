from typing import List, Tuple, Set, Optional

from .pieces import Team, N_TEAMS, PIECE_SCORES
from .board import Board, BoardState, PieceMove
from .moves import Move


# Default worth of each available move we have
# (when scoring a board state)
MOVE_WEIGHT = .02

# Default worth of each piece we have with no available moves
# (when scoring a board state)
STUCK_PIECE_WEIGHT = -.1

Score = float


class AI:

    def find_next_move(
            self,
            board: Board,
            ) -> Optional[Tuple[PieceMove, Score]]:
        next_moves = self.find_next_moves(board)
        return next_moves[0] if next_moves else None

    def find_next_moves(
            self,
            board: Board,
            ) -> List[Tuple[PieceMove, Score]]:
        """Find our next possible moves for the given board, sorted by score
        (highest first)"""
        raise NotImplementedError


class FutureSeekerAI(AI):
    """

        >>> board = Board.from_file('boards/basic.json')
        >>> board.print()
        %%%%%%%%%%%%
        %╬╬╬╬╬╬╬╬╬╬%
        %╬RNBKQBNR╬%
        %╬↡↡↡↡↡↡↡↡╬%
        %╬ ░ ░ ░ ░╬%
        %╬░ ░ ░ ░ ╬%
        %╬ ░ ░ ░ ░╬%
        %╬░ ░ ░ ░ ╬%
        %╬↟↟↟↟↟↟↟↟╬%
        %╬RNBKQBNR╬%
        %╬╬╬╬╬╬╬╬╬╬%
        %%%%%%%%%%%%

        An AI for team 1, i.e. team North in the board above.
        >>> ai = FutureSeekerAI(1)

        The AI considers this board state to be neutral.
        >>> state = board.get_state()
        >>> round(ai.get_state_score(state), 6)
        0.0

        Now the AI makes a move!..
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

        The AI considers this board state to be an improvement!..
        (Due to increased mobility, now that AI's pawn isn't blocking
        some of its pieces)
        >>> state = board.get_state()
        >>> round(ai.get_state_score(state), 6)
        0.5

        Let's ask the AI which moves it considers to be the best from here:
        >>> next_moves = ai.find_next_moves(board)
        >>> len(next_moves)
        30
        >>> for (piece, move), score in next_moves[:3]:
        ...     print(piece.piece.char, (move.x, move.y), round(score, 6))
        Q (1, 5) 0.8
        ↡ (5, 4) 0.76
        Q (2, 4) 0.7

        Let's make the move it considers to be the best:
        >>> move, score = next_moves[0]
        >>> board.apply(move)
        >>> board.print()
        %%%%%%%%%%%%
        %╬╬╬╬╬╬╬╬╬╬%
        %╬RNBK BNR╬%
        %╬↡↡↡ ↡↡↡↡╬%
        %╬ ░ ░ ░ ░╬%
        %╬░ ░↓░ ░ ╬%
        %╬Q░ ░ ░ ░╬%
        %╬░ ░ ░ ░ ╬%
        %╬↟↟↟↟↟↟↟↟╬%
        %╬RNBKQBNR╬%
        %╬╬╬╬╬╬╬╬╬╬%
        %%%%%%%%%%%%

    """

    piece_scores = PIECE_SCORES

    def __init__(self, team: Team):
        self.team = team

        # How far into the future the AI should look
        self.future_sight = 0 #1 * N_TEAMS

        # How much we like for each team to have material
        self.material_weight_by_team = {
            other_team: 1 if other_team == team else -1
            for other_team in range(N_TEAMS)}

        # How much we like for each team to have available moves
        self.move_weight_by_team = {
            other_team: MOVE_WEIGHT * (1 if other_team == team else -1)
            for other_team in range(N_TEAMS)}

        # How much we like for each team to have stuck pieces
        self.stuck_piece_weight_by_team = {
            other_team: STUCK_PIECE_WEIGHT * (1 if other_team == team else -1)
            for other_team in range(N_TEAMS)}

    def get_state_score(self, state: BoardState) -> Score:
        """Get a score for the given state"""

        piece_scores = self.piece_scores

        material_score = 0
        moves_score = 0
        stuck_pieces_score = 0
        for team in state.teams:
            material_weight = self.material_weight_by_team[team]
            for piece_type, piece_count in state.material_by_team[team].items():
                material_score += piece_scores[piece_type] * piece_count * material_weight
            move_weight = self.move_weight_by_team[team]
            stuck_piece_weight = self.stuck_piece_weight_by_team[team]
            for piece, moves in state.pieces_and_moves_by_team[team]:
                if moves:
                    moves_score += len(moves) * move_weight
                else:
                    stuck_pieces_score += stuck_piece_weight

        mobility_score = moves_score + stuck_pieces_score
        return material_score + mobility_score

    def find_next_moves(
            self,
            board: Board,
            ) -> List[Tuple[PieceMove, Score]]:
        """Find our next possible moves for the given board, sorted by score
        (highest first)"""
        return self._find_next_moves_future(board)

    def _find_next_moves_future(
            self,
            board: Board,
            future_sight: int = None,
            *,
            team: Team = None,
            allow_the_empty_move: bool = False,
            ) -> List[Tuple[PieceMove, Score]]:
        """Find our next possible moves for the given board, sorted by score
        (highest first), looking future_sight + 1 moves into the future"""

        # This function calls itself recursively, cycling through the teams,
        # so that the AI can understand what its opponents' best moves might
        # be.
        if team is None:
            team = self.team
        if future_sight is None:
            future_sight = self.future_sight

        def get_board_score(piece_move: Optional[PieceMove]) -> float:
            """Returns the score for the board obtained by applying the given
            PieceMove, or just the score for the current board, but in either
            case factors future moves by all teams into the score."""
            if piece_move is not None:
                new_board = board.copy_for_trying_out_moves()
                new_board.apply(piece_move)
            else:
                new_board = board
            new_state = new_board.get_state()
            if future_sight > 0:
                future_next_moves = self._find_next_moves_future(
                    new_board,
                    future_sight - 1,
                    team=(team + 1) % N_TEAMS,
                    allow_the_empty_move=True,
                )
                future_move, future_move_score = future_next_moves[0]
                return future_move_score
            else:
                return self.get_state_score(new_state)

        # Find all valid moves from this board state
        state = board.get_state()
        pieces_and_moves = state.pieces_and_moves_by_team.get(team)
        if not pieces_and_moves:
            # We have no valid moves!
            if allow_the_empty_move:
                # There are no valid moves, but we still want to return
                # the score for this position.
                score = get_board_score(None)
                return [(None, score)]
            else:
                return []

        # For each valid move, make a copy of the board, make the move on
        # that board, then evaluate the resulting position and assign its
        # score to that move
        moves_and_scores = []
        for piece, moves in pieces_and_moves:
            for move in moves:
                piece_move = PieceMove(piece, move)
                score = get_board_score(piece_move)
                moves_and_scores.append((piece_move, score))

        # Sort moves by score, best to worst
        moves_and_scores.sort(key=lambda t: t[1], reverse=True)
        return moves_and_scores


AI_TYPES = {
    'futureseeker': FutureSeekerAI,
}
DEFAULT_AI_TYPE = next(iter(AI_TYPES))
