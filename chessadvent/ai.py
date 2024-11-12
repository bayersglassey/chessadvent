from typing import List, Tuple, Set

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
        >>> ai = AI(1)

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

    """

    piece_scores = PIECE_SCORES

    def __init__(self, team: Team):
        self.team = team

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

    def find_next_moves(self, board: Board, *, for_piece: Tuple[int, int] = None) -> List[Tuple[PieceMove, Score]]:
        """Find our next possible moves for the given board, sorted by score
        (highest first)"""

        state = board.get_state()

        if self.team not in state.pieces_and_moves_by_team:
            # We have no valid moves!
            return []

        pieces_and_moves = state.pieces_and_moves_by_team[self.team]
        if for_piece is not None:
            # Filter pieces_and_moves so it only contains one entry, for
            # the indicated piece
            x, y = for_piece
            for piece, moves in pieces_and_moves:
                if piece.x == x and piece.y == y:
                    break
            else:
                raise Exception(f"No piece at {(x, y)}!")
            pieces_and_moves = [(piece, moves)]

        moves_and_scores = []
        for piece, moves in pieces_and_moves:
            for move in moves:
                new_board = board.copy_for_trying_out_moves()
                piece_move = PieceMove(piece, move)
                new_board.apply(piece_move)
                new_state = new_board.get_state()
                score = self.get_state_score(new_state)
                moves_and_scores.append((piece_move, score))

        moves_and_scores.sort(key=lambda t: t[1], reverse=True)
        return moves_and_scores
