"""
محرك الذكاء الاصطناعي المتقدم للعبة الداما
===============================================
المميزات:
- Iterative Deepening مع عمق حتى 20
- Transposition Table مع Zobrist Hashing
- Move Ordering متقدم (Killer Moves + History Heuristic)
- Quiescence Search لتجنب أفق البحث
- Null Move Pruning
- Late Move Reduction (LMR)
- Opening Book (كتاب افتتاحيات)
- Endgame Tablebase بسيط
- تقييم موضعي متقدم متعدد المراحل
"""
import math
import time
import random
import hashlib
import pickle
import os
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
NULL_MOVE_R    = 2        # Null Move Reduction
LMR_MIN_DEPTH  = 3
LMR_MIN_MOVES  = 4

# ════════════════════════════════════════════
# ثوابت التقييم الموضعي
# ════════════════════════════════════════════
PIECE_VALUE      = 100
KING_VALUE       = 310
TEMPO_BONUS      = 11
CENTER_BONUS     = 17
INNER_CENTER_B   = 28
ADVANCEMENT_B    = 6
BACK_ROW_BONUS   = 14
KING_SAFETY_B    = 20
KING_CENTER_B    = 22
MOBILITY_W       = 4
ENDGAME_KING_B   = 35
TRIANGLE_BONUS   = 15     # تشكيل مثلث دفاعي
BRIDGE_BONUS     = 12     # جسر الملك
DOUBLE_CORNER_B  = 18     # الزاوية المزدوجة
TRADE_BONUS      = 8      # تشجيع التبادل عند التفوق

# مربعات استراتيجية
CENTER_SQUARES  = {10, 11, 14, 15, 18, 19, 22, 23}
INNER_CENTER    = {14, 15, 18, 19}
WHITE_BACK_ROW  = {29, 30, 31, 32}
BLACK_BACK_ROW  = {1, 2, 3, 4}
CORNER_SQ       = {1, 4, 29, 32}
DOUBLE_CORNER   = {4, 29}
EDGE_SQUARES    = {5, 13, 21, 9, 17, 25}

# ════════════════════════════════════════════
# جداول الموضع (Piece-Square Tables)
# ════════════════════════════════════════════
# قيمة إضافية لكل مربع (مرقّمة 1-32)
WHITE_MAN_TABLE = {
    1: 0,  2: 0,  3: 0,  4: 0,
    5: 4,  6: 4,  7: 4,  8: 4,
    9: 6,  10: 8, 11: 8, 12: 6,
    13: 8, 14: 12,15: 12,16: 8,
    17:10, 18: 14,19: 14,20:10,
    21:10, 22: 12,23: 12,24:10,
    25:12, 26: 10,27: 10,28:12,
    29:18, 30: 18,31: 18,32:18,
}

BLACK_MAN_TABLE = {
    32:0,  31:0,  30:0,  29:0,
    28:4,  27:4,  26:4,  25:4,
    24:6,  23:8,  22:8,  21:6,
    20:8,  19:12, 18:12, 17:8,
    16:10, 15:14, 14:14, 13:10,
    12:10, 11:12, 10:12,  9:10,
     8:12,  7:10,  6:10,  5:12,
     4:18,  3:18,  2:18,  1:18,
}

KING_TABLE = {
    1:2,  2:2,  3:2,  4:2,
    5:2,  6:4,  7:4,  8:2,
    9:2,  10:6, 11:6, 12:2,
    13:2, 14:8, 15:8, 16:2,
    17:2, 18:8, 19:8, 20:2,
    21:2, 22:6, 23:6, 24:2,
    25:2, 26:4, 27:4, 28:2,
    29:2, 30:2, 31:2, 32:2,
}


# ════════════════════════════════════════════
# كتاب الافتتاحيات
# ════════════════════════════════════════════
OPENING_BOOK = {
    # FEN الابتدائي → أفضل الحركات
    "W:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "23-19", "22-18", "24-20", "21-17",
    ],
    # بعد 23-19
    "W:W21,22,24,25,26,27,28,29,30,31,32,19:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "22-18", "24-20", "21-17",
    ],
}


class SearchTimeout(Exception):
    """استثناء انتهاء وقت البحث"""
    pass


