""" محرك الذكاء الاصطناعي المتقدم للعبة الداما
=============================================
النسخة المُصححة - جميع الأخطاء الحرجة والمتوسطة والبسيطة تم إصلاحها
"""

import math
import time
import random
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
INF = math.inf
MATE_SCORE = 10_000_000
TT_MAX_SIZE = 1_000_000
KILLER_SLOTS = 3
MAX_DEPTH = 24
LMR_MIN_DEPTH = 3
LMR_MIN_MOVES = 4

# ════════════════════════════════════════════
# ثوابت التقييم
# ════════════════════════════════════════════
PIECE_VALUE = 1000
KING_VALUE = 3200
TEMPO_BONUS = 18
CENTER_BONUS = 22
INNER_CENTER_B = 40
ADVANCEMENT_B = 12
BACK_ROW_BONUS = 35
KING_CENTER_B = 45
MOBILITY_W = 8
ENDGAME_KING_B = 60
TRIANGLE_BONUS = 30
BRIDGE_BONUS = 25
DOUBLE_CORNER_B = 40
TRADE_BONUS = 15
SAFE_PIECE_BONUS = 20
DANGER_PENALTY = 80
FORK_BONUS = 150
TRAP_BONUS = 200
DECOY_BONUS = 120
CHAIN_CAPTURE_B = 180
PAWN_STRUCTURE_B = 18
ISOLATION_PENALTY = 25
VULNERABILITY_PEN = 90

# مربعات استراتيجية
CENTER_SQUARES = {10, 11, 14, 15, 18, 19, 22, 23}
INNER_CENTER = {14, 15, 18, 19}
WHITE_BACK_ROW = {29, 30, 31, 32}
BLACK_BACK_ROW = {1, 2, 3, 4}
CORNER_SQUARES = {1, 4, 29, 32}
DOUBLE_CORNER = {4, 29}
EDGE_SQUARES = {5, 9, 13, 17, 21, 25}

# ════════════════════════════════════════════
# دوال تحويل الإحداثيات
# ════════════════════════════════════════════
def _sq_to_pos(sq):
    """
    تحويل رقم المربع (1-32) إلى (صف، عمود) على رقعة 8×8.
    الترقيم:
    Row 0: __ 1 __ 2 __ 3 __ 4
    Row 1: 5 __ 6 __ 7 __ 8 __
    Row 2: __ 9 __ 10 __ 11 __ 12
    Row 3: 13 __ 14 __ 15 __ 16 __
    Row 4: __ 17 __ 18 __ 19 __ 20
    Row 5: 21 __ 22 __ 23 __ 24 __
    Row 6: __ 25 __ 26 __ 27 __ 28
    Row 7: 29 __ 30 __ 31 __ 32 __
    """
    row = (sq - 1) // 4
    col_idx = (sq - 1) % 4
    if row % 2 == 0:
        col = col_idx * 2 + 1
    else:
        col = col_idx * 2
    return row, col


def _pos_to_sq(row, col):
    """
    تحويل (صف، عمود) إلى رقم المربع (1-32).
    يُرجع None إذا كان خارج الحدود أو ليس مربعاً داكناً.
    """
    if row < 0 or row > 7 or col < 0 or col > 7:
        return None
    if (row + col) % 2 == 0:
        return None
    if row % 2 == 0:
        idx = (col - 1) // 2
    else:
        idx = col // 2
    return row * 4 + idx + 1


# ════════════════════════════════════════════
# خريطة الجيران المُصححة لكل مربع
# ════════════════════════════════════════════
def _build_neighbors():
    """ بناء خريطة الجيران القطريين لكل مربع بشكل صحيح.
        كل مربع له حتى 4 جيران قطريين. """
    neighbors = {}
    for sq in range(1, 33):
        row, col = _sq_to_pos(sq)
        nb_list = []
        for dr, dc in [(-1, -1), (-1, +1), (+1, -1), (+1, +1)]:
            nr = row + dr
            nc = col + dc
            nb_sq = _pos_to_sq(nr, nc)
            if nb_sq is not None:
                nb_list.append(nb_sq)
        neighbors[sq] = nb_list
    return neighbors


NEIGHBORS = _build_neighbors()


# ════════════════════════════════════════════
# جدول القفزات المُصحح
# ════════════════════════════════════════════
def _build_jump_table():
    """
    بناء جدول: (من، فوق) → مربع_الهبوط.
    يُستخدم لحساب مربع الهبوط بعد القفز فوق قطعة.
    المفتاح: (attacker_sq, target_sq) → landing_sq
    """
    jump = {}
    for sq in range(1, 33):
        r1, c1 = _sq_to_pos(sq)
        for nb in NEIGHBORS.get(sq, []):
            r2, c2 = _sq_to_pos(nb)
            dr = r2 - r1
            dc = c2 - c1
            lr = r2 + dr
            lc = c2 + dc
            land = _pos_to_sq(lr, lc)
            if land is not None:
                jump[(sq, nb)] = land
    return jump


JUMP_TABLE = _build_jump_table()


# ════════════════════════════════════════════
# جداول الموضع
# ════════════════════════════════════════════
WHITE_MAN_PST = {
    1: 0, 2: 0, 3: 0, 4: 0,
    5: 8, 6: 8, 7: 8, 8: 8,
    9: 14, 10: 20, 11: 20, 12: 14,
    13: 18, 14: 28, 15: 28, 16: 18,
    17: 20, 18: 35, 19: 35, 20: 20,
    21: 22, 22: 30, 23: 30, 24: 22,
    25: 28, 26: 24, 27: 24, 28: 28,
    29: 40, 30: 40, 31: 40, 32: 40,
}

