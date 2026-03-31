"""
محرك الذكاء الاصطناعي المتقدم للعبة الداما
"""
import math
import time
import random
import hashlib
from collections import defaultdict

try:
    from draughts import Board, WHITE, BLACK
    DRAUGHTS_AVAILABLE = True
except ImportError:
    DRAUGHTS_AVAILABLE = False
    WHITE, BLACK = 2, 1

# ════════════════════════════════════════════
# ثوابت النظام
# ════════════════════════════════════════════
INF            = math.inf
MATE_SCORE     = 1_000_000
TT_MAX_SIZE    = 500_000
KILLER_SLOTS   = 2
MAX_DEPTH      = 20
NULL_MOVE_R    = 2
LMR_MIN_DEPTH  = 3
LMR_MIN_MOVES  = 4

# ════════════════════════════════════════════
# ثوابت التقييم
# ════════════════════════════════════════════
PIECE_VALUE     = 100
KING_VALUE      = 310
TEMPO_BONUS     = 11
CENTER_BONUS    = 17
INNER_CENTER_B  = 28
ADVANCEMENT_B   = 6
BACK_ROW_BONUS  = 14
KING_CENTER_B   = 22
MOBILITY_W      = 4
ENDGAME_KING_B  = 35
TRIANGLE_BONUS  = 15
BRIDGE_BONUS    = 12
DOUBLE_CORNER_B = 18
TRADE_BONUS     = 8

# مربعات استراتيجية
CENTER_SQUARES = {10, 11, 14, 15, 18, 19, 22, 23}
INNER_CENTER   = {14, 15, 18, 19}
WHITE_BACK_ROW = {29, 30, 31, 32}
BLACK_BACK_ROW = {1, 2, 3, 4}
CORNER_SQ      = {1, 4, 29, 32}
DOUBLE_CORNER  = {4, 29}
EDGE_SQUARES   = {5, 13, 21, 9, 17, 25}

# ════════════════════════════════════════════
# جداول الموضع
# ════════════════════════════════════════════
WHITE_MAN_TABLE = {
    1: 0,  2: 0,  3: 0,  4: 0,
    5: 4,  6: 4,  7: 4,  8: 4,
    9: 6,  10: 8, 11: 8, 12: 6,
    13: 8, 14:12, 15:12, 16: 8,
    17:10, 18:14, 19:14, 20:10,
    21:10, 22:12, 23:12, 24:10,
    25:12, 26:10, 27:10, 28:12,
    29:18, 30:18, 31:18, 32:18,
}

BLACK_MAN_TABLE = {
    32: 0, 31: 0, 30: 0, 29: 0,
    28: 4, 27: 4, 26: 4, 25: 4,
    24: 6, 23: 8, 22: 8, 21: 6,
    20: 8, 19:12, 18:12, 17: 8,
    16:10, 15:14, 14:14, 13:10,
    12:10, 11:12, 10:12,  9:10,
     8:12,  7:10,  6:10,  5:12,
     4:18,  3:18,  2:18,  1:18,
}

KING_TABLE = {
    1: 2,  2: 2,  3: 2,  4: 2,
    5: 2,  6: 4,  7: 4,  8: 2,
    9: 2, 10: 6, 11: 6, 12: 2,
    13: 2, 14: 8, 15: 8, 16: 2,
    17: 2, 18: 8, 19: 8, 20: 2,
    21: 2, 22: 6, 23: 6, 24: 2,
    25: 2, 26: 4, 27: 4, 28: 2,
    29: 2, 30: 2, 31: 2, 32: 2,
}

# ════════════════════════════════════════════
# كتاب الافتتاحيات
# ════════════════════════════════════════════
OPENING_BOOK = {
    "W:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "23-19", "22-18", "24-20", "21-17",
    ],
}


# ════════════════════════════════════════════
# استثناء انتهاء الوقت
# ════════════════════════════════════════════
class SearchTimeout(Exception):
    pass


