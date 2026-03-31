"""
محرك الذكاء الاصطناعي للعبة الداما الكلاسيكية (8x8)
نسخة محسّنة مع:
- إزالة board.pop() واستخدام FEN للمحاكاة الآمنة
- Transposition Table لتسريع البحث
- Move Ordering لتحسين Alpha-Beta
- Iterative Deepening مع Time Management
"""
import math
import time
import hashlib
from functools import lru_cache

try:
    from draughts import Board, WHITE, BLACK
    DRAUGHTS_AVAILABLE = True
except ImportError:
    DRAUGHTS_AVAILABLE = False
    WHITE, BLACK = 2, 1

# ════════════════════════════════════════════
# ثوابت التقييم
# ════════════════════════════════════════════
KING_VALUE      = 500
PIECE_VALUE     = 100
CENTER_BONUS    = 15
INNER_CENTER_B  = 25
ADVANCEMENT_B   = 5
MOBILITY_WEIGHT = 3
BACK_ROW_BONUS  = 8
KING_SAFETY_B   = 12
ENDGAME_KING_B  = 30

# مربعات مهمة
CENTER_SQUARES   = {10, 11, 14, 15, 18, 19, 22, 23}
INNER_CENTER     = {14, 15, 18, 19}
WHITE_BACK_ROW   = {29, 30, 31, 32}
BLACK_BACK_ROW   = {1, 2, 3, 4}

# حدود Transposition Table
TT_MAX_SIZE = 200_000


class SearchTimeout(Exception):
    """استثناء انتهاء وقت البحث"""
    pass


# ════════════════════════════════════════════
# دوال المساعدة للرقعة
# ════════════════════════════════════════════
def get_legal_moves(board) -> list:
    """جلب الحركات القانونية بأمان"""
    try:
        moves = board.legal_moves
        return list(moves() if callable(moves) else moves)
    except Exception:
        return []


def get_board_fen(board) -> str:
    """جلب FEN الرقعة بأمان"""
    try:
        fen = board.fen
        return fen() if callable(fen) else str(fen)
    except Exception:
        return ""


def format_move_to_string(move) -> str:
    """
    تحويل الحركة إلى نص يحتوي أرقام المربعات.
    الأولوية: steps_move → pdn_move → str(move)
    """
    try:
        # الأفضل: steps_move يعطي قائمة المربعات
        if hasattr(move, 'steps_move') and move.steps_move:
            steps = list(move.steps_move)
            if len(steps) >= 2:
                sep = "x" if _is_capture_move(move) else "-"
                return sep.join(str(s) for s in steps)

        # بديل: pdn_move
        if hasattr(move, 'pdn_move') and move.pdn_move:
            pdn = str(move.pdn_move)
            if any(c.isdigit() for c in pdn):
                return pdn

        # أخيراً: str(move)
        move_str = str(move)
        if any(c.isdigit() for c in move_str):
            return move_str

    except Exception:
        pass
    return "?"


def _is_capture_move(move) -> bool:
    """هل الحركة أكل؟"""
    try:
        if hasattr(move, 'captures') and move.captures:
            return True
        if hasattr(move, 'is_capture') and move.is_capture:
            return True
        move_str = str(move)
        return 'x' in move_str or 'X' in move_str
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
            """تحليل جانب واحد من FEN"""
            pieces = []
            # إزالة حرف اللون (W أو B)
            if s and s[0] in ('W', 'B', 'w', 'b'):
                s = s[1:]
            for token in s.split(','):
                token = token.strip()
                if not token:
                    continue
                is_king = token.startswith('K')
                num_str = token[1:] if is_king else token
                try:
                    sq = int(num_str)
                    pieces.append((sq, is_king))
                except ValueError:
                    continue
            return pieces

        white_pieces = parse_side(parts[1])
        black_pieces = parse_side(parts[2])
        return white_pieces, black_pieces

    except Exception:
        return [], []


# ════════════════════════════════════════════
# Transposition Table
# ════════════════════════════════════════════
_transposition_table: dict = {}


def _fen_hash(fen: str) -> str:
    """توليد مفتاح مختصر من FEN"""
    return hashlib.md5(fen.encode()).hexdigest()


def _tt_lookup(fen: str, depth: int):
    """البحث في جدول التحويل"""
    key = (fen, depth)
    return _transposition_table.get(key)