BLACK_MAN_PST = {
    32: 0, 31: 0, 30: 0, 29: 0,
    28: 8, 27: 8, 26: 8, 25: 8,
    24: 14, 23: 20, 22: 20, 21: 14,
    20: 18, 19: 28, 18: 28, 17: 18,
    16: 20, 15: 35, 14: 35, 13: 20,
    12: 22, 11: 30, 10: 30, 9: 22,
    8: 28, 7: 24, 6: 24, 5: 28,
    4: 40, 3: 40, 2: 40, 1: 40,
}

KING_PST = {
    1: 5, 2: 5, 3: 5, 4: 5,
    5: 5, 6: 12, 7: 12, 8: 5,
    9: 5, 10: 20, 11: 20, 12: 5,
    13: 5, 14: 30, 15: 30, 16: 5,
    17: 5, 18: 30, 19: 30, 20: 5,
    21: 5, 22: 20, 23: 20, 24: 5,
    25: 5, 26: 12, 27: 12, 28: 5,
    29: 5, 30: 5, 31: 5, 32: 5,
}

KING_ENDGAME_PST = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 2, 6: 8, 7: 8, 8: 2,
    9: 2, 10: 18, 11: 18, 12: 2,
    13: 2, 14: 28, 15: 28, 16: 2,
    17: 2, 18: 28, 19: 28, 20: 2,
    21: 2, 22: 18, 23: 18, 24: 2,
    25: 2, 26: 8, 27: 8, 28: 2,
    29: 2, 30: 2, 31: 2, 32: 2,
}


# ════════════════════════════════════════════
# كتاب الافتتاحيات
# ════════════════════════════════════════════
OPENING_BOOK: dict = {
    "W:W21,22,23,24,25,26,27,28,29,30,31,32:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "23-19", "22-18", "24-20", "21-17", "23-18",
    ],
    "W:W21,22,24,25,26,27,28,29,30,31,32,19:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "22-18", "24-20", "26-23", "21-17",
    ],
    "W:W21,23,24,25,26,27,28,29,30,31,32,18:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "23-19", "24-20", "25-22", "21-17",
    ],
    "W:W21,22,24,25,26,27,28,29,30,31,32,18,19:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "24-20", "26-23",
    ],
    "W:W21,22,23,24,26,27,28,29,30,31,32,25,18:B1,2,3,4,5,6,7,8,9,10,11,12": [
        "23-19", "21-17",
    ],
}


# ════════════════════════════════════════════
# استثناء الوقت
# ════════════════════════════════════════════
class SearchTimeout(Exception):
    pass