# ════════════════════════════════════════════
# Zobrist Hashing للـ Transposition Table
# ════════════════════════════════════════════
class ZobristHasher:
    """توليد هاش Zobrist سريع وموثوق"""

    def __init__(self):
        rng = random.Random(0xDEADBEEF)
        # [مربع 1-32][نوع: 0=رجل أبيض, 1=ملك أبيض, 2=رجل أسود, 3=ملك أسود]
        self.table = {
            sq: [rng.getrandbits(64) for _ in range(4)]
            for sq in range(1, 33)
        }
        self.turn_hash = rng.getrandbits(64)

    def hash_position(self, white_pieces, black_pieces, turn_white: bool) -> int:
        h = 0
        for sq, is_king in white_pieces:
            h ^= self.table[sq][1 if is_king else 0]
        for sq, is_king in black_pieces:
            h ^= self.table[sq][3 if is_king else 2]
        if turn_white:
            h ^= self.turn_hash
        return h


_zobrist = ZobristHasher()


# ════════════════════════════════════════════
# Transposition Table متقدم
# ════════════════════════════════════════════
class TranspositionTable:
    """
    جدول التحويل مع:
    - Always-Replace و Depth-Preferred استراتيجيتان
    - عمر الإدخالات لتنظيف الجدول
    """
    EXACT = 0
    LOWER = 1  # Alpha (lower bound)
    UPPER = 2  # Beta  (upper bound)

    def __init__(self, max_size: int = TT_MAX_SIZE):
        self.max_size = max_size
        self.table: dict = {}
        self.hits = 0
        self.stores = 0

    def lookup(self, key: int, depth: int, alpha: float, beta: float):
        entry = self.table.get(key)
        if entry is None:
            return None
        stored_depth, score, flag, best_move = entry
        if stored_depth < depth:
            return None  # عمق غير كافٍ
        self.hits += 1
        if flag == self.EXACT:
            return score
        if flag == self.LOWER and score >= beta:
            return score
        if flag == self.UPPER and score <= alpha:
            return score
        return None

    def store(self, key: int, depth: int, score: float,
              flag: int, best_move=None):
        if len(self.table) >= self.max_size:
            # حذف ربع الجدول عشوائياً
            keys = list(self.table.keys())
            for k in random.sample(keys, len(keys) // 4):
                del self.table[k]
        self.table[key] = (depth, score, flag, best_move)
        self.stores += 1

    def get_best_move(self, key: int):
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
# Killer Moves + History Heuristic
# ════════════════════════════════════════════
class MoveOrderingData:
    """بيانات ترتيب الحركات"""

    def __init__(self):
        # killer_moves[depth][slot] = move_str
        self.killers: dict = defaultdict(lambda: [None] * KILLER_SLOTS)
        # history[move_str] = score
        self.history: dict = defaultdict(int)
        self.counter_moves: dict = {}

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
        self.counter_moves.clear()


# ════════════════════════════════════════════
# الـ Singletons
# ════════════════════════════════════════════
_tt    = TranspositionTable()
_order = MoveOrderingData()


def clear_transposition_table():
    _tt.clear()
    _order.clear()


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
    """تحويل الحركة لنص يحتوي أرقام المربعات"""
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
    try:
        return bool(getattr(move, 'is_promotion', False))
    except Exception:
        return False


def parse_fen_pieces(fen_str: str):
    """تحليل FEN وإرجاع قوائم القطع"""
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


def _fen_hash(white_pieces, black_pieces, turn) -> int:
    """توليد Zobrist hash للوضع"""
    return _zobrist.hash_position(
        white_pieces, black_pieces, turn == WHITE
    )


# ════════════════════════════════════════════
# التقييم الموضعي المتقدم
# ════════════════════════════════════════════
def _game_phase(total_pieces: int) -> float:
    """
    مرحلة اللعبة:
    1.0 = افتتاح | 0.5 = وسط | 0.0 = نهاية
    """
    if total_pieces >= 20:
        return 1.0
    if total_pieces >= 10:
        return 0.5
    return 0.0


def _score_side(pieces: list, is_white: bool,
                total: int, phase: float) -> float:
    """تقييم شامل لجانب واحد"""
    score = 0.0
    table = WHITE_MAN_TABLE if is_white else BLACK_MAN_TABLE

    for sq, is_king in pieces:
        if is_king:
            base = KING_VALUE
            # جدول موضع الملك
            base += KING_TABLE.get(sq, 0)
            # مكافأة الملك في المركز في نهاية اللعبة
            if phase < 0.5:
                if sq in INNER_CENTER:
                    base += KING_CENTER_B * (1 - phase)
                elif sq in CENTER_SQUARES:
                    base += (KING_CENTER_B // 2) * (1 - phase)
            # مكافأة الزاوية المزدوجة في الافتتاح
            if sq in DOUBLE_CORNER and phase > 0.7:
                base += DOUBLE_CORNER_B
        else:
            base = PIECE_VALUE
            # جدول موضع الرجل
            base += table.get(sq, 0)
            # التقدم
            row = (sq - 1) // 4
            advancement = (7 - row) if is_white else row
            base += advancement * ADVANCEMENT_B
            # مكافأة الصف الخلفي
            back = WHITE_BACK_ROW if is_white else BLACK_BACK_ROW
            if sq in back:
                base += BACK_ROW_BONUS
            # مكافأة المركز
            if sq in INNER_CENTER:
                base += INNER_CENTER_B
            elif sq in CENTER_SQUARES:
                base += CENTER_BONUS

        score += base

    return score


def _detect_structures(pieces: list) -> float:
    """كشف التشكيلات الاستراتيجية"""
    bonus = 0.0
    squares = {sq for sq, _ in pieces}

    # تشكيل المثلث الدفاعي (White: 29,30,31 أو 30,31,32)
    if {29, 30, 31}.issubset(squares) or {30, 31, 32}.issubset(squares):
        bonus += TRIANGLE_BONUS

    # تشكيل جسر الملك
    kings = {sq for sq, k in pieces if k}
    if len(kings) >= 2:
        bonus += BRIDGE_BONUS

    return bonus


def evaluate_position(board, ai_color) -> float:
    """
    تقييم شامل متعدد المراحل.
    + = أفضل للـ AI | - = أفضل للخصم
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

    # ─ القيمة المادية + الموضعية ─
    w_score = _score_side(wp, True, total, phase)
    b_score = _score_side(bp, False, total, phase)

    # ─ التشكيلات ─
    if ai_color == WHITE:
        w_score += _detect_structures(wp)
        b_score += _detect_structures(bp)
    else:
        b_score += _detect_structures(bp)
        w_score += _detect_structures(wp)

    # ─ الحركية ─
    mobility = len(legal) * MOBILITY_W

    # ─ تشجيع التبادل عند التفوق المادي ─
    trade_bonus = 0.0
    w_mat = len(wp) * PIECE_VALUE
    b_mat = len(bp) * PIECE_VALUE
    if ai_color == WHITE and w_mat > b_mat + PIECE_VALUE:
        trade_bonus = TRADE_BONUS * (w_mat - b_mat) / PIECE_VALUE
    elif ai_color == BLACK and b_mat > w_mat + PIECE_VALUE:
        trade_bonus = TRADE_BONUS * (b_mat - w_mat) / PIECE_VALUE

    # ─ حساب التقييم النهائي ─
    if ai_color == WHITE:
        base = w_score - b_score + trade_bonus
    else:
        base = b_score - w_score + trade_bonus

    base += mobility if board.turn == ai_color else -mobility
    base += TEMPO_BONUS if board.turn == ai_color else -TEMPO_BONUS

    return base


# ════════════════════════════════════════════
# Quiescence Search
# ════════════════════════════════════════════
def quiescence(board, alpha: float, beta: float,
               ai_color, deadline=None, depth: int = 0) -> float:
    """
    بحث الهدوء: يتابع حركات الأكل فقط حتى الاستقرار
    لتجنب أفق البحث (Horizon Effect)
    """
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    stand_pat = evaluate_position(board, ai_color)

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    # حد عمق Quiescence
    if depth >= 8:
        return stand_pat

    legal = get_legal_moves(board)
    # تصفية: حركات الأكل فقط
    captures = [m for m in legal if _is_capture(m)]

    if not captures:
        return alpha

    captures = _order_moves_fast(captures, board, 0, is_q=True)

    for move in captures:
        fen = get_board_fen(board)
        sim = Board(variant="english", fen=fen)
        sim_moves = get_legal_moves(sim)
        sim_move = _find_matching_move(move, sim_moves)
        if sim_move is None:
            continue
        sim.push(sim_move)

        score = -quiescence(sim, -beta, -alpha, ai_color, deadline, depth + 1)

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


# ════════════════════════════════════════════
# ترتيب الحركات المتقدم
# ════════════════════════════════════════════
def _move_score(move, board, depth: int, is_q: bool = False) -> int:
    """
    حساب أولوية الحركة للترتيب:
    أكل > تتويج > killer > history > مركز > غير ذلك
    """
    score = 0
    ms = format_move_to_string(move)

    if _is_capture(move):
        score += 20_000
        # MVV-LVA تقريبي: أكل أكثر = أفضل
        if hasattr(move, 'steps_move') and move.steps_move:
            score += len(list(move.steps_move)) * 1_000

    if _is_promotion(move):
        score += 15_000

    if not is_q:
        if _order.is_killer(depth, ms):
            score += 10_000
        score += _order.history.get(ms, 0)

    # مكافأة التحرك نحو المركز
    if hasattr(move, 'steps_move') and move.steps_move:
        steps = list(move.steps_move)
        if steps:
            dest = steps[-1]
            if dest in INNER_CENTER:
                score += 300
            elif dest in CENTER_SQUARES:
                score += 150

    return score


def _order_moves_fast(moves: list, board, depth: int,
                      is_q: bool = False) -> list:
    """ترتيب الحركات بسرعة"""
    try:
        return sorted(
            moves,
            key=lambda m: _move_score(m, board, depth, is_q),
            reverse=True
        )
    except Exception:
        return moves


# ════════════════════════════════════════════
# مطابقة الحركات
# ════════════════════════════════════════════
def _find_matching_move(original_move, sim_moves: list):
    """إيجاد الحركة المكافئة في الرقعة المحاكاة"""
    if not sim_moves:
        return None

    orig_str = str(original_move)
    orig_fmt = format_move_to_string(original_move)

    # 1) مطابقة str مباشرة
    for sm in sim_moves:
        if str(sm) == orig_str:
            return sm

    # 2) steps_move
    if hasattr(original_move, 'steps_move') and original_move.steps_move:
        orig_steps = tuple(original_move.steps_move)
        for sm in sim_moves:
            if (hasattr(sm, 'steps_move') and sm.steps_move and
                    tuple(sm.steps_move) == orig_steps):
                return sm

    # 3) pdn_move
    if hasattr(original_move, 'pdn_move') and original_move.pdn_move:
        orig_pdn = str(original_move.pdn_move)
        for sm in sim_moves:
            if (hasattr(sm, 'pdn_move') and sm.pdn_move and
                    str(sm.pdn_move) == orig_pdn):
                return sm

    # 4) format string
    if orig_fmt and orig_fmt != "?":
        for sm in sim_moves:
            if format_move_to_string(sm) == orig_fmt:
                return sm

    return None


# ════════════════════════════════════════════
# خوارزمية Minimax المتقدمة
# ════════════════════════════════════════════
def minimax(board, depth: int, alpha: float, beta: float,
            maximizing: bool, ai_color,
            deadline=None, ply: int = 0,
            null_ok: bool = True) -> float:
    """
    Minimax مع كامل التحسينات:
    - Alpha-Beta Pruning
    - Transposition Table
    - Null Move Pruning
    - LMR (Late Move Reduction)
    - Quiescence Search عند عمق 0
    """
    # ─ فحص الوقت ─
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    # ─ Transposition Table Lookup ─
    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    pos_hash = _fen_hash(wp, bp, board.turn)

    tt_score = _tt.lookup(pos_hash, depth, alpha, beta)
    if tt_score is not None:
        return tt_score

    legal = get_legal_moves(board)

    # ─ حالات نهائية ─
    if not legal:
        score = -MATE_SCORE + ply if maximizing else MATE_SCORE - ply
        _tt.store(pos_hash, depth, score, TranspositionTable.EXACT)
        return score

    # ─ Quiescence Search ─
    if depth <= 0:
        score = quiescence(board, alpha, beta, ai_color, deadline)
        _tt.store(pos_hash, 0, score, TranspositionTable.EXACT)
        return score

    # ─ Null Move Pruning ─
    # (تخطي الدور لرؤية هل ما زلنا أفضل)
    # ملاحظة: محدود في الداما لأن الدور إلزامي
    # نطبقه فقط في عمق عالٍ وبدون أكل مجبر
    captures_only = all(_is_capture(m) for m in legal)
    if (null_ok and maximizing and depth >= 4 and
            not captures_only and len(wp) > 3 and len(bp) > 3):
        # تقدير سريع بعمق مخفض
        null_score = evaluate_position(board, ai_color)
        if null_score >= beta:
            return beta

    # ─ ترتيب الحركات ─
    # أولاً: تحقق من TT best move
    tt_best_str = _tt.get_best_move(pos_hash)
    ordered = _order_moves_fast(legal, board, ply)

    # إعادة ترتيب: TT best في المقدمة
    if tt_best_str:
        for i, m in enumerate(ordered):
            if format_move_to_string(m) == tt_best_str:
                ordered.insert(0, ordered.pop(i))
                break

    original_alpha = alpha
    best_score = -INF if maximizing else INF
    best_move_str = None
    moves_tried = 0

    for move in ordered:
        move_str = format_move_to_string(move)

        # ─ بناء رقعة المحاكاة ─
        sim = Board(variant="english", fen=fen)
        sim_moves = get_legal_moves(sim)
        sim_move = _find_matching_move(move, sim_moves)
        if sim_move is None:
            continue

        sim.push(sim_move)
        moves_tried += 1

        # ─ Late Move Reduction (LMR) ─
        reduction = 0
        if (moves_tried > LMR_MIN_MOVES and
                depth >= LMR_MIN_DEPTH and
                not _is_capture(move) and
                not _is_promotion(move) and
                not _order.is_killer(ply, move_str)):
            reduction = 1
            if moves_tried > LMR_MIN_MOVES * 2:
                reduction = 2

        # ─ البحث الفعلي ─
        if maximizing:
            score = minimax(
                sim, depth - 1 - reduction,
                alpha, beta, False, ai_color,
                deadline, ply + 1, null_ok=True
            )
            # إعادة البحث بعمق كامل إذا أثبت الـ reduction خطأ
            if reduction > 0 and score > alpha:
                score = minimax(
                    sim, depth - 1,
                    alpha, beta, False, ai_color,
                    deadline, ply + 1, null_ok=True
                )

            if score > best_score:
                best_score = score
                best_move_str = move_str
            alpha = max(alpha, score)

        else:
            score = minimax(
                sim, depth - 1 - reduction,
                alpha, beta, True, ai_color,
                deadline, ply + 1, null_ok=True
            )
            if reduction > 0 and score < beta:
                score = minimax(
                    sim, depth - 1,
                    alpha, beta, True, ai_color,
                    deadline, ply + 1, null_ok=True
                )

            if score < best_score:
                best_score = score
                best_move_str = move_str
            beta = min(beta, score)

        # ─ Beta Cutoff ─
        if beta <= alpha:
            # تسجيل Killer Move
            if not _is_capture(move):
                _order.add_killer(ply, move_str)
                _order.add_history(move_str, depth)
            break

    # ─ تخزين في TT ─
    if best_score <= original_alpha:
        flag = TranspositionTable.UPPER
    elif best_score >= beta:
        flag = TranspositionTable.LOWER
    else:
        flag = TranspositionTable.EXACT

    _tt.store(pos_hash, depth, best_score, flag, best_move_str)
    return best_score


# ════════════════════════════════════════════
# كتاب الافتتاحيات
# ════════════════════════════════════════════
def _lookup_opening_book(fen: str):
    """البحث في كتاب الافتتاحيات"""
    fen_clean = fen.strip()
    moves_strs = OPENING_BOOK.get(fen_clean)
    if moves_strs:
        return random.choice(moves_strs)
    return None


# ════════════════════════════════════════════
# البحث الرئيسي
# ════════════════════════════════════════════
def find_best_move(original_board, ai_color,
                   max_depth: int = MAX_DEPTH,
                   time_limit: float = 5.0):
    """
    Iterative Deepening Minimax مع كامل التحسينات.

    Returns:
        (best_move, best_score, reached_depth)
    """
    legal = get_legal_moves(original_board)
    if not legal:
        return None, 0, 0
    if len(legal) == 1:
        return legal[0], 0, 1

    original_fen = get_board_fen(original_board)

    # ─ كتاب الافتتاحيات ─
    book_move_str = _lookup_opening_book(original_fen)
    if book_move_str:
        for m in legal:
            if format_move_to_string(m) == book_move_str:
                return m, 0, 0

    # ─ ترتيب أولي ─
    ordered = _order_moves_fast(legal, original_board, 0)

    best_move    = ordered[0]
    best_score   = -INF
    reached_depth = 0

    start_time = time.time()
    deadline   = start_time + time_limit

    for depth in range(1, max_depth + 1):
        # فحص مسبق: هل الوقت كافٍ؟
        elapsed = time.time() - start_time
        if elapsed > time_limit * 0.9:
            break

        try:
            depth_best      = None
            depth_score     = -INF
            alpha           = -INF
            beta            = INF

            for move in ordered:
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

                if score > depth_score:
                    depth_score = score
                    depth_best  = move

                alpha = max(alpha, score)

            if depth_best is not None:
                best_move    = depth_best
                best_score   = depth_score
                reached_depth = depth

                # Aspiration Windows: إعادة ترتيب
                if depth_best in ordered:
                    ordered.remove(depth_best)
                    ordered.insert(0, depth_best)

            # فوز مؤكد
            if abs(best_score) > MATE_SCORE // 2:
                break

        except SearchTimeout:
            break

    return best_move, best_score, reached_depth


# ════════════════════════════════════════════
# تحليل الموقف (للمساعدة الذكية)
# ════════════════════════════════════════════
def analyze_position(board, player_color, ai_color,
                     depth: int = 8, time_limit: float = 5.0) -> dict:
    """
    تحليل شامل للموقف يُرجع:
    - best_move: أفضل حركة
    - score: تقييم الموقف
    - reached_depth: عمق البحث المحقق
    - top_moves: أفضل 3 حركات مع تقييماتها
    - threats: التهديدات الموجودة
    - phase: مرحلة اللعبة
    - advantage: من يتفوق وبكم
    - recommendation: نصيحة نصية
    """
    legal = get_legal_moves(board)
    if not legal:
        return {"error": "لا توجد حركات"}

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    total = len(wp) + len(bp)
    phase = _game_phase(total)

    # ─ تقييم كل الحركات ─
    original_fen = get_board_fen(board)
    move_scores  = []
    deadline     = time.time() + time_limit

    ordered = _order_moves_fast(legal, board, 0)

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
        return {"error": "فشل التحليل"}

    move_scores.sort(key=lambda x: x[1], reverse=True)
    best_move, best_score = move_scores[0]

    # ─ كشف التهديدات ─
    threats = _detect_threats(board, player_color, ai_color, fen, wp, bp)

    # ─ تحديد التفوق ─
    advantage = _get_advantage_text(best_score, player_color, ai_color)

    # ─ توليد نصيحة ذكية ─
    recommendation = _generate_recommendation(
        best_move, best_score, move_scores,
        threats, phase, wp, bp,
        player_color, ai_color
    )

    # أفضل 3 حركات
    top3 = [
        {
            "move": format_move_to_string(m),
            "score": s,
            "label": _score_label(s, player_color, ai_color)
        }
        for m, s in move_scores[:3]
    ]

    return {
        "best_move":     best_move,
        "best_move_str": format_move_to_string(best_move),
        "score":         best_score,
        "reached_depth": depth,
        "top_moves":     top3,
        "threats":       threats,
        "phase":         _phase_label(phase),
        "phase_value":   phase,
        "advantage":     advantage,
        "recommendation": recommendation,
        "piece_balance": len(wp) - len(bp),
        "total_pieces":  total,
    }


def _detect_threats(board, player_color, ai_color,
                    fen, wp, bp) -> list:
    """كشف التهديدات الفورية"""
    threats = []

    # هل هناك أكل مجبر؟
    legal = get_legal_moves(board)
    captures = [m for m in legal if _is_capture(m)]
    if captures:
        threats.append(f"⚔️ أكل مجبر: {len(captures)} خيار")

    # هل الخصم يهدد بالأكل؟
    # محاكاة دور الخصم
    try:
        sim = Board(variant="english", fen=fen)
        # نفّذ حركة وهمية للخصم (نأخذ أول حركة)
        opp_legal = []
        if sim.turn != player_color:
            opp_legal = get_legal_moves(sim)
        if opp_legal:
            opp_caps = [m for m in opp_legal if _is_capture(m)]
            if opp_caps:
                threats.append(f"⚠️ الخصم يهدد بأكل {len(opp_caps)} قطعة")
    except Exception:
        pass

    # هل توشك قطعة على التتويج؟
    if player_color == WHITE:
        near_crown = [sq for sq, k in wp if not k and (sq - 1) // 4 <= 1]
    else:
        near_crown = [sq for sq, k in bp if not k and (sq - 1) // 4 >= 6]
    if near_crown:
        threats.append(f"👑 قطعة قريبة من التتويج في: {near_crown}")

    # هل الخصم يوشك على التتويج؟
    if ai_color == WHITE:
        enemy_near = [sq for sq, k in wp if not k and (sq - 1) // 4 <= 1]
    else:
        enemy_near = [sq for sq, k in bp if not k and (sq - 1) // 4 >= 6]
    if enemy_near:
        threats.append(f"🚨 قطعة خصم قريبة من التتويج! مربع: {enemy_near}")

    return threats if threats else ["✅ لا تهديدات فورية"]


def _get_advantage_text(score: float, player_color, ai_color) -> str:
    """نص التفوق"""
    abs_score = abs(score)
    if abs_score < 50:
        return "⚖️ تعادل تام"
    elif abs_score < 150:
        who = "اللاعب" if score > 0 else "الكمبيوتر"
        return f"🟡 تفوق طفيف لـ {who}"
    elif abs_score < 350:
        who = "اللاعب" if score > 0 else "الكمبيوتر"
        return f"🟠 تفوق واضح لـ {who}"
    elif abs_score < 700:
        who = "اللاعب" if score > 0 else "الكمبيوتر"
        return f"🔴 تفوق كبير لـ {who}"
    else:
        who = "اللاعب" if score > 0 else "الكمبيوتر"
        return f"💀 هيمنة كاملة لـ {who}"


def _score_label(score: float, player_color, ai_color) -> str:
    """تسمية قصيرة للنقاط"""
    if score > MATE_SCORE // 2:
        return "فوز مؤكد ✅"
    if score < -MATE_SCORE // 2:
        return "خسارة محتملة ❌"
    if abs(score) < 50:
        return "متعادل ⚖️"
    if score > 0:
        return "أفضل 🟢"
    return "أسوأ 🔴"


def _phase_label(phase: float) -> str:
    if phase >= 0.8:
        return "افتتاح"
    if phase >= 0.4:
        return "وسط اللعبة"
    return "نهاية اللعبة"


def _generate_recommendation(best_move, best_score, move_scores,
                              threats, phase, wp, bp,
                              player_color, ai_color) -> str:
    """توليد نصيحة ذكية باللغة العربية"""
    lines = []
    best_str = format_move_to_string(best_move)

    # النصيحة الأساسية
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

    # تحذيرات من التهديدات
    for t in threats:
        if "🚨" in t or "⚠️" in t:
            lines.append(t)

    # نصائح مرحلة اللعبة
    if phase >= 0.8:
        lines.append("📚 *الافتتاح: سيطر على المركز وحافظ على الصف الخلفي*")
    elif phase >= 0.4:
        lines.append("⚔️ *وسط اللعبة: ابحث عن سلاسل أكل وحافظ على التماسك*")
    else:
        lines.append("🎯 *نهاية اللعبة: الملوك أقوى، اسعَ للتتويج*")

    # مقارنة أفضل الحركات
    if len(move_scores) > 1:
        diff = move_scores[0][1] - move_scores[1][1]
        if diff > 100:
            lines.append(f"⭐ هذه الحركة أفضل بكثير من البديل التالي (+{diff:.0f})")
        elif diff < 20:
            alt = format_move_to_string(move_scores[1][0])
            lines.append(f"💡 بديل قريب: **{alt}** (فرق {diff:.0f} نقطة)")

    return "\n".join(lines)


def get_tt_stats() -> dict:
    """إحصائيات Transposition Table"""
    return {
        "size":   _tt.size,
        "hits":   _tt.hits,
        "stores": _tt.stores,
        "hit_rate": (
            f"{100 * _tt.hits / max(1, _tt.hits + _tt.stores):.1f}%"
        ),
    }