# ════════════════════════════════════════════
# Zobrist Hashing
# ════════════════════════════════════════════
class ZobristHasher:
    def __init__(self):
        rng = random.Random(0xDEADBEEF)
        self.table = {
            sq: [rng.getrandbits(64) for _ in range(4)]
            for sq in range(1, 33)
        }
        self.turn_hash = rng.getrandbits(64)

    def hash_position(self, white_pieces, black_pieces, turn_white: bool) -> int:
        h = 0
        for sq, is_king in white_pieces:
            if 1 <= sq <= 32:
                h ^= self.table[sq][1 if is_king else 0]
        for sq, is_king in black_pieces:
            if 1 <= sq <= 32:
                h ^= self.table[sq][3 if is_king else 2]
        if turn_white:
            h ^= self.turn_hash
        return h


_zobrist = ZobristHasher()


# ════════════════════════════════════════════
# Transposition Table
# ════════════════════════════════════════════
class TranspositionTable:
    EXACT = 0
    LOWER = 1
    UPPER = 2

    def __init__(self, max_size: int = TT_MAX_SIZE):
        self.max_size = max_size
        self.table: dict = {}
        self.hits = 0
        self.stores = 0

    def lookup(self, key: int, depth: int, alpha: float, beta: float):
        entry = self.table.get(key)
        if entry is None:
            return None
        stored_depth, score, flag, _ = entry
        if stored_depth < depth:
            return None
        self.hits += 1
        if flag == self.EXACT:
            return score
        if flag == self.LOWER and score >= beta:
            return score
        if flag == self.UPPER and score <= alpha:
            return score
        return None

    def store(self, key: int, depth: int, score: float,
              flag: int, best_move_str=None):
        if len(self.table) >= self.max_size:
            keys = list(self.table.keys())
            for k in random.sample(keys, max(1, len(keys) // 4)):
                del self.table[k]
        self.table[key] = (depth, score, flag, best_move_str)
        self.stores += 1

    def get_best_move_str(self, key: int):
        entry = self.table.get(key)
        return entry[3] if entry else None

    def clear(self):
        self.table.clear()
        self.hits = 0
        self.stores = 0

    @property
    def size(self):
        return len(self.table)


# ════════════════════════════════════════════
# Move Ordering Data
# ════════════════════════════════════════════
class MoveOrderingData:
    def __init__(self):
        self.killers: dict = defaultdict(lambda: [None] * KILLER_SLOTS)
        self.history: dict = defaultdict(int)

    def add_killer(self, depth: int, move_str: str):
        killers = self.killers[depth]
        if move_str != killers[0]:
            killers[1] = killers[0]
            killers[0] = move_str

    def add_history(self, move_str: str, depth: int):
        self.history[move_str] += depth * depth

    def is_killer(self, depth: int, move_str: str) -> bool:
        return move_str in self.killers[depth]

    def clear(self):
        self.killers.clear()
        self.history.clear()


# ════════════════════════════════════════════
# Singletons
# ════════════════════════════════════════════
_tt    = TranspositionTable()
_order = MoveOrderingData()


# ════════════════════════════════════════════
# API عامة - تُصدَّر لـ app.py
# ════════════════════════════════════════════
def clear_transposition_table():
    """مسح جدول التحويل وبيانات الترتيب"""
    _tt.clear()
    _order.clear()


def get_tt_stats() -> dict:
    """إحصائيات Transposition Table"""
    total = max(1, _tt.hits + _tt.stores)
    return {
        "size":     _tt.size,
        "hits":     _tt.hits,
        "stores":   _tt.stores,
        "hit_rate": f"{100 * _tt.hits / total:.1f}%",
    }


# ════════════════════════════════════════════
# دوال المساعدة للرقعة
# ════════════════════════════════════════════
def get_legal_moves(board) -> list:
    try:
        moves = board.legal_moves
        return list(moves() if callable(moves) else moves)
    except Exception:
        return []


def get_board_fen(board) -> str:
    try:
        fen = board.fen
        return fen() if callable(fen) else str(fen)
    except Exception:
        return ""


def format_move_to_string(move) -> str:
    """تحويل الحركة لنص أرقام المربعات"""
    try:
        if hasattr(move, 'steps_move') and move.steps_move:
            steps = list(move.steps_move)
            if len(steps) >= 2:
                sep = "x" if _is_capture(move) else "-"
                return sep.join(str(s) for s in steps)
        if hasattr(move, 'pdn_move') and move.pdn_move:
            pdn = str(move.pdn_move)
            if any(c.isdigit() for c in pdn):
                return pdn
        s = str(move)
        if any(c.isdigit() for c in s):
            return s
    except Exception:
        pass
    return "?"


def _is_capture(move) -> bool:
    """هل الحركة أكل؟"""
    try:
        if hasattr(move, 'captures') and move.captures:
            return True
        if hasattr(move, 'is_capture') and move.is_capture:
            return True
        s = str(move)
        return 'x' in s or 'X' in s
    except Exception:
        return False


def _is_promotion(move) -> bool:
    """هل الحركة تتويج؟"""
    try:
        return bool(getattr(move, 'is_promotion', False))
    except Exception:
        return False


def parse_fen_pieces(fen_str: str):
    """
    تحليل FEN وإرجاع:
    - white_pieces: list of (square, is_king)
    - black_pieces: list of (square, is_king)
    """
    try:
        if not fen_str:
            return [], []
        parts = fen_str.split(':')
        if len(parts) < 3:
            return [], []

        def parse_side(s: str):
            pieces = []
            if s and s[0] in ('W', 'B', 'w', 'b'):
                s = s[1:]
            for token in s.split(','):
                token = token.strip()
                if not token:
                    continue
                is_king = token.startswith('K')
                try:
                    sq = int(token[1:] if is_king else token)
                    pieces.append((sq, is_king))
                except ValueError:
                    continue
            return pieces

        return parse_side(parts[1]), parse_side(parts[2])
    except Exception:
        return [], []


def _game_phase(total_pieces: int) -> float:
    """
    مرحلة اللعبة:
    1.0=افتتاح | 0.5=وسط | 0.0=نهاية
    """
    if total_pieces >= 20:
        return 1.0
    if total_pieces >= 10:
        return 0.5
    return 0.0


def _phase_label(phase: float) -> str:
    """نص مرحلة اللعبة"""
    if phase >= 0.8:
        return "افتتاح"
    if phase >= 0.4:
        return "وسط اللعبة"
    return "نهاية اللعبة"


# ════════════════════════════════════════════
# التقييم الموضعي
# ════════════════════════════════════════════
def _score_side(pieces: list, is_white: bool,
                total: int, phase: float) -> float:
    score = 0.0
    table = WHITE_MAN_TABLE if is_white else BLACK_MAN_TABLE

    for sq, is_king in pieces:
        if is_king:
            base = KING_VALUE
            base += KING_TABLE.get(sq, 0)
            if phase < 0.5:
                if sq in INNER_CENTER:
                    base += KING_CENTER_B * (1 - phase)
                elif sq in CENTER_SQUARES:
                    base += (KING_CENTER_B // 2) * (1 - phase)
            if sq in DOUBLE_CORNER and phase > 0.7:
                base += DOUBLE_CORNER_B
        else:
            base = PIECE_VALUE
            base += table.get(sq, 0)
            row = (sq - 1) // 4
            advancement = (7 - row) if is_white else row
            base += advancement * ADVANCEMENT_B
            back = WHITE_BACK_ROW if is_white else BLACK_BACK_ROW
            if sq in back:
                base += BACK_ROW_BONUS
            if sq in INNER_CENTER:
                base += INNER_CENTER_B
            elif sq in CENTER_SQUARES:
                base += CENTER_BONUS

        score += base
    return score


def _detect_structures(pieces: list) -> float:
    bonus = 0.0
    squares = {sq for sq, _ in pieces}
    if {29, 30, 31}.issubset(squares) or {30, 31, 32}.issubset(squares):
        bonus += TRIANGLE_BONUS
    kings = {sq for sq, k in pieces if k}
    if len(kings) >= 2:
        bonus += BRIDGE_BONUS
    return bonus


def evaluate_position(board, ai_color) -> float:
    """
    تقييم شامل للموقف.
    موجب = أفضل للـ AI | سالب = أفضل للخصم
    """
    legal = get_legal_moves(board)
    if not legal:
        return -MATE_SCORE if board.turn == ai_color else MATE_SCORE

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)

    if not wp and not bp:
        return 0.0

    total = len(wp) + len(bp)
    phase = _game_phase(total)

    w_score = _score_side(wp, True,  total, phase)
    b_score = _score_side(bp, False, total, phase)

    w_score += _detect_structures(wp)
    b_score += _detect_structures(bp)

    mobility = len(legal) * MOBILITY_W

    w_mat = len(wp) * PIECE_VALUE
    b_mat = len(bp) * PIECE_VALUE
    trade_bonus = 0.0
    if ai_color == WHITE and w_mat > b_mat + PIECE_VALUE:
        trade_bonus = TRADE_BONUS * (w_mat - b_mat) / PIECE_VALUE
    elif ai_color == BLACK and b_mat > w_mat + PIECE_VALUE:
        trade_bonus = TRADE_BONUS * (b_mat - w_mat) / PIECE_VALUE

    if ai_color == WHITE:
        base = w_score - b_score + trade_bonus
    else:
        base = b_score - w_score + trade_bonus

    base += mobility if board.turn == ai_color else -mobility
    base += TEMPO_BONUS if board.turn == ai_color else -TEMPO_BONUS
    return base


# ════════════════════════════════════════════
# مطابقة الحركات
# ════════════════════════════════════════════
def _find_matching_move(original_move, sim_moves: list):
    """إيجاد الحركة المكافئة في الرقعة المحاكاة"""
    if not sim_moves:
        return None

    orig_str = str(original_move)
    orig_fmt = format_move_to_string(original_move)

    for sm in sim_moves:
        if str(sm) == orig_str:
            return sm

    if hasattr(original_move, 'steps_move') and original_move.steps_move:
        orig_steps = tuple(original_move.steps_move)
        for sm in sim_moves:
            if (hasattr(sm, 'steps_move') and sm.steps_move and
                    tuple(sm.steps_move) == orig_steps):
                return sm

    if hasattr(original_move, 'pdn_move') and original_move.pdn_move:
        orig_pdn = str(original_move.pdn_move)
        for sm in sim_moves:
            if (hasattr(sm, 'pdn_move') and sm.pdn_move and
                    str(sm.pdn_move) == orig_pdn):
                return sm

    if orig_fmt and orig_fmt != "?":
        for sm in sim_moves:
            if format_move_to_string(sm) == orig_fmt:
                return sm

    return None


# ════════════════════════════════════════════
# ترتيب الحركات
# ════════════════════════════════════════════
def _move_score_for_ordering(move, depth: int, is_q: bool = False) -> int:
    score = 0
    ms = format_move_to_string(move)

    if _is_capture(move):
        score += 20_000
        if hasattr(move, 'steps_move') and move.steps_move:
            score += len(list(move.steps_move)) * 1_000

    if _is_promotion(move):
        score += 15_000

    if not is_q:
        if _order.is_killer(depth, ms):
            score += 10_000
        score += _order.history.get(ms, 0)

    if hasattr(move, 'steps_move') and move.steps_move:
        steps = list(move.steps_move)
        if steps:
            dest = steps[-1]
            if dest in INNER_CENTER:
                score += 300
            elif dest in CENTER_SQUARES:
                score += 150

    return score


def _order_moves(moves: list, depth: int, is_q: bool = False) -> list:
    try:
        return sorted(
            moves,
            key=lambda m: _move_score_for_ordering(m, depth, is_q),
            reverse=True
        )
    except Exception:
        return moves


# ════════════════════════════════════════════
# Quiescence Search
# ════════════════════════════════════════════
def quiescence(board, alpha: float, beta: float,
               ai_color, deadline=None, qdepth: int = 0) -> float:
    """بحث الهدوء - يتابع الأكل حتى الاستقرار"""
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    stand_pat = evaluate_position(board, ai_color)

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    if qdepth >= 6:
        return stand_pat

    legal = get_legal_moves(board)
    captures = [m for m in legal if _is_capture(m)]

    if not captures:
        return alpha

    captures = _order_moves(captures, 0, is_q=True)
    fen = get_board_fen(board)

    for move in captures:
        try:
            sim = Board(variant="english", fen=fen)
            sim_moves = get_legal_moves(sim)
            sim_move = _find_matching_move(move, sim_moves)
            if sim_move is None:
                continue
            sim.push(sim_move)
            score = -quiescence(
                sim, -beta, -alpha, ai_color, deadline, qdepth + 1
            )
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        except SearchTimeout:
            raise
        except Exception:
            continue

    return alpha


# ════════════════════════════════════════════
# Minimax مع Alpha-Beta
# ════════════════════════════════════════════
def minimax(board, depth: int, alpha: float, beta: float,
            maximizing: bool, ai_color,
            deadline=None, ply: int = 0) -> float:
    """
    Minimax مع:
    - Alpha-Beta Pruning
    - Transposition Table (Zobrist)
    - Killer Moves + History Heuristic
    - Late Move Reduction
    - Quiescence Search
    """
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    pos_hash = _zobrist.hash_position(wp, bp, board.turn == WHITE)

    # TT Lookup
    tt_score = _tt.lookup(pos_hash, depth, alpha, beta)
    if tt_score is not None:
        return tt_score

    legal = get_legal_moves(board)

    if not legal:
        score = (-MATE_SCORE + ply) if maximizing else (MATE_SCORE - ply)
        _tt.store(pos_hash, depth, score, TranspositionTable.EXACT)
        return score

    if depth <= 0:
        score = quiescence(board, alpha, beta, ai_color, deadline)
        _tt.store(pos_hash, 0, score, TranspositionTable.EXACT)
        return score

    # ترتيب الحركات مع TT best move أولاً
    tt_best_str = _tt.get_best_move_str(pos_hash)
    ordered = _order_moves(legal, ply)

    if tt_best_str:
        for i, m in enumerate(ordered):
            if format_move_to_string(m) == tt_best_str:
                ordered.insert(0, ordered.pop(i))
                break

    original_alpha = alpha
    best_score    = -INF if maximizing else INF
    best_move_str = None
    moves_tried   = 0

    for move in ordered:
        move_str = format_move_to_string(move)

        try:
            sim = Board(variant="english", fen=fen)
            sim_moves = get_legal_moves(sim)
            sim_move = _find_matching_move(move, sim_moves)
            if sim_move is None:
                continue
            sim.push(sim_move)
        except Exception:
            continue

        moves_tried += 1

        # Late Move Reduction
        reduction = 0
        if (moves_tried > LMR_MIN_MOVES and
                depth >= LMR_MIN_DEPTH and
                not _is_capture(move) and
                not _is_promotion(move) and
                not _order.is_killer(ply, move_str)):
            reduction = 1
            if moves_tried > LMR_MIN_MOVES * 3:
                reduction = 2

        if maximizing:
            score = minimax(
                sim, depth - 1 - reduction,
                alpha, beta, False, ai_color, deadline, ply + 1
            )
            if reduction > 0 and alpha < score < beta:
                score = minimax(
                    sim, depth - 1,
                    alpha, beta, False, ai_color, deadline, ply + 1
                )
            if score > best_score:
                best_score    = score
                best_move_str = move_str
            alpha = max(alpha, score)
        else:
            score = minimax(
                sim, depth - 1 - reduction,
                alpha, beta, True, ai_color, deadline, ply + 1
            )
            if reduction > 0 and alpha < score < beta:
                score = minimax(
                    sim, depth - 1,
                    alpha, beta, True, ai_color, deadline, ply + 1
                )
            if score < best_score:
                best_score    = score
                best_move_str = move_str
            beta = min(beta, score)

        if beta <= alpha:
            if not _is_capture(move):
                _order.add_killer(ply, move_str)
                _order.add_history(move_str, depth)
            break

    # TT Store
    if best_score <= original_alpha:
        flag = TranspositionTable.UPPER
    elif best_score >= beta:
        flag = TranspositionTable.LOWER
    else:
        flag = TranspositionTable.EXACT

    _tt.store(pos_hash, depth, best_score, flag, best_move_str)
    return best_score


# ════════════════════════════════════════════
# البحث الرئيسي
# ════════════════════════════════════════════
def find_best_move(original_board, ai_color,
                   max_depth: int = MAX_DEPTH,
                   time_limit: float = 5.0):
    """
    Iterative Deepening Minimax.
    Returns: (best_move, best_score, reached_depth)
    """
    legal = get_legal_moves(original_board)
    if not legal:
        return None, 0, 0
    if len(legal) == 1:
        return legal[0], 0, 1

    original_fen = get_board_fen(original_board)

    # كتاب الافتتاحيات
    book_moves = OPENING_BOOK.get(original_fen.strip())
    if book_moves:
        book_str = random.choice(book_moves)
        for m in legal:
            if format_move_to_string(m) == book_str:
                return m, 0, 0

    ordered      = _order_moves(legal, 0)
    best_move    = ordered[0]
    best_score   = -INF
    reached      = 0
    start        = time.time()
    deadline     = start + time_limit

    for depth in range(1, max_depth + 1):
        if time.time() - start > time_limit * 0.88:
            break

        try:
            d_best  = None
            d_score = -INF
            alpha   = -INF
            beta    = INF

            for move in ordered:
                try:
                    sim = Board(variant="english", fen=original_fen)
                    sim_moves = get_legal_moves(sim)
                    sim_move = _find_matching_move(move, sim_moves)
                    if sim_move is None:
                        continue
                    sim.push(sim_move)
                    score = minimax(
                        sim, depth - 1,
                        alpha, beta,
                        False, ai_color,
                        deadline, ply=1
                    )
                except SearchTimeout:
                    raise
                except Exception:
                    continue

                if score > d_score:
                    d_score = score
                    d_best  = move
                alpha = max(alpha, score)

            if d_best is not None:
                best_move  = d_best
                best_score = d_score
                reached    = depth
                # إعادة ترتيب: أفضل حركة أولاً
                if d_best in ordered:
                    ordered.remove(d_best)
                    ordered.insert(0, d_best)

            if abs(best_score) > MATE_SCORE // 2:
                break

        except SearchTimeout:
            break

    return best_move, best_score, reached


# ════════════════════════════════════════════
# تحليل الموقف (للمساعد الذكي)
# ════════════════════════════════════════════
def _detect_threats(board, player_color, ai_color, fen, wp, bp) -> list:
    """كشف التهديدات الفورية"""
    threats = []

    legal    = get_legal_moves(board)
    captures = [m for m in legal if _is_capture(m)]
    if captures:
        threats.append(f"⚔️ أكل مجبر: {len(captures)} خيار متاح")

    # قطع قريبة من التتويج
    if player_color == WHITE:
        near = [sq for sq, k in wp if not k and (sq - 1) // 4 <= 1]
    else:
        near = [sq for sq, k in bp if not k and (sq - 1) // 4 >= 6]
    if near:
        threats.append(f"👑 قطعة قريبة من التتويج: مربع {near}")

    # خصم قريب من التتويج
    if ai_color == WHITE:
        enemy = [sq for sq, k in wp if not k and (sq - 1) // 4 <= 1]
    else:
        enemy = [sq for sq, k in bp if not k and (sq - 1) // 4 >= 6]
    if enemy:
        threats.append(f"🚨 قطعة خصم قريبة من التتويج! {enemy}")

    return threats if threats else ["✅ لا تهديدات فورية"]


def _get_advantage_text(score: float) -> str:
    a = abs(score)
    if a < 50:
        return "⚖️ تعادل تام"
    who = "اللاعب" if score > 0 else "الكمبيوتر"
    if a < 150:
        return f"🟡 تفوق طفيف لـ {who}"
    if a < 350:
        return f"🟠 تفوق واضح لـ {who}"
    if a < 700:
        return f"🔴 تفوق كبير لـ {who}"
    return f"💀 هيمنة كاملة لـ {who}"


def _score_label(score: float) -> str:
    if score > MATE_SCORE // 2:
        return "فوز مؤكد ✅"
    if score < -MATE_SCORE // 2:
        return "خسارة محتملة ❌"
    if abs(score) < 50:
        return "متعادل ⚖️"
    return "أفضل 🟢" if score > 0 else "أسوأ 🔴"


def _generate_recommendation(best_move, best_score,
                              move_scores, threats,
                              phase, wp, bp) -> str:
    """توليد نصيحة ذكية"""
    lines = []
    best_str = format_move_to_string(best_move)

    if best_score > MATE_SCORE // 2:
        lines.append(f"🏆 **الحركة {best_str} تضمن الفوز!**")
    elif best_score < -MATE_SCORE // 2:
        lines.append(f"😰 **الموقف صعب، أفضل ما يمكن: {best_str}**")
    elif _is_capture(best_move):
        lines.append(f"⚔️ **الأفضل هو الأكل: {best_str}**")
    elif _is_promotion(best_move):
        lines.append(f"👑 **تتويج قطعة بـ: {best_str}!**")
    else:
        lines.append(f"♟️ **الحركة المثلى: {best_str}**")

    for t in threats:
        if "🚨" in t or "⚠️" in t:
            lines.append(t)

    if phase >= 0.8:
        lines.append("📚 *سيطر على المركز وحافظ على الصف الخلفي*")
    elif phase >= 0.4:
        lines.append("⚔️ *ابحث عن سلاسل أكل وحافظ على التماسك*")
    else:
        lines.append("🎯 *الملوك أقوى في النهاية - اسعَ للتتويج*")

    if len(move_scores) > 1:
        diff = move_scores[0][1] - move_scores[1][1]
        if diff > 100:
            lines.append(f"⭐ هذه الحركة أفضل بكثير من البديل (+{diff:.0f})")
        elif diff < 20:
            alt = format_move_to_string(move_scores[1][0])
            lines.append(f"💡 بديل قريب: **{alt}** (فرق {diff:.0f} نقطة)")

    return "\n".join(lines)


def analyze_position(board, player_color, ai_color,
                     depth: int = 8,
                     time_limit: float = 5.0) -> dict:
    """
    تحليل شامل للموقف.
    Returns dict مع: best_move, score, top_moves, threats,
                     phase, advantage, recommendation
    """
    legal = get_legal_moves(board)
    if not legal:
        return {"error": "لا توجد حركات"}

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    total  = len(wp) + len(bp)
    phase  = _game_phase(total)

    original_fen = fen
    move_scores  = []
    deadline     = time.time() + time_limit
    ordered      = _order_moves(legal, 0)

    for move in ordered:
        try:
            sim = Board(variant="english", fen=original_fen)
            sim_moves = get_legal_moves(sim)
            sim_move  = _find_matching_move(move, sim_moves)
            if sim_move is None:
                continue
            sim.push(sim_move)
            score = minimax(
                sim, depth - 1,
                -INF, INF,
                False, player_color,
                deadline, ply=1
            )
            move_scores.append((move, score))
        except SearchTimeout:
            break
        except Exception:
            continue

    if not move_scores:
        # fallback: تقييم سريع
        for move in ordered[:5]:
            try:
                sim = Board(variant="english", fen=original_fen)
                sim_moves = get_legal_moves(sim)
                sim_move  = _find_matching_move(move, sim_moves)
                if sim_move is None:
                    continue
                sim.push(sim_move)
                score = evaluate_position(sim, player_color)
                move_scores.append((move, score))
            except Exception:
                continue

    if not move_scores:
        return {"error": "فشل التحليل"}

    move_scores.sort(key=lambda x: x[1], reverse=True)
    best_move, best_score = move_scores[0]

    threats = _detect_threats(board, player_color, ai_color, fen, wp, bp)
    advantage = _get_advantage_text(best_score)

    recommendation = _generate_recommendation(
        best_move, best_score, move_scores,
        threats, phase, wp, bp
    )

    top3 = [
        {
            "move":  format_move_to_string(m),
            "score": s,
            "label": _score_label(s),
        }
        for m, s in move_scores[:3]
    ]

    return {
        "best_move":      best_move,
        "best_move_str":  format_move_to_string(best_move),
        "score":          best_score,
        "reached_depth":  depth,
        "top_moves":      top3,
        "threats":        threats,
        "phase":          _phase_label(phase),
        "phase_value":    phase,
        "advantage":      advantage,
        "recommendation": recommendation,
        "piece_balance":  len(wp) - len(bp),
        "total_pieces":   total,
    }