# ════════════════════════════════════════════
# Zobrist Hashing
# ════════════════════════════════════════════
class ZobristHasher:
    def __init__(self):
        rng = random.Random(0xCAFEBABE_DEADBEEF)
        self.table = {
            sq: [rng.getrandbits(64) for _ in range(4)]
            for sq in range(1, 33)
        }
        self.turn_white = rng.getrandbits(64)

    def compute(self, white_pieces: list, black_pieces: list, is_white_turn: bool) -> int:
        h = 0
        for sq, is_king in white_pieces:
            if 1 <= sq <= 32:
                h ^= self.table[sq][1 if is_king else 0]
        for sq, is_king in black_pieces:
            if 1 <= sq <= 32:
                h ^= self.table[sq][3 if is_king else 2]
        if is_white_turn:
            h ^= self.turn_white
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
        self.data: dict = {}
        self.hits = 0
        self.stores = 0

    def lookup(self, key: int, depth: int, alpha: float, beta: float):
        entry = self.data.get(key)
        if entry is None:
            return None
        d, score, flag, _ = entry
        if d < depth:
            return None
        self.hits += 1
        if flag == self.EXACT:
            return score
        if flag == self.LOWER and score >= beta:
            return score
        if flag == self.UPPER and score <= alpha:
            return score
        return None

    def store(self, key: int, depth: int, score: float, flag: int, best_str: str = ""):
        existing = self.data.get(key)
        if existing and existing[0] > depth:
            return
        if len(self.data) >= self.max_size:
            keys = list(self.data.keys())
            keys_to_del = keys[:len(keys) // 4]
            for k in keys_to_del:
                del self.data[k]
        self.data[key] = (depth, score, flag, best_str)
        self.stores += 1

    def get_best_str(self, key: int) -> str:
        e = self.data.get(key)
        return e[3] if e else ""

    def clear(self):
        self.data.clear()
        self.hits = 0
        self.stores = 0

    @property
    def size(self) -> int:
        return len(self.data)


# ════════════════════════════════════════════
# Move Ordering Data
# ════════════════════════════════════════════
class MoveOrderingData:
    def __init__(self):
        self.killers: dict = defaultdict(lambda: [None] * KILLER_SLOTS)
        self.history: dict = defaultdict(int)
        self.counters: dict = {}

    def add_killer(self, depth: int, ms: str):
        kl = self.killers[depth]
        if ms != kl[0]:
            kl[2] = kl[1]
            kl[1] = kl[0]
            kl[0] = ms

    def add_history(self, ms: str, depth: int):
        self.history[ms] += depth * depth

    def is_killer(self, depth: int, ms: str) -> bool:
        return ms in self.killers[depth]

    def set_counter(self, prev_ms: str, ms: str):
        self.counters[prev_ms] = ms

    def get_counter(self, prev_ms: str) -> str:
        return self.counters.get(prev_ms, "")

    def clear(self):
        self.killers.clear()
        self.history.clear()
        self.counters.clear()


# ════════════════════════════════════════════
# Singletons
# ════════════════════════════════════════════
_tt = TranspositionTable()
_order = MoveOrderingData()


# ════════════════════════════════════════════
# API عامة مُصدَّرة
# ════════════════════════════════════════════
def clear_transposition_table():
    """مسح جدول التحويل وبيانات الترتيب"""
    _tt.clear()
    _order.clear()


def get_tt_stats() -> dict:
    """إحصائيات Transposition Table"""
    total = max(1, _tt.hits + _tt.stores)
    return {
        "size": _tt.size,
        "hits": _tt.hits,
        "stores": _tt.stores,
        "hit_rate": f"{100 * _tt.hits / total:.1f}%",
    }


# ════════════════════════════════════════════
# دوال الرقعة الأساسية - مُصدَّرة
# ════════════════════════════════════════════
def get_legal_moves(board) -> list:
    try:
        mv = board.legal_moves
        return list(mv() if callable(mv) else mv)
    except Exception:
        return []


def get_board_fen(board) -> str:
    try:
        f = board.fen
        return f() if callable(f) else str(f)
    except Exception:
        return ""


def format_move_to_string(move) -> str:
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
        return 'x' in s.lower()
    except Exception:
        return False


def _is_promotion(move) -> bool:
    """هل الحركة تتويج؟"""
    try:
        return bool(getattr(move, 'is_promotion', False))
    except Exception:
        return False


def _capture_count(move) -> int:
    """عدد القطع المأكولة في الحركة"""
    try:
        if hasattr(move, 'steps_move') and move.steps_move:
            return max(0, len(list(move.steps_move)) - 1)
        if hasattr(move, 'captures') and move.captures:
            return len(list(move.captures))
    except Exception:
        pass
    return 1 if _is_capture(move) else 0


def parse_fen_pieces(fen_str: str):
    """تحليل FEN → (white_pieces, black_pieces)"""
    try:
        if not fen_str:
            return [], []
        parts = fen_str.split(':')
        if len(parts) < 3:
            return [], []

        def _parse(s: str):
            if s and s[0] in 'WBwb':
                s = s[1:]
            result = []
            for tok in s.split(','):
                tok = tok.strip()
                if not tok:
                    continue
                is_king = tok.startswith('K')
                try:
                    sq = int(tok[1:] if is_king else tok)
                    result.append((sq, is_king))
                except ValueError:
                    continue
            return result

        return _parse(parts[1]), _parse(parts[2])
    except Exception:
        return [], []


def _game_phase(total: int) -> float:
    """1.0=افتتاح | 0.0=نهاية"""
    if total >= 20:
        return 1.0
    if total >= 10:
        return (total - 10) / 10.0
    return 0.0


def _phase_label(phase: float) -> str:
    """نص مرحلة اللعبة"""
    if phase >= 0.75:
        return "افتتاح"
    if phase >= 0.35:
        return "وسط اللعبة"
    return "نهاية اللعبة"


# ════════════════════════════════════════════
# تحليل التهديدات - دوال مُصدَّرة علنياً
# ════════════════════════════════════════════
def build_square_sets(wp: list, bp: list):
    """
    بناء مجموعات المربعات.
    مُصدَّرة علنياً بدون underscore.
    Returns: (w_set, b_set, w_kings, b_kings)
    """
    w_set = {sq for sq, _ in wp}
    b_set = {sq for sq, _ in bp}
    w_kings = {sq for sq, k in wp if k}
    b_kings = {sq for sq, k in bp if k}
    return w_set, b_set, w_kings, b_kings


def _build_square_sets(wp: list, bp: list):
    """نسخة داخلية للتوافق مع الكود القديم"""
    return build_square_sets(wp, bp)


def is_square_attacked_by_white(sq: int, w_set: set, b_set: set, w_kings: set, all_pieces: set) -> bool:
    """
    هل المربع sq (الذي يحتوي قطعة سوداء) مهدد من الأبيض؟
    يتحقق: هل توجد قطعة بيضاء مجاورة يمكنها القفز فوق sq والهبوط في مربع فارغ؟
    مُصدَّرة علنياً.
    """
    for nb in NEIGHBORS.get(sq, []):
        if nb not in w_set:
            continue
        land = JUMP_TABLE.get((nb, sq))
        if land is None:
            continue
        if land in all_pieces:
            continue
        nb_row = (nb - 1) // 4
        sq_row = (sq - 1) // 4
        if nb_row > sq_row or nb in w_kings:
            return True
    return False


def _is_square_attacked_by_white(sq: int, w_set: set, b_set: set, w_kings: set, all_pieces: set) -> bool:
    """نسخة داخلية للتوافق"""
    return is_square_attacked_by_white(sq, w_set, b_set, w_kings, all_pieces)


def is_square_attacked_by_black(sq: int, w_set: set, b_set: set, b_kings: set, all_pieces: set) -> bool:
    """
    هل المربع sq (الذي يحتوي قطعة بيضاء) مهدد من الأسود؟
    يتحقق: هل توجد قطعة سوداء مجاورة يمكنها القفز فوق sq والهبوط في مربع فارغ؟
    مُصدَّرة علنياً.
    """
    for nb in NEIGHBORS.get(sq, []):
        if nb not in b_set:
            continue
        land = JUMP_TABLE.get((nb, sq))
        if land is None:
            continue
        if land in all_pieces:
            continue
        nb_row = (nb - 1) // 4
        sq_row = (sq - 1) // 4
        if nb_row < sq_row or nb in b_kings:
            return True
    return False


def _is_square_attacked_by_black(sq: int, w_set: set, b_set: set, b_kings: set, all_pieces: set) -> bool:
    """نسخة داخلية للتوافق"""
    return is_square_attacked_by_black(sq, w_set, b_set, b_kings, all_pieces)


def count_threatened_pieces(wp: list, bp: list, is_white_threatened: bool) -> int:
    """
    عدد القطع المهددة بالأكل.
    مُصدَّرة علنياً.
    """
    w_set, b_set, w_kings, b_kings = build_square_sets(wp, bp)
    all_pieces = w_set | b_set
    count = 0
    if is_white_threatened:
        for sq, _ in wp:
            if is_square_attacked_by_black(
                sq, w_set, b_set, b_kings, all_pieces):
                count += 1
    else:
        for sq, _ in bp:
            if is_square_attacked_by_white(
                sq, w_set, b_set, w_kings, all_pieces):
                count += 1
    return count


def _count_threatened_pieces(wp: list, bp: list, is_white_threatened: bool) -> int:
    """نسخة داخلية للتوافق"""
    return count_threatened_pieces(wp, bp, is_white_threatened)


def get_threatened_squares(wp: list, bp: list, player_color) -> set:
    """
    إرجاع مجموعة المربعات التي تحتوي قطع اللاعب المهددة.
    مُصدَّرة علنياً - تُستخدم في app.py مباشرة.
    """
    w_set, b_set, w_kings, b_kings = build_square_sets(wp, bp)
    all_pieces = w_set | b_set
    threatened = set()
    if player_color == WHITE:
        for sq, _ in wp:
            if is_square_attacked_by_black(
                sq, w_set, b_set, b_kings, all_pieces):
                threatened.add(sq)
    else:
        for sq, _ in bp:
            if is_square_attacked_by_white(
                sq, w_set, b_set, w_kings, all_pieces):
                threatened.add(sq)
    return threatened


def detect_forks(pieces_attacker: list, pieces_target: list, attacker_is_white: bool) -> int:
    """
    كشف الشوكات: عدد القطع التي تهدد أكثر من هدف.
    مُصدَّرة علنياً.
    يستخدم JUMP_TABLE لحساب مربعات الهبوط بشكل صحيح.
    """
    if attacker_is_white:
        w_set = {sq for sq, _ in pieces_attacker}
        b_set = {sq for sq, _ in pieces_target}
    else:
        w_set = {sq for sq, _ in pieces_target}
        b_set = {sq for sq, _ in pieces_attacker}
    all_pieces = w_set | b_set
    fork_count = 0
    attacker_kings = {sq for sq, k in pieces_attacker if k}
    target_set = {sq for sq, _ in pieces_target}
    for sq, is_king in pieces_attacker:
        threats = 0
        for nb in NEIGHBORS.get(sq, []):
            if nb not in target_set:
                continue
            land = JUMP_TABLE.get((sq, nb))
            if land is None:
                continue
            if land in all_pieces:
                continue
            nb_row = (nb - 1) // 4
            sq_row = (sq - 1) // 4
            if attacker_is_white:
                if sq_row > nb_row or is_king:
                    threats += 1
            else:
                if sq_row < nb_row or is_king:
                    threats += 1
        if threats >= 2:
            fork_count += 1
    return fork_count


def _detect_forks(pa, pt, aiw):
    """نسخة داخلية للتوافق"""
    return detect_forks(pa, pt, aiw)


def evaluate_safety(wp: list, bp: list, ai_is_white: bool) -> float:
    """
    تقييم السلامة.
    مُصدَّرة علنياً.
    """
    w_set, b_set, w_kings, b_kings = build_square_sets(wp, bp)
    all_p = w_set | b_set
    score = 0.0
    ai_pieces = wp if ai_is_white else bp
    opp_pieces = bp if ai_is_white else wp

    for sq, is_king in ai_pieces:
        if ai_is_white:
            thr = is_square_attacked_by_black(
                sq, w_set, b_set, b_kings, all_p)
        else:
            thr = is_square_attacked_by_white(
                sq, w_set, b_set, w_kings, all_p)
        if thr:
            score -= DANGER_PENALTY * (3 if is_king else 1)
        else:
            score += SAFE_PIECE_BONUS

    for sq, is_king in opp_pieces:
        if ai_is_white:
            thr = is_square_attacked_by_white(
                sq, w_set, b_set, w_kings, all_p)
        else:
            thr = is_square_attacked_by_black(
                sq, w_set, b_set, b_kings, all_p)
        if thr:
            score += VULNERABILITY_PEN * (3 if is_king else 1)
    return score


def _evaluate_safety(wp, bp, ai_is_white):
    """نسخة داخلية للتوافق"""
    return evaluate_safety(wp, bp, ai_is_white)


def detect_ui_threats(board, player_color, ai_color, fen: str, wp: list, bp: list) -> list:
    """
    كشف التهديدات للعرض في الواجهة.
    مُصدَّرة علنياً بدون underscore.
    """
    threats = []
    legal = get_legal_moves(board)
    captures = [m for m in legal if _is_capture(m)]
    if captures:
        max_cap = max(_capture_count(m) for m in captures)
        threats.append(
            f"⚔️ أكل مجبر: {len(captures)} خيار "
            f"(أقصى: {max_cap} قطعة)"
        )

    w_set, b_set, w_kings, b_kings = build_square_sets(wp, bp)
    all_p = w_set | b_set

    # قطع اللاعب المهددة
    player_pieces = wp if player_color == WHITE else bp
    threatened_p = []
    for sq, _ in player_pieces:
        if player_color == WHITE:
            if is_square_attacked_by_black(
                sq, w_set, b_set, b_kings, all_p):
                threatened_p.append(sq)
        else:
            if is_square_attacked_by_white(
                sq, w_set, b_set, w_kings, all_p):
                threatened_p.append(sq)
    if threatened_p:
        threats.append(f"⚠️ قطعك المهددة: {threatened_p}")

    # قطع الخصم المهددة
    ai_pieces = bp if player_color == WHITE else wp
    threatened_a = []
    for sq, _ in ai_pieces:
        if player_color == WHITE:
            if is_square_attacked_by_white(
                sq, w_set, b_set, w_kings, all_p):
                threatened_a.append(sq)
        else:
            if is_square_attacked_by_black(
                sq, w_set, b_set, b_kings, all_p):
                threatened_a.append(sq)
    if threatened_a:
        threats.append(f"🎯 قطع الخصم المهددة: {threatened_a}")

    # قرب التتويج
    if player_color == WHITE:
        near = [sq for sq, k in wp if not k and sq in {5, 6, 7, 8}]
        enemy_near = [sq for sq, k in bp if not k and sq in {25, 26, 27, 28}]
    else:
        near = [sq for sq, k in bp if not k and sq in {25, 26, 27, 28}]
        enemy_near = [sq for sq, k in wp if not k and sq in {5, 6, 7, 8}]
    if near:
        threats.append(f"👑 قريب من التتويج: {near}")
    if enemy_near:
        threats.append(f"🚨 خصمك قريب من التتويج! {enemy_near}")

    # شوكات
    if player_color == WHITE:
        forks = detect_forks(wp, bp, True)
    else:
        forks = detect_forks(bp, wp, False)
    if forks > 0:
        threats.append(f"🍴 فرصة شوكة! ({forks} موضع)")

    return threats if threats else ["✅ الموقف آمن"]


def _detect_ui_threats(board, player_color, ai_color, fen, wp, bp):
    """نسخة داخلية للتوافق"""
    return detect_ui_threats(board, player_color, ai_color, fen, wp, bp)


# ════════════════════════════════════════════
# التقييم الموضعي
# ════════════════════════════════════════════
def _score_side(pieces: list, is_white: bool, phase: float) -> float:
    """
    تقييم جانب واحد.
    تم حذف المعامل total غير المُستخدم.
    """
    score = 0.0
    man_pst = WHITE_MAN_PST if is_white else BLACK_MAN_PST
    king_pst = KING_ENDGAME_PST if phase < 0.3 else KING_PST
    squares = {sq for sq, _ in pieces}
    for sq, is_king in pieces:
        if is_king:
            base = KING_VALUE
            base += king_pst.get(sq, 0)
            if phase < 0.3:
                if sq in INNER_CENTER:
                    base += ENDGAME_KING_B
                elif sq in CENTER_SQUARES:
                    base += ENDGAME_KING_B // 2
            if sq in DOUBLE_CORNER and phase > 0.6:
                base += DOUBLE_CORNER_B
        else:
            base = PIECE_VALUE
            base += man_pst.get(sq, 0)
            row = (sq - 1) // 4
            adv = (7 - row) if is_white else row
            base += adv * ADVANCEMENT_B
            back = WHITE_BACK_ROW if is_white else BLACK_BACK_ROW
            if sq in back:
                base += BACK_ROW_BONUS
            if sq in INNER_CENTER:
                base += INNER_CENTER_B
            elif sq in CENTER_SQUARES:
                base += CENTER_BONUS
            nb_count = sum(1 for n in NEIGHBORS.get(sq, []) if n in squares)
            if nb_count >= 2:
                score += PAWN_STRUCTURE_B
            elif nb_count == 0 and not is_king:
                score -= ISOLATION_PENALTY
        score += base
    return score


def _detect_structures(pieces: list, is_white: bool) -> float:
    """كشف الهياكل التكتيكية"""
    bonus = 0.0
    squares = {sq for sq, _ in pieces}
    if is_white:
        if ({29, 30, 31}.issubset(squares) or {30, 31, 32}.issubset(squares)):
            bonus += TRIANGLE_BONUS
    else:
        if ({1, 2, 3}.issubset(squares) or {2, 3, 4}.issubset(squares)):
            bonus += TRIANGLE_BONUS
    kings = [sq for sq, k in pieces if k]
    if len(kings) >= 2:
        bonus += BRIDGE_BONUS
    return bonus


def evaluate_position(board, ai_color) -> float:
    """
    تقييم شامل للموقف.
    موجب = أفضل للـ AI.
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

    w_score = _score_side(wp, True, phase)
    b_score = _score_side(bp, False, phase)

    w_score += _detect_structures(wp, True)
    b_score += _detect_structures(bp, False)

    safety = evaluate_safety(wp, bp, ai_color == WHITE)

    if ai_color == WHITE:
        forks = detect_forks(wp, bp, True)
        opp_forks = detect_forks(bp, wp, False)
    else:
        forks = detect_forks(bp, wp, False)
        opp_forks = detect_forks(wp, bp, True)
    fork_score = (forks - opp_forks) * FORK_BONUS

    w_mat = (len(wp) * PIECE_VALUE + sum(KING_VALUE for _, k in wp if k))
    b_mat = (len(bp) * PIECE_VALUE + sum(KING_VALUE for _, k in bp if k))

    trade = 0.0
    if ai_color == WHITE and w_mat > b_mat + PIECE_VALUE:
        trade = TRADE_BONUS * (w_mat - b_mat) / PIECE_VALUE
    elif ai_color == BLACK and b_mat > w_mat + PIECE_VALUE:
        trade = TRADE_BONUS * (b_mat - w_mat) / PIECE_VALUE

    mobility = len(legal) * MOBILITY_W

    if ai_color == WHITE:
        base = w_score - b_score
    else:
        base = b_score - w_score

    base += safety + fork_score + trade
    base += mobility if board.turn == ai_color else -mobility
    base += TEMPO_BONUS if board.turn == ai_color else -TEMPO_BONUS

    return base


# ════════════════════════════════════════════
# مطابقة الحركات
# ════════════════════════════════════════════
def _find_matching_move(orig_move, sim_moves: list):
    """إيجاد الحركة المطابقة في قائمة الحركات المحاكاة"""
    if not sim_moves:
        return None
    orig_str = str(orig_move)
    orig_fmt = format_move_to_string(orig_move)
    for sm in sim_moves:
        if str(sm) == orig_str:
            return sm
    if hasattr(orig_move, 'steps_move') and orig_move.steps_move:
        orig_steps = tuple(orig_move.steps_move)
        for sm in sim_moves:
            if (hasattr(sm, 'steps_move') and sm.steps_move and
                tuple(sm.steps_move) == orig_steps):
                return sm
    if hasattr(orig_move, 'pdn_move') and orig_move.pdn_move:
        orig_pdn = str(orig_move.pdn_move)
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
def _score_move_ordering(move, depth: int, prev_ms: str = "", is_q: bool = False) -> int:
    """تقييم الحركة لأغراض الترتيب"""
    score = 0
    ms = format_move_to_string(move)
    if _is_capture(move):
        score += 25_000 + _capture_count(move) * 2_000
    if _is_promotion(move):
        score += 18_000
    if not is_q:
        if _order.is_killer(depth, ms):
            score += 12_000
        if prev_ms and _order.get_counter(prev_ms) == ms:
            score += 8_000
        score += min(_order.history.get(ms, 0), 6_000)
    if hasattr(move, 'steps_move') and move.steps_move:
        steps = list(move.steps_move)
        if steps:
            dest = steps[-1]
            if dest in INNER_CENTER:
                score += 500
            elif dest in CENTER_SQUARES:
                score += 250
    return score


def _order_moves(moves: list, depth: int, prev_ms: str = "", is_q: bool = False) -> list:
    """ترتيب الحركات حسب الأولوية"""
    try:
        return sorted(
            moves,
            key=lambda m: _score_move_ordering(m, depth, prev_ms, is_q),
            reverse=True
        )
    except Exception:
        return moves


# ════════════════════════════════════════════
# Quiescence Search - مُصحح (Minimax style)
# ════════════════════════════════════════════
def quiescence(board, alpha: float, beta: float, ai_color, maximizing: bool, deadline=None, qdepth: int = 0) -> float:
    """
    بحث الاستقرار (Quiescence Search).
    مُصحح ليعمل بأسلوب Minimax بدلاً من Negamax لمنع تعارض التقييم.
    """
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    stand_pat = evaluate_position(board, ai_color)
    if qdepth >= 10:
        return stand_pat

    legal = get_legal_moves(board)
    captures = [m for m in legal if _is_capture(m)]

    if maximizing:
        if stand_pat >= beta:
            return beta
        DELTA = PIECE_VALUE * 2
        if stand_pat + DELTA < alpha:
            return alpha
        if stand_pat > alpha:
            alpha = stand_pat
        if not captures:
            return stand_pat

        captures = _order_moves(captures, 0, is_q=True)
        fen = get_board_fen(board)
        for move in captures:
            try:
                sim = Board(variant="english", fen=fen)
                sim_mvs = get_legal_moves(sim)
                sim_move = _find_matching_move(move, sim_mvs)
                if sim_move is None:
                    continue
                sim.push(sim_move)
                score = quiescence(
                    sim, alpha, beta, ai_color, False, deadline, qdepth + 1
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
    else:
        if stand_pat <= alpha:
            return alpha
        DELTA = PIECE_VALUE * 2
        if stand_pat - DELTA > beta:
            return beta
        if stand_pat < beta:
            beta = stand_pat
        if not captures:
            return stand_pat

        captures = _order_moves(captures, 0, is_q=True)
        fen = get_board_fen(board)
        for move in captures:
            try:
                sim = Board(variant="english", fen=fen)
                sim_mvs = get_legal_moves(sim)
                sim_move = _find_matching_move(move, sim_mvs)
                if sim_move is None:
                    continue
                sim.push(sim_move)
                score = quiescence(
                    sim, alpha, beta, ai_color, True, deadline, qdepth + 1
                )
                if score <= alpha:
                    return alpha
                if score < beta:
                    beta = score
            except SearchTimeout:
                raise
            except Exception:
                continue
        return beta


# ════════════════════════════════════════════
# Minimax الرئيسي - مُصحح
# ════════════════════════════════════════════
def minimax(board, depth: int, alpha: float, beta: float, maximizing: bool, ai_color, deadline=None, ply: int = 0, prev_ms: str = "") -> float:
    """
    بحث Minimax مع Alpha-Beta Pruning.
    مُصحح ليمرر maximizing إلى quiescence.
    """
    if deadline and time.time() > deadline:
        raise SearchTimeout()

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    pos_hash = _zobrist.compute(wp, bp, board.turn == WHITE)
    tt_val = _tt.lookup(pos_hash, depth, alpha, beta)
    if tt_val is not None:
        return tt_val

    legal = get_legal_moves(board)
    if not legal:
        s = (-MATE_SCORE + ply) if maximizing else (MATE_SCORE - ply)
        _tt.store(pos_hash, depth, s, TranspositionTable.EXACT)
        return s

    if depth <= 0:
        s = quiescence(board, alpha, beta, ai_color, maximizing, deadline)
        _tt.store(pos_hash, 0, s, TranspositionTable.EXACT)
        return s

    # Null Move Pruning
    all_cap = all(_is_capture(m) for m in legal)
    if (maximizing and depth >= 4 and not all_cap and len(wp) >= 4 and len(bp) >= 4):
        null_score = evaluate_position(board, ai_color)
        if null_score >= beta + 50:
            return beta

    tt_best = _tt.get_best_str(pos_hash)
    ordered = _order_moves(legal, ply, prev_ms)
    if tt_best:
        for i, m in enumerate(ordered):
            if format_move_to_string(m) == tt_best:
                ordered.insert(0, ordered.pop(i))
                break

    orig_alpha = alpha
    best_score = -INF if maximizing else INF
    best_move_str = ""
    tried = 0
    for move in ordered:
        ms = format_move_to_string(move)
        try:
            sim = Board(variant="english", fen=fen)
            sim_mvs = get_legal_moves(sim)
            sim_move = _find_matching_move(move, sim_mvs)
            if sim_move is None:
                continue
            sim.push(sim_move)
        except Exception:
            continue
        tried += 1

        reduction = 0
        if (tried > LMR_MIN_MOVES and depth >= LMR_MIN_DEPTH and
            not _is_capture(move) and not _is_promotion(move) and
            not _order.is_killer(ply, ms)):
            reduction = 1 + (1 if tried > LMR_MIN_MOVES * 3 else 0)

        if maximizing:
            score = minimax(
                sim, depth - 1 - reduction, alpha, beta, False, ai_color,
                deadline, ply + 1, ms
            )
            if reduction > 0 and alpha < score < beta:
                score = minimax(
                    sim, depth - 1, alpha, beta, False, ai_color,
                    deadline, ply + 1, ms
                )
            if score > best_score:
                best_score = score
                best_move_str = ms
                alpha = max(alpha, score)
        else:
            score = minimax(
                sim, depth - 1 - reduction, alpha, beta, True, ai_color,
                deadline, ply + 1, ms
            )
            if reduction > 0 and alpha < score < beta:
                score = minimax(
                    sim, depth - 1, alpha, beta, True, ai_color,
                    deadline, ply + 1, ms
                )
            if score < best_score:
                best_score = score
                best_move_str = ms
                beta = min(beta, score)

        if beta <= alpha:
            if not _is_capture(move):
                _order.add_killer(ply, ms)
                _order.add_history(ms, depth)
                if prev_ms:
                    _order.set_counter(prev_ms, ms)
            break

    if best_score <= orig_alpha:
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
def find_best_move(original_board, ai_color, max_depth: int = MAX_DEPTH, time_limit: float = 5.0):
    """
    Iterative Deepening + Aspiration Windows.
    Returns: (best_move, best_score, reached_depth)
    """
    legal = get_legal_moves(original_board)
    if not legal:
        return None, 0, 0
    if len(legal) == 1:
        return legal[0], 0, 1

    orig_fen = get_board_fen(original_board)
    book = OPENING_BOOK.get(orig_fen.strip())
    if book:
        book_str = random.choice(book)
        for m in legal:
            if format_move_to_string(m) == book_str:
                return m, 0, 0

    ordered = _order_moves(legal, 0)
    best_move = ordered[0]
    best_score = -INF
    reached = 0
    start = time.time()
    deadline = start + time_limit

    asp_window = 150
    prev_score = 0.0

    for depth in range(1, max_depth + 1):
        if time.time() - start > time_limit * 0.88:
            break

        if depth > 4 and abs(prev_score) < MATE_SCORE // 2:
            asp_alpha = prev_score - asp_window
            asp_beta = prev_score + asp_window
        else:
            asp_alpha = -INF
            asp_beta = INF

        try:
            d_best = None
            d_score = -INF
            alpha = asp_alpha
            beta = asp_beta
            failed = False

            for move in ordered:
                try:
                    sim = Board(variant="english", fen=orig_fen)
                    sim_mvs = get_legal_moves(sim)
                    sim_move = _find_matching_move(move, sim_mvs)
                    if sim_move is None:
                        continue
                    sim.push(sim_move)
                    score = minimax(
                        sim, depth - 1, alpha, beta, False, ai_color,
                        deadline, 1, format_move_to_string(move)
                    )
                except SearchTimeout:
                    raise
                except Exception:
                    continue

                if score > d_score:
                    d_score = score
                    d_best = move
                    alpha = max(alpha, score)
                if score >= beta or score <= asp_alpha:
                    failed = True
                    break

            if failed and d_best is None:
                d_score = -INF
                alpha = -INF
                beta = INF
                for move in ordered:
                    try:
                        sim = Board(variant="english", fen=orig_fen)
                        sim_mvs = get_legal_moves(sim)
                        sim_move = _find_matching_move(move, sim_mvs)
                        if sim_move is None:
                            continue
                        sim.push(sim_move)
                        score = minimax(
                            sim, depth - 1, alpha, beta, False, ai_color,
                            deadline, 1
                        )
                    except SearchTimeout:
                        raise
                    except Exception:
                        continue
                    if score > d_score:
                        d_score = score
                        d_best = move
                        alpha = max(alpha, score)

            if d_best is not None:
                best_move = d_best
                best_score = d_score
                reached = depth
                prev_score = d_score
                asp_window = 150
                if d_best in ordered:
                    ordered.remove(d_best)
                    ordered.insert(0, d_best)

                if abs(best_score) > MATE_SCORE // 2:
                    break

        except SearchTimeout:
            break

    return best_move, best_score, reached


# ════════════════════════════════════════════
# تقييم مساعد الواجهة
# ════════════════════════════════════════════
def _get_advantage_text(score: float) -> str:
    """نص يصف التفوق الحالي"""
    a = abs(score)
    if a < 100:
        return "⚖️ تعادل تام"
    who = "اللاعب" if score > 0 else "الكمبيوتر"
    if a < 500:
        return f"🟡 تفوق طفيف لـ {who}"
    if a < 1500:
        return f"🟠 تفوق واضح لـ {who}"
    if a < 4000:
        return f"🔴 تفوق كبير لـ {who}"
    return f"💀 هيمنة كاملة لـ {who}"


def _score_label(score: float) -> str:
    """تسمية مختصرة للتقييم"""
    if score > MATE_SCORE // 2:
        return "فوز مؤكد ✅"
    if score < -MATE_SCORE // 2:
        return "خسارة محتملة ❌"
    if abs(score) < 100:
        return "متعادل ⚖️"
    return "أفضل 🟢" if score > 0 else "أسوأ 🔴"


def _generate_recommendation(best_move, best_score, move_scores, threats, phase, wp, bp, player_color) -> str:
    """توليد توصية نصية للاعب"""
    lines = []
    best_str = format_move_to_string(best_move)

    if best_score > MATE_SCORE // 2:
        lines.append(f"🏆 **{best_str} تضمن الفوز!**")
    elif best_score < -MATE_SCORE // 2:
        lines.append(f"😰 **الموقف صعب، أفضل ما يمكن: {best_str}**")
    elif _is_capture(best_move):
        cnt = _capture_count(best_move)
        if cnt > 1:
            lines.append(f"⚔️ **سلسلة أكل {cnt} قطع: {best_str}**")
        else:
            lines.append(f"⚔️ **الأفضل الأكل: {best_str}**")
    elif _is_promotion(best_move):
        lines.append(f"👑 **تتويج قطعة: {best_str}!**")
    else:
        lines.append(f"♟️ **الحركة المثلى: {best_str}**")

    for t in threats:
        if "🚨" in t or "⚠️" in t:
            lines.append(t)

    if phase >= 0.75:
        lines.append("📚 *سيطر على المركز وحافظ على الصف الخلفي*")
    elif phase >= 0.35:
        lines.append("⚔️ *ابحث عن الشوكات وسلاسل الأكل*")
    else:
        lines.append("🎯 *الملوك أقوى - سيطر على الزوايا المزدوجة*")

    if len(move_scores) > 1:
        diff = move_scores[0][1] - move_scores[1][1]
        if diff > PIECE_VALUE:
            lines.append(f"⭐ هذه الحركة أفضل بفارق كبير (+{diff:.0f})")
        elif diff < 50:
            alt = format_move_to_string(move_scores[1][0])
            lines.append(f"💡 بديل: **{alt}** (فرق {diff:.0f})")

    return "\n".join(lines)


def analyze_position(board, player_color, ai_color, depth: int = 10, time_limit: float = 8.0) -> dict:
    """
    تحليل شامل للموقف.
    مُصدَّرة علنياً.
    """
    legal = get_legal_moves(board)
    if not legal:
        return {"error": "لا توجد حركات"}

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    total = len(wp) + len(bp)
    phase = _game_phase(total)
    orig_fen = fen
    move_scores = []
    deadline = time.time() + time_limit

    ordered = _order_moves(legal, 0)
    for move in ordered:
        try:
            sim = Board(variant="english", fen=orig_fen)
            sim_mvs = get_legal_moves(sim)
            sim_move = _find_matching_move(move, sim_mvs)
            if sim_move is None:
                continue
            sim.push(sim_move)
            score = minimax(
                sim, depth - 1, -INF, INF, False, player_color, deadline, 1
            )
            move_scores.append((move, score))
        except SearchTimeout:
            break
        except Exception:
            continue

    if not move_scores:
        for move in ordered[:8]:
            try:
                sim = Board(variant="english", fen=orig_fen)
                sim_mvs = get_legal_moves(sim)
                sim_move = _find_matching_move(move, sim_mvs)
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

    threats = detect_ui_threats(
        board, player_color, ai_color, fen, wp, bp
    )
    advantage = _get_advantage_text(best_score)
    recommendation = _generate_recommendation(
        best_move, best_score, move_scores, threats, phase, wp, bp, player_color
    )

    top5 = [
        {
            "move": format_move_to_string(m),
            "score": s,
            "label": _score_label(s),
            "is_capture": _is_capture(m),
            "is_promotion": _is_promotion(m),
            "cap_count": _capture_count(m),
        }
        for m, s in move_scores[:5]
    ]

    threatened_mine = count_threatened_pieces(
        wp, bp, player_color == WHITE
    )
    threatened_opp = count_threatened_pieces(
        wp, bp, player_color != WHITE
    )

    return {
        "best_move": best_move,
        "best_move_str": format_move_to_string(best_move),
        "score": best_score,
        "reached_depth": depth,
        "top_moves": top5,
        "threats": threats,
        "phase": _phase_label(phase),
        "phase_value": phase,
        "advantage": advantage,
        "recommendation": recommendation,
        "piece_balance": len(wp) - len(bp),
        "total_pieces": total,
        "threatened_mine": threatened_mine,
        "threatened_opp": threatened_opp,
        "safety_score": evaluate_safety(wp, bp, player_color == WHITE),
    }