def _tt_store(fen: str, depth: int, score: float, flag: str):
    """تخزين في جدول التحويل مع تحديد الحجم"""
    global _transposition_table
    if len(_transposition_table) >= TT_MAX_SIZE:
        # حذف نصف الجدول عند الامتلاء
        keys = list(_transposition_table.keys())
        for k in keys[:TT_MAX_SIZE // 2]:
            del _transposition_table[k]
    _transposition_table[(fen, depth)] = (score, flag)


def clear_transposition_table():
    """مسح جدول التحويل"""
    global _transposition_table
    _transposition_table = {}


# ════════════════════════════════════════════
# دوال التقييم
# ════════════════════════════════════════════
def _score_side(pieces: list, is_white: bool, total_pieces: int) -> float:
    """
    حساب نقاط جانب واحد مع مراعاة:
    - قيمة القطع والملوك
    - المكافآت الموضعية
    - مرحلة اللعبة (بداية/نهاية)
    """
    score = 0.0
    is_endgame = total_pieces <= 8  # مرحلة النهاية

    for sq, is_king in pieces:
        if is_king:
            base = KING_VALUE
            if is_endgame:
                base += ENDGAME_KING_B  # الملك أقوى في النهاية
            # مكافأة الملك في المركز
            if sq in INNER_CENTER:
                score += INNER_CENTER_B
            elif sq in CENTER_SQUARES:
                score += CENTER_BONUS
        else:
            base = PIECE_VALUE
            # حساب الصف (0-7)
            row = (sq - 1) // 4
            # التقدم: أبيض يتحرك للأعلى (صف صغير أفضل)
            advancement = (7 - row) if is_white else row
            score += advancement * ADVANCEMENT_B

            # مكافأة المركز
            if sq in INNER_CENTER:
                score += INNER_CENTER_B
            elif sq in CENTER_SQUARES:
                score += CENTER_BONUS

            # مكافأة الصف الخلفي (حماية الملك)
            back_row = WHITE_BACK_ROW if is_white else BLACK_BACK_ROW
            if sq in back_row:
                score += BACK_ROW_BONUS

        score += base

    return score


def evaluate_position(board, ai_color) -> float:
    """
    تقييم شامل للموقف.
    قيم موجبة = أفضل للـ AI
    قيم سالبة = أفضل للخصم
    """
    legal_moves = get_legal_moves(board)

    # حالة النهاية
    if not legal_moves:
        # من لا يملك حركات يخسر
        if board.turn == ai_color:
            return -100_000
        else:
            return 100_000

    fen = get_board_fen(board)
    white_pieces, black_pieces = parse_fen_pieces(fen)

    total_pieces = len(white_pieces) + len(black_pieces)

    # الرقعة فارغة (تعادل نادر)
    if total_pieces == 0:
        return 0.0

    white_score = _score_side(white_pieces, is_white=True,
                               total_pieces=total_pieces)
    black_score = _score_side(black_pieces, is_white=False,
                               total_pieces=total_pieces)

    # مكافأة الحركية
    mobility = len(legal_moves) * MOBILITY_WEIGHT

    if ai_color == WHITE:
        base = white_score - black_score
    else:
        base = black_score - white_score

    # إضافة/خصم الحركية حسب دور من؟
    base += mobility if board.turn == ai_color else -mobility

    return base


# ════════════════════════════════════════════
# ترتيب الحركات (Move Ordering)
# ════════════════════════════════════════════
def _order_moves(moves: list, board) -> list:
    """
    ترتيب الحركات لتحسين قطع Alpha-Beta:
    1. حركات الأكل أولاً
    2. حركات التتويج
    3. باقي الحركات
    """
    def move_priority(move):
        score = 0
        # أكل متعدد = الأولوية الأعلى
        if _is_capture_move(move):
            score += 1000
            # أكل متعدد (multi-jump)
            if hasattr(move, 'steps_move') and move.steps_move:
                steps = list(move.steps_move)
                score += len(steps) * 100
        # حركة نحو التتويج
        if hasattr(move, 'is_promotion') and move.is_promotion:
            score += 500
        return score

    try:
        return sorted(moves, key=move_priority, reverse=True)
    except Exception:
        return moves


# ════════════════════════════════════════════
# خوارزمية Minimax مع Alpha-Beta
# ════════════════════════════════════════════
def minimax(board, depth: int, alpha: float, beta: float,
            maximizing: bool, ai_color, deadline=None) -> float:
    """
    Minimax مع:
    - Alpha-Beta Pruning
    - Transposition Table
    - Time Management
    """
    # فحص الوقت
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    fen = get_board_fen(board)

    # فحص جدول التحويل
    tt_entry = _tt_lookup(fen, depth)
    if tt_entry is not None:
        cached_score, flag = tt_entry
        if flag == 'exact':
            return cached_score
        elif flag == 'lower':
            alpha = max(alpha, cached_score)
        elif flag == 'upper':
            beta = min(beta, cached_score)
        if alpha >= beta:
            return cached_score

    legal_moves = get_legal_moves(board)

    # حالات القاعدة
    if depth == 0 or not legal_moves:
        score = evaluate_position(board, ai_color)
        _tt_store(fen, depth, score, 'exact')
        return score

    # ترتيب الحركات
    ordered_moves = _order_moves(legal_moves, board)
    original_alpha = alpha

    if maximizing:
        max_eval = -math.inf
        for move in ordered_moves:
            # إنشاء رقعة جديدة بدلاً من push/pop
            sim = Board(variant="english", fen=fen)
            sim_moves = get_legal_moves(sim)
            sim_move = _find_matching_move(move, sim_moves)
            if sim_move is None:
                continue
            sim.push(sim_move)
            score = minimax(sim, depth - 1, alpha, beta,
                            False, ai_color, deadline)
            max_eval = max(max_eval, score)
            alpha = max(alpha, score)
            if beta <= alpha:
                break  # Beta cutoff

        # تخزين في TT
        flag = 'exact' if original_alpha < max_eval < beta else \
               'lower' if max_eval >= beta else 'upper'
        _tt_store(fen, depth, max_eval, flag)
        return max_eval

    else:
        min_eval = math.inf
        for move in ordered_moves:
            sim = Board(variant="english", fen=fen)
            sim_moves = get_legal_moves(sim)
            sim_move = _find_matching_move(move, sim_moves)
            if sim_move is None:
                continue
            sim.push(sim_move)
            score = minimax(sim, depth - 1, alpha, beta,
                            True, ai_color, deadline)
            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha:
                break  # Alpha cutoff

        flag = 'exact' if alpha < min_eval < original_alpha else \
               'lower' if min_eval >= beta else 'upper'
        _tt_store(fen, depth, min_eval, flag)
        return min_eval


# ════════════════════════════════════════════
# مطابقة الحركات
# ════════════════════════════════════════════
def _find_matching_move(original_move, sim_moves: list):
    """
    إيجاد الحركة المكافئة في الرقعة المحاكاة.
    يجرب عدة طرق للمطابقة.
    """
    if not sim_moves:
        return None

    orig_str = str(original_move)

    # المطابقة الأولى: نص مباشر
    for sm in sim_moves:
        if str(sm) == orig_str:
            return sm

    # المطابقة الثانية: steps_move
    if hasattr(original_move, 'steps_move') and original_move.steps_move:
        orig_steps = tuple(original_move.steps_move)
        for sm in sim_moves:
            if (hasattr(sm, 'steps_move') and sm.steps_move and
                    tuple(sm.steps_move) == orig_steps):
                return sm

    # المطابقة الثالثة: pdn_move
    if hasattr(original_move, 'pdn_move') and original_move.pdn_move:
        orig_pdn = str(original_move.pdn_move)
        for sm in sim_moves:
            if (hasattr(sm, 'pdn_move') and sm.pdn_move and
                    str(sm.pdn_move) == orig_pdn):
                return sm

    # المطابقة الرابعة: format string
    orig_fmt = format_move_to_string(original_move)
    if orig_fmt and orig_fmt != "?":
        for sm in sim_moves:
            if format_move_to_string(sm) == orig_fmt:
                return sm

    return None


# ════════════════════════════════════════════
# البحث الرئيسي
# ════════════════════════════════════════════
def find_best_move(original_board, ai_color,
                   max_depth: int = 5,
                   time_limit: float = 3.5):
    """
    Iterative Deepening Minimax مع Alpha-Beta.
    
    Returns:
        (best_move, best_score, reached_depth)
    """
    legal_moves = get_legal_moves(original_board)

    if not legal_moves:
        return None, 0, 0

    if len(legal_moves) == 1:
        return legal_moves[0], 0, 1

    # ترتيب مبدئي للحركات
    ordered_moves = _order_moves(legal_moves, original_board)

    best_move = ordered_moves[0]
    best_score = -math.inf
    reached_depth = 0

    original_fen = get_board_fen(original_board)
    start_time = time.time()
    deadline = start_time + time_limit

    for depth in range(1, max_depth + 1):
        try:
            depth_best_move = None
            depth_best_score = -math.inf
            alpha = -math.inf
            beta = math.inf

            for move in ordered_moves:
                # إنشاء رقعة محاكاة جديدة
                sim_board = Board(variant="english", fen=original_fen)
                sim_moves = get_legal_moves(sim_board)
                sim_move = _find_matching_move(move, sim_moves)

                if sim_move is None:
                    continue

                sim_board.push(sim_move)
                score = minimax(
                    sim_board, depth - 1,
                    alpha, beta,
                    False, ai_color, deadline
                )

                if score > depth_best_score:
                    depth_best_score = score
                    depth_best_move = move

                alpha = max(alpha, score)

            # تحديث أفضل حركة إذا اكتمل العمق
            if depth_best_move is not None:
                best_move = depth_best_move
                best_score = depth_best_score
                reached_depth = depth

                # ترتيب الحركات بناءً على نتائج هذا العمق
                # (أفضل حركة أولاً في العمق التالي)
                if depth_best_move in ordered_moves:
                    ordered_moves.remove(depth_best_move)
                    ordered_moves.insert(0, depth_best_move)

            # فوز/خسارة مؤكدة → لا حاجة للبحث أعمق
            if abs(best_score) > 90_000:
                break

        except SearchTimeout:
            break

    return best_move, best_score, reached_depth
