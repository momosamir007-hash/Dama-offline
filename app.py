""" لعبة الداما الكلاسيكية - واجهة Streamlit المتقدمة
=============================================
النسخة المُصححة والنهائية - تم إصلاح دالة التراجع، التلميحات السريعة، وأمان التزامن
"""

import re
import time
import streamlit as st

# استيراد آمن وتوافق مع وجود أو غياب مكتبة pydraughts
from engine import (
    get_legal_moves, get_board_fen, format_move_to_string, parse_fen_pieces,
    evaluate_position, find_best_move, analyze_position, _is_capture,
    _is_promotion, _capture_count, _phase_label, _game_phase,
    get_threatened_squares, count_pieces, count_threatened_pieces,
    clear_transposition_table, get_tt_stats, DRAUGHTS_AVAILABLE, MAX_DEPTH
)

if DRAUGHTS_AVAILABLE:
    from draughts import Board, WHITE, BLACK
    DRAUGHTS_OK = True
else:
    DRAUGHTS_OK = False
    WHITE, BLACK = 2, 1
    Board = lambda *args, **kwargs: None

st.set_page_config(
    page_title="داما AI | الداما الذكية",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ════════════════════════════════════════════
# CSS الكامل
# ════════════════════════════════════════════
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700;900&display=swap');
    html, body, [class*="css"] {
        direction: rtl;
    }
    .main-title {
        text-align: center;
        font-family: 'Tajawal', sans-serif;
        font-size: 2.6rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FFD700 0%, #FF8C00 50%, #FF4500 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding: 10px 0 2px;
        letter-spacing: 2px;
    }
    .sub-title {
        text-align: center;
        font-family: 'Tajawal', sans-serif;
        color: #8899AA;
        font-size: 0.92rem;
        margin: 0 0 6px;
        letter-spacing: 1px;
    }
    .index-container {
        background: linear-gradient(135deg, rgba(30,40,60,0.97), rgba(20,30,50,0.97));
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: 12px;
        padding: 18px;
        margin: 8px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    .index-title {
        font-size: 1.2rem;
        font-weight: 900;
        color: #FFD700;
        margin-bottom: 10px;
        border-bottom: 2px solid rgba(255,215,0,0.3);
        padding-bottom: 6px;
    }
    .index-item {
        display: flex;
        align-items: center;
        padding: 7px 10px;
        margin: 3px 0;
        border-radius: 7px;
        border: 1px solid transparent;
    }
    .index-item:hover {
        background: rgba(255,215,0,0.1);
        border-color: rgba(255,215,0,0.3);
    }
    .index-icon {
        font-size: 1.15rem;
        margin-left: 9px;
    }
    .index-label {
        font-size: 0.9rem;
        color: #DDD;
        font-weight: 700;
    }
    .index-desc {
        font-size: 0.72rem;
        color: #888;
    }
    .status-box {
        text-align: center;
        padding: 9px 14px;
        border-radius: 10px;
        font-family: 'Tajawal', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        margin: 5px 0;
        direction: rtl;
    }
    .status-player {
        background: linear-gradient(135deg, #1B5E20, #2E7D32);
        color: #FFF;
        border: 2px solid #4CAF50;
    }
    .status-ai {
        background: linear-gradient(135deg, #B71C1C, #C62828);
        color: #FFF;
        border: 2px solid #EF5350;
    }
    .status-win {
        background: linear-gradient(135deg, #F9A825, #FFD54F);
        color: #1A1A1A;
        border: 2px solid #FFD700;
        font-size: 1.35rem;
        animation: pulse 1s infinite;
    }
    .status-lose {
        background: linear-gradient(135deg, #37474F, #546E7A);
        color: #FFF;
        border: 2px solid #78909C;
    }
    .status-draw {
        background: linear-gradient(135deg, #0D47A1, #1565C0);
        color: #FFF;
        border: 2px solid #42A5F5;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    .analysis-card {
        background: linear-gradient(135deg, rgba(12,22,45,0.99), rgba(18,32,65,0.99));
        border: 2px solid rgba(0,200,100,0.4);
        border-radius: 14px;
        padding: 16px;
        margin: 8px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        box-shadow: 0 4px 22px rgba(0,200,100,0.12);
    }
    .analysis-title {
        font-size: 1.1rem;
        font-weight: 900;
        color: #00CC66;
        margin-bottom: 8px;
    }
    .analysis-section {
        margin: 8px 0;
        padding: 9px;
        background: rgba(255,255,255,0.035);
        border-radius: 7px;
        border-right: 3px solid rgba(0,200,100,0.45);
    }
    .analysis-label {
        font-size: 0.78rem;
        color: #888;
        margin-bottom: 3px;
    }
    .analysis-value {
        font-size: 0.92rem;
        color: #EEE;
        font-weight: 700;
    }
    .move-card {
        display: flex;
        align-items: center;
        padding: 7px 11px;
        margin: 3px 0;
        border-radius: 7px;
        border: 1px solid rgba(255,255,255,0.1);
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    .move-card.best {
        background: rgba(0,200,100,0.14);
        border-color: rgba(0,200,100,0.38);
    }
    .move-card.good {
        background: rgba(255,200,0,0.07);
        border-color: rgba(255,200,0,0.28);
    }
    .move-card.neutral {
        background: rgba(100,100,100,0.09);
    }
    .move-card.bad {
        background: rgba(255,60,60,0.07);
        border-color: rgba(255,60,60,0.25);
    }
    .move-rank {
        font-size: 1.05rem;
        margin-left: 7px;
    }
    .move-str {
        font-size: 0.95rem;
        font-weight: 900;
        color: #FFF;
        font-family: monospace;
        min-width: 75px;
    }
    .move-label {
        font-size: 0.75rem;
        color: #AAA;
        margin-right: auto;
    }
    .move-badge {
        font-size: 0.68rem;
        padding: 2px 6px;
        border-radius: 10px;
        margin-right: 4px;
        font-weight: 700;
    }
    .badge-cap {
        background: rgba(255,80,80,0.25);
        color: #FF8888;
    }
    .badge-prom {
        background: rgba(255,200,0,0.25);
        color: #FFD700;
    }
    .eval-container {
        background: rgba(255,255,255,0.045);
        border-radius: 8px;
        padding: 9px 13px;
        margin: 5px 0;
        font-family: 'Tajawal', sans-serif;
    }
    .eval-bar-bg {
        height: 13px;
        border-radius: 6px;
        background: linear-gradient(to left, #EF5350 0%, #FF8C00 25%, #FFC107 40%, #888 50%, #66BB6A 60%, #00C853 75%, #00E676 100%);
        position: relative;
        margin: 5px 0;
        overflow: hidden;
    }
    .eval-marker {
        position: absolute;
        top: 0;
        width: 3px;
        height: 100%;
        background: white;
        border-radius: 2px;
        box-shadow: 0 0 4px rgba(255,255,255,0.8);
    }
    .info-card {
        background: rgba(255,255,255,0.038);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 9px;
        padding: 12px;
        margin: 7px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    .piece-count {
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding: 5px;
    }
    .piece-side {
        text-align: center;
    }
    .piece-num {
        font-size: 1.9rem;
        font-weight: 900;
    }
    .piece-sub {
        font-size: 0.76rem;
        color: #999;
    }
    .history-row {
        display: flex;
        align-items: center;
        padding: 4px 7px;
        margin: 2px 0;
        border-radius: 5px;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        font-size: 0.86rem;
    }
    .history-row:nth-child(odd) {
        background: rgba(255,255,255,0.028);
    }
    .history-row.last-move {
        background: rgba(255,215,0,0.11);
        border: 1px solid rgba(255,215,0,0.28);
        font-weight: 700;
    }
    .h-num {
        color: #666;
        width: 22px;
        flex-shrink: 0;
    }
    .h-who {
        width: 26px;
        flex-shrink: 0;
    }
    .h-move {
        color: #EEE;
        font-family: monospace;
        flex: 1;
    }
    .h-type {
        font-size: 0.72rem;
        color: #888;
    }
    .stButton > button {
        font-family: 'Tajawal', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        transition: all 0.18s !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 5px 18px rgba(0,0,0,0.38) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00C853, #00E676) !important;
        color: #000 !important;
        border: none !important;
    }
    .board-wrap {
        display: flex;
        justify-content: center;
        padding: 6px 0;
    }
    .stat-pill {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 18px;
        font-size: 0.76rem;
        font-family: 'Tajawal', sans-serif;
        margin: 2px 2px;
        font-weight: 700;
    }
    .sg {
        background: rgba(0,200,80,0.18);
        color: #00E676;
    }
    .sb {
        background: rgba(0,150,255,0.18);
        color: #64B5F6;
    }
    .so {
        background: rgba(255,150,0,0.18);
        color: #FFB74D;
    }
    .sr {
        background: rgba(255,80,80,0.18);
        color: #EF9A9A;
    }
    .section-header {
        font-family: 'Tajawal', sans-serif;
        font-size: 1.05rem;
        font-weight: 900;
        color: #FFD700;
        padding: 7px 0;
        border-bottom: 1px solid rgba(255,215,0,0.18);
        margin: 10px 0 7px;
        direction: rtl;
    }
    .hint-box {
        background: rgba(0,200,100,0.07);
        border: 1px solid rgba(0,200,100,0.28);
        border-radius: 7px;
        padding: 9px 13px;
        margin: 5px 0;
        font-family: 'Tajawal', sans-serif;
        font-size: 0.88rem;
        direction: rtl;
        color: #88FFBB;
    }
    .safety-box {
        display: flex;
        gap: 8px;
        margin: 6px 0;
        direction: rtl;
    }
    .safety-item {
        flex: 1;
        text-align: center;
        padding: 8px;
        border-radius: 8px;
        font-family: 'Tajawal', sans-serif;
    }
    .safety-good {
        background: rgba(0,200,80,0.12);
        border: 1px solid rgba(0,200,80,0.3);
    }
    .safety-warn {
        background: rgba(255,80,80,0.12);
        border: 1px solid rgba(255,80,80,0.3);
    }
    .safety-num {
        font-size: 1.5rem;
        font-weight: 900;
    }
    .safety-lbl {
        font-size: 0.72rem;
        color: #999;
    }
    .welcome-feature {
        display: flex;
        align-items: flex-start;
        padding: 9px 13px;
        margin: 5px 0;
        border-radius: 9px;
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.07);
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        gap: 11px;
    }
    .wf-icon {
        font-size: 1.5rem;
        flex-shrink: 0;
    }
    .wf-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #FFD700;
        margin-bottom: 2px;
    }
    .wf-desc {
        font-size: 0.78rem;
        color: #999;
        line-height: 1.4;
    }
    .game-over-stats {
        background: linear-gradient(135deg, rgba(12,22,45,0.99), rgba(18,32,65,0.99));
        border: 2px solid rgba(255,215,0,0.28);
        border-radius: 13px;
        padding: 18px;
        margin: 8px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# دوال مساعدة
# ════════════════════════════════════════════
def fmt(move) -> str:
    """تنسيق الحركة للعرض"""
    result = format_move_to_string(move)
    return result if result and result != "?" else "حركة"


def get_piece_counts(board):
    """
    حساب عدد القطع لكل جانب باستخدام FEN.
    يُرجع (w_men, w_kings, b_men, b_kings)
    """
    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    w_men = sum(1 for _, k in wp if not k)
    w_kings = sum(1 for _, k in wp if k)
    b_men = sum(1 for _, k in bp if not k)
    b_kings = sum(1 for _, k in bp if k)
    return w_men, w_kings, b_men, b_kings


def is_game_over(board) -> bool:
    """التحقق من انتهاء اللعبة"""
    try:
        if hasattr(board, 'is_over') and board.is_over():
            return True
    except Exception:
        pass
    return len(get_legal_moves(board)) == 0


def get_winner(board, player_color, ai_color):
    """
    تحديد الفائز.
    يُرجع: 'player' | 'ai' | 'draw' | None
    """
    if not is_game_over(board):
        return None
    wm, wk, bm, bk = get_piece_counts(board)
    wt = wm + wk
    bt = bm + bk
    if wt == 0 and bt == 0:
        return 'draw'
    if wt == 0:
        return 'ai' if player_color == WHITE else 'player'
    if bt == 0:
        return 'ai' if player_color == BLACK else 'player'
    if board.turn == ai_color:
        return 'player'
    return 'ai'


def eval_to_pct(score: float) -> float:
    """
    تحويل نقاط التقييم إلى نسبة مئوية (0-100).
    50 = تعادل | أكبر = اللاعب أفضل | أصغر = AI أفضل
    """
    return max(2.0, min(98.0, 50.0 + float(score) / 80.0))


# ════════════════════════════════════════════
# رسم السهم على الرقعة
# ════════════════════════════════════════════
def _draw_arrow(svg_parts, mv_str, sq_coords, arrow_color, marker_id, dash_style, opacity_val):
    """رسم سهم على الرقعة لتمثيل الحركة"""
    if not mv_str:
        return
    valid_nums = []
    for n in re.findall(r'\d+', mv_str):
        try:
            v = int(n)
            if v in sq_coords:
                valid_nums.append(v)
        except ValueError:
            pass
    if len(valid_nums) < 2:
        return
    pts = " ".join(
        f"{sq_coords[n][0]},{sq_coords[n][1]}" for n in valid_nums
    )
    svg_parts.append(
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{arrow_color}" stroke-width="6" {dash_style} '
        f'marker-end="url(#{marker_id})" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{opacity_val}"/>'
    )


# ════════════════════════════════════════════
# رسم الرقعة SVG
# ════════════════════════════════════════════
def render_board(board, last_move="", hint_move="", threatened_squares=None) -> str:
    """
    رسم رقعة الداما كـ SVG كامل.
    - last_move: سهم برتقالي للحركة الأخيرة
    - hint_move: سهم أخضر منقط للتلميح
    - threatened_squares: مجموعة مربعات القطع المهددة
    """
    CELL_SIZE = 66
    BOARD_SZ = CELL_SIZE * 8
    MARGIN = 30
    TOTAL_SIZE = BOARD_SZ + MARGIN * 2
    PIECE_R = 26
    INNER_R = 18

    TS = threatened_squares if threatened_squares else set()
    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    piece_map = {}
    for sq, is_king in wp:
        piece_map[sq] = ('w', is_king)
    for sq, is_king in bp:
        piece_map[sq] = ('b', is_king)

    hl_last = set()
    if last_move:
        for n in re.findall(r'\d+', last_move):
            try:
                hl_last.add(int(n))
            except ValueError:
                pass
    hl_hint = set()
    if hint_move:
        for n in re.findall(r'\d+', hint_move):
            try:
                hl_hint.add(int(n))
            except ValueError:
                pass

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {TOTAL_SIZE} {TOTAL_SIZE}" width="100%" '
        f'style="max-width:{TOTAL_SIZE}px;display:block;margin:0 auto">'
    )
    svg.append("""<defs>
        <filter id="sh">
            <feDropShadow dx="1" dy="2" stdDeviation="3" flood-opacity="0.6"/>
        </filter>
        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="b"/>
            <feMerge>
                <feMergeNode in="b"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <filter id="danger-glow">
            <feGaussianBlur stdDeviation="4" result="b"/>
            <feMerge>
                <feMergeNode in="b"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <radialGradient id="wg" cx="38%" cy="32%" r="60%">
            <stop offset="0%" stop-color="#FFFFFF"/>
            <stop offset="55%" stop-color="#EDD9A3"/>
            <stop offset="100%" stop-color="#C8A050"/>
        </radialGradient>
        <radialGradient id="bg" cx="38%" cy="32%" r="60%">
            <stop offset="0%" stop-color="#666666"/>
            <stop offset="55%" stop-color="#2A2A2A"/>
            <stop offset="100%" stop-color="#0A0A0A"/>
        </radialGradient>
        <marker id="last-arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0 0 L10 5 L0 10z" fill="#FF4500"/>
        </marker>
        <marker id="hint-arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0 0 L10 5 L0 10z" fill="#00DD55"/>
        </marker>
    </defs>""")

    # الإطار الخشبي
    svg.append(
        f'<rect x="0" y="0" width="{TOTAL_SIZE}" height="{TOTAL_SIZE}" '
        f'rx="10" fill="#4A2C10"/>'
    )
    svg.append(
        f'<rect x="{MARGIN - 5}" y="{MARGIN - 5}" '
        f'width="{BOARD_SZ + 10}" height="{BOARD_SZ + 10}" '
        f'rx="5" fill="#2D1A08" stroke="#7A5028" stroke-width="1.5"/>'
    )

    # حروف الأعمدة
    for col_i in range(8):
        cx = MARGIN + col_i * CELL_SIZE + CELL_SIZE // 2
        svg.append(
            f'<text x="{cx}" y="{MARGIN - 10}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{chr(65 + col_i)}</text>'
        )

    # أرقام الصفوف
    for row_i in range(8):
        cy = MARGIN + row_i * CELL_SIZE + CELL_SIZE // 2 + 5
        svg.append(
            f'<text x="{MARGIN - 14}" y="{cy}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{8 - row_i}</text>'
        )

    sq_number = 0
    sq_coords = {}
    for row in range(8):
        for col in range(8):
            x_pos = MARGIN + col * CELL_SIZE
            y_pos = MARGIN + row * CELL_SIZE
            is_dark = (row + col) % 2 == 1
            sq_color = "#B58863" if is_dark else "#F0D9B5"
            svg.append(
                f'<rect x="{x_pos}" y="{y_pos}" '
                f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                f'fill="{sq_color}"/>'
            )
            if is_dark:
                sq_number += 1
            center_x = x_pos + CELL_SIZE // 2
            center_y = y_pos + CELL_SIZE // 2
            sq_coords[sq_number] = (center_x, center_y)

            # تظليل آخر حركة
            if sq_number in hl_last:
                svg.append(
                    f'<rect x="{x_pos}" y="{y_pos}" '
                    f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="rgba(255,220,50,0.30)"/>'
                )
            # تظليل التلميح
            if sq_number in hl_hint:
                svg.append(
                    f'<rect x="{x_pos}" y="{y_pos}" '
                    f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="rgba(0,220,80,0.20)"/>'
                )
            # تظليل القطع المهددة بالأحمر
            if sq_number in TS:
                svg.append(
                    f'<rect x="{x_pos}" y="{y_pos}" '
                    f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="rgba(255,30,30,0.22)"/>'
                )
                svg.append(
                    f'<rect x="{x_pos}" y="{y_pos}" '
                    f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'fill="none" stroke="rgba(255,60,60,0.6)" '
                    f'stroke-width="2"/>'
                )

            # رقم المربع
            svg.append(
                f'<text x="{x_pos + 4}" y="{y_pos + 14}" '
                f'font-size="10" fill="rgba(255,255,255,0.26)" '
                f'font-family="monospace">{sq_number}</text>'
            )

            # رسم القطعة
            if sq_number in piece_map:
                piece_color, is_king = piece_map[sq_number]
                gradient = "url(#wg)" if piece_color == 'w' else "url(#bg)"
                stroke_c = "#BFA070" if piece_color == 'w' else "#111111"
                inner_c = "#D4B896" if piece_color == 'w' else "#2A2A2A"
                is_danger = sq_number in TS

                # ظل القطعة
                svg.append(
                    f'<circle cx="{center_x + 1}" cy="{center_y + 3}" '
                    f'r="{PIECE_R}" fill="rgba(0,0,0,0.4)"/>'
                )
                # جسم القطعة
                if is_danger:
                    svg.append(
                        f'<circle cx="{center_x}" cy="{center_y}" '
                        f'r="{PIECE_R}" fill="{gradient}" '
                        f'stroke="#FF4444" stroke-width="3.5" '
                        f'filter="url(#danger-glow)"/>'
                    )
                else:
                    svg.append(
                        f'<circle cx="{center_x}" cy="{center_y}" '
                        f'r="{PIECE_R}" fill="{gradient}" '
                        f'stroke="{stroke_c}" stroke-width="2.5" '
                        f'filter="url(#sh)"/>'
                    )
                # الحلقة الداخلية
                svg.append(
                    f'<circle cx="{center_x}" cy="{center_y}" '
                    f'r="{INNER_R}" fill="none" stroke="{inner_c}" '
                    f'stroke-width="1.5" opacity="0.5"/>'
                )
                # رمز الملك
                if is_king:
                    crown_color = "#DAA520" if piece_color == 'w' else "#FFD700"
                    svg.append(
                        f'<text x="{center_x}" y="{center_y + 8}" '
                        f'text-anchor="middle" font-size="24" '
                        f'fill="{crown_color}" font-weight="bold" '
                        f'filter="url(#glow)">♛</text>'
                    )
                # أيقونة التحذير للقطع المهددة
                if is_danger:
                    svg.append(
                        f'<text x="{center_x + 18}" y="{center_y - 14}" '
                        f'font-size="14" fill="#FF4444">⚠</text>'
                    )

    # حدود الرقعة
    svg.append(
        f'<rect x="{MARGIN}" y="{MARGIN}" '
        f'width="{BOARD_SZ}" height="{BOARD_SZ}" '
        f'fill="none" stroke="#4A2C10" stroke-width="2"/>'
    )

    # رسم الأسهم
    _draw_arrow(
        svg, last_move, sq_coords, "#FF4500", "last-arr", "", "0.80"
    )
    _draw_arrow(
        svg, hint_move, sq_coords, "#00DD55", "hint-arr", 'stroke-dasharray="10,6"', "0.90"
    )

    svg.append('</svg>')
    return '\n'.join(svg)


# ════════════════════════════════════════════
# فهرس البرنامج
# ════════════════════════════════════════════
def render_index():
    """عرض فهرس تفاعلي كامل لجميع مكونات البرنامج"""
    st.markdown("""
    <div class="index-container">
        <div class="index-title">📋 فهرس البرنامج</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;direction:rtl">
            <div class="index-item">
                <span class="index-icon">🎮</span>
                <span>
                    <div class="index-label">رقعة اللعب</div>
                    <div class="index-desc">8×8 | 12 قطعة لكل جانب</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">🧠</span>
                <span>
                    <div class="index-label">محرك AI</div>
                    <div class="index-desc">Minimax + Alpha-Beta | عمق 24</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">💡</span>
                <span>
                    <div class="index-label">مساعد عبقري</div>
                    <div class="index-desc">تحليل عميق + أفضل 5 حركات</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">🛡️</span>
                <span>
                    <div class="index-label">تحليل السلامة</div>
                    <div class="index-desc">كشف التهديدات لحظياً</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">🍴</span>
                <span>
                    <div class="index-label">كشف الشوكات</div>
                    <div class="index-desc">Forks + Traps + Decoys</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">⚡</span>
                <span>
                    <div class="index-label">Aspiration Windows</div>
                    <div class="index-desc">بحث أسرع وأكثر دقة</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">🔬</span>
                <span>
                    <div class="index-label">Quiescence Search</div>
                    <div class="index-desc">استقرار الأكل | تم تصحيح الأكل الإجباري</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">📚</span>
                <span>
                    <div class="index-label">كتاب الافتتاحيات</div>
                    <div class="index-desc">5 افتتاحيات كلاسيكية</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">🔀</span>
                <span>
                    <div class="index-label">Zobrist Hashing</div>
                    <div class="index-desc">TT بحجم 1,000,000 إدخال</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">📊</span>
                <span>
                    <div class="index-label">PST + Structures</div>
                    <div class="index-desc">تقييم موضعي متعدد المراحل</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">🎯</span>
                <span>
                    <div class="index-label">LMR + Null Move</div>
                    <div class="index-desc">Late Move Reduction متقدم</div>
                </span>
            </div>
            <div class="index-item">
                <span class="index-icon">📜</span>
                <span>
                    <div class="index-label">سجل الحركات</div>
                    <div class="index-desc">تراجع فوري (Instant Undo)</div>
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# لوحة التحليل الذكي
# ════════════════════════════════════════════
def render_analysis_panel(analysis: dict):
    """عرض نتائج التحليل العميق بشكل منسق وكامل"""
    if not analysis or "error" in analysis:
        err_msg = analysis.get("error", "خطأ غير معروف") if analysis else "لا يوجد تحليل"
        st.error(f"❌ {err_msg}")
        return

    st.markdown(
        '<div class="analysis-title">🧠 تحليل المحرك العبقري</div>',
        unsafe_allow_html=True
    )

    # التفوق ومرحلة اللعبة
    adv_col, phase_col = st.columns(2)
    with adv_col:
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">التفوق الحالي</div>'
            f'<div class="analysis-value">{analysis.get("advantage", "—")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with phase_col:
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">مرحلة اللعبة</div>'
            f'<div class="analysis-value">🎯 {analysis.get("phase", "—")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # صندوق السلامة
    threatened_mine = analysis.get("threatened_mine", 0)
    threatened_opp = analysis.get("threatened_opp", 0)
    mine_class = "safety-warn" if threatened_mine > 0 else "safety-good"
    opp_class = "safety-good" if threatened_opp > 0 else "safety-good"
    mine_icon = "⚠️" if threatened_mine > 0 else "✅"
    opp_icon = "🎯" if threatened_opp > 0 else "—"
    st.markdown(
        f'<div class="safety-box">'
        f'<div class="safety-item {mine_class}">'
        f'<div class="safety-num">{mine_icon} {threatened_mine}</div>'
        f'<div class="safety-lbl">قطعك المهددة</div>'
        f'</div>'
        f'<div class="safety-item {opp_class}">'
        f'<div class="safety-num">{opp_icon} {threatened_opp}</div>'
        f'<div class="safety-lbl">قطع الخصم المهددة</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # التوصية
    recommendation = analysis.get("recommendation", "")
    if recommendation:
        rec_html = recommendation.replace('\n', '<br>')
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">💬 توصية المحرك</div>'
            f'<div class="analysis-value" style="line-height:1.7">'
            f'{rec_html}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # أفضل 5 حركات
    top_moves = analysis.get("top_moves", [])
    if top_moves:
        st.markdown(
            '<div class="analysis-label" style="margin-top:9px">'
            '🏆 أفضل الحركات:'
            '</div>',
            unsafe_allow_html=True
        )
        rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        card_styles = ["best", "good", "neutral", "neutral", "bad"]
        for idx, mv_data in enumerate(top_moves):
            rank_icon = rank_icons[idx] if idx < len(rank_icons) else "▪️"
            card_style = card_styles[idx] if idx < len(card_styles) else "neutral"
            mv_str = mv_data.get("move", "?")
            mv_label = mv_data.get("label", "")
            mv_score = mv_data.get("score", 0)
            is_cap = mv_data.get("is_capture", False)
            is_prom = mv_data.get("is_promotion", False)
            cap_n = mv_data.get("cap_count", 0)

            badges_html = ""
            if is_cap:
                badges_html += (
                    f'<span class="move-badge badge-cap">⚔️ ×{cap_n}</span>'
                )
            if is_prom:
                badges_html += (
                    '<span class="move-badge badge-prom">👑</span>'
                )

            st.markdown(
                f'<div class="move-card {card_style}">'
                f'<span class="move-rank">{rank_icon}</span>'
                f'<span class="move-str">{mv_str}</span>'
                f'{badges_html}'
                f'<span class="move-label">{mv_label} | {mv_score:+.0f}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # التهديدات
    threats = analysis.get("threats", [])
    if threats:
        st.markdown(
            '<div class="analysis-label" style="margin-top:9px">'
            '⚠️ التهديدات والملاحظات:'
            '</div>',
            unsafe_allow_html=True
        )
        for threat_text in threats:
            st.markdown(
                f'<div style="font-family:Tajawal;font-size:0.86rem;'
                f'color:#CCC;padding:2px 0;direction:rtl">'
                f'{threat_text}</div>',
                unsafe_allow_html=True
            )

    # معلومات البحث
    reached_depth = analysis.get("reached_depth", 0)
    analysis_time = analysis.get("analysis_time", "")
    time_text = f" | ⏱ {analysis_time}" if analysis_time else ""
    st.markdown(
        f'<div style="margin-top:8px;font-family:Tajawal;font-size:0.78rem;'
        f'color:#555;direction:rtl">'
        f'🔬 عمق البحث: <b style="color:#777">{reached_depth}</b>'
        f'{time_text}'
        f'</div>',
        unsafe_allow_html=True
    )


# ════════════════════════════════════════════
# إدارة حالة اللعبة
# ════════════════════════════════════════════
def init_game(player_color, ai_color, depth, time_limit):
    """تهيئة لعبة جديدة وإعادة ضبط جميع متغيرات الحالة"""
    clear_transposition_table()
    board = Board(variant="english")
    st.session_state['board'] = board
    st.session_state['initial_fen'] = get_board_fen(board)
    st.session_state['player_color'] = player_color
    st.session_state['ai_color'] = ai_color
    st.session_state['depth'] = depth
    st.session_state['time_limit'] = time_limit
    st.session_state['move_history'] = []  # سيحتوي الآن على FEN أيضاً لتسريع التراجع
    st.session_state['game_over'] = False
    st.session_state['winner'] = None
    st.session_state['last_move'] = ""
    st.session_state['hint_move'] = ""
    st.session_state['ai_info'] = ""
    st.session_state['game_started'] = True
    st.session_state['pending_ai'] = (board.turn == ai_color)
    st.session_state['celebrated'] = False
    st.session_state['analysis'] = None
    st.session_state['show_analysis'] = False
    st.session_state['move_count'] = 0
    st.session_state['captures_w'] = 0
    st.session_state['captures_b'] = 0
    st.session_state['threatened_sqs'] = set()


def play_human_move(chosen_move):
    """تنفيذ الحركة المختارة من اللاعب البشري (تم تأمين الاستدعاء)"""
    if st.session_state.get('game_over'):
        return
    
    board = st.session_state['board']
    move_str = fmt(chosen_move)
    is_cap = _is_capture(chosen_move)
    is_prom = _is_promotion(chosen_move)

    board.push(chosen_move)
    current_fen = get_board_fen(board)

    if is_cap:
        move_type = "⚔️"
    elif is_prom:
        move_type = "👑"
    else:
        move_type = "➡️"

    # إضافة FEN لتسريع عملية التراجع لاحقاً
    st.session_state['move_history'].append(("👤", move_str, move_type, current_fen))
    st.session_state['last_move'] = move_str
    st.session_state['hint_move'] = ""
    st.session_state['analysis'] = None
    st.session_state['show_analysis'] = False
    st.session_state['move_count'] = st.session_state.get('move_count', 0) + 1
    st.session_state['threatened_sqs'] = set()

    if is_cap:
        if st.session_state['player_color'] == WHITE:
            st.session_state['captures_w'] = st.session_state.get('captures_w', 0) + 1
        else:
            st.session_state['captures_b'] = st.session_state.get('captures_b', 0) + 1

    if is_game_over(board):
        st.session_state['game_over'] = True
        st.session_state['winner'] = get_winner(
            board, st.session_state['player_color'], st.session_state['ai_color']
        )
    else:
        st.session_state['pending_ai'] = True


def play_ai_move():
    """تنفيذ حركة الذكاء الاصطناعي"""
    board = st.session_state['board']
    ai_color = st.session_state['ai_color']
    depth = st.session_state['depth']
    time_limit = st.session_state.get('time_limit', 5.0)
    
    best_move, score, reached_depth = find_best_move(
        board, ai_color, max_depth=depth, time_limit=time_limit
    )
    
    if best_move is not None:
        move_str = fmt(best_move)
        is_cap = _is_capture(best_move)
        is_prom = _is_promotion(best_move)
        
        board.push(best_move)
        current_fen = get_board_fen(board)

        if is_cap:
            move_type = "⚔️"
        elif is_prom:
            move_type = "👑"
        else:
            move_type = "➡️"

        # حفظ FEN لتسريع عملية التراجع
        st.session_state['move_history'].append(("🤖", move_str, move_type, current_fen))
        st.session_state['last_move'] = move_str
        st.session_state['hint_move'] = ""
        st.session_state['analysis'] = None
        st.session_state['move_count'] = st.session_state.get('move_count', 0) + 1

        if is_cap:
            if st.session_state['ai_color'] == WHITE:
                st.session_state['captures_w'] = st.session_state.get('captures_w', 0) + 1
            else:
                st.session_state['captures_b'] = st.session_state.get('captures_b', 0) + 1

        tt_stats = get_tt_stats()
        st.session_state['ai_info'] = (
            f"عمق: **{reached_depth}** | "
            f"تقييم: **{score:+.0f}** | "
            f"TT: **{tt_stats['size']:,}** | "
            f"إصابة: **{tt_stats['hit_rate']}**"
        )

        try:
            wp_now, bp_now = parse_fen_pieces(current_fen)
            player_c = st.session_state['player_color']
            threatened = get_threatened_squares(wp_now, bp_now, player_c)
            st.session_state['threatened_sqs'] = threatened
        except Exception:
            st.session_state['threatened_sqs'] = set()

        if is_game_over(board):
            st.session_state['game_over'] = True
            st.session_state['winner'] = get_winner(
                board, st.session_state['player_color'], ai_color
            )
        else:
            st.session_state['pending_ai'] = False
    else:
        st.session_state['game_over'] = True
        st.session_state['winner'] = 'player'
        st.session_state['pending_ai'] = False


def undo_move():
    """
    التراجع عن آخر حركتين (اللاعب + AI) بلمح البصر (Instant Undo).
    تم تغيير النظام ليستخدم FEN بدلاً من إعادة محاكاة اللعبة من الصفر!
    """
    history = st.session_state.get('move_history', [])
    if not history:
        return
        
    moves_to_remove = min(2, len(history))
    remaining_history = history[:-moves_to_remove]

    # جلب حالة الرقعة (FEN) من الحركة الأخيرة المتبقية أو من البداية
    if remaining_history:
        last_fen = remaining_history[-1][3]
        last_move_str = remaining_history[-1][1]
    else:
        last_fen = st.session_state.get('initial_fen', "")
        last_move_str = ""

    # استعادة الرقعة في جزء من الثانية
    if last_fen:
        new_board = Board(variant="english", fen=last_fen)
    else:
        new_board = Board(variant="english")

    st.session_state['board'] = new_board
    st.session_state['move_history'] = remaining_history
    st.session_state['game_over'] = False
    st.session_state['winner'] = None
    st.session_state['last_move'] = last_move_str
    st.session_state['hint_move'] = ""
    st.session_state['pending_ai'] = False
    st.session_state['celebrated'] = False
    st.session_state['analysis'] = None
    st.session_state['show_analysis'] = False
    st.session_state['threatened_sqs'] = set()


# ════════════════════════════════════════════
# الواجهة الرئيسية
# ════════════════════════════════════════════
def main():
    inject_css()

    # فحص المكتبة بأمان ومنع انهيار البرنامج
    if not DRAUGHTS_OK or not DRAUGHTS_AVAILABLE:
        st.error("❌ مكتبة `pydraughts` غير مثبتة!")
        st.info("قم بتثبيتها بتنفيذ الأمر:")
        st.code("pip install pydraughts", language="bash")
        st.stop()

    # ════════════════════════════════════════
    # الشريط الجانبي
    # ════════════════════════════════════════
    with st.sidebar:
        st.markdown(
            '<div style="text-align:center;font-family:Tajawal;'
            'font-size:1.45rem;font-weight:900;color:#FFD700;'
            'padding:8px 0 3px">♟️ داما AI</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="text-align:center;font-family:Tajawal;'
            'font-size:0.78rem;color:#666;padding-bottom:6px">'
            'الداما الكلاسيكية بذكاء اصطناعي متقدم'
            '</div>',
            unsafe_allow_html=True
        )

        with st.expander("📋 فهرس البرنامج", expanded=False):
            render_index()

        st.markdown("---")
        st.markdown(
            '<div class="section-header">⚙️ إعدادات اللعبة</div>',
            unsafe_allow_html=True
        )

        color_choice = st.radio(
            "اختر لونك:",
            ["⬜ أبيض (تبدأ أنت)", "⬛ أسود (يبدأ الكمبيوتر)"],
            index=0,
            key="color_radio"
        )

        difficulty = st.select_slider(
            "🎯 مستوى الصعوبة",
            options=["مبتدئ", "سهل", "متوسط", "صعب", "خبير", "عبقري"],
            value="متوسط",
            key="diff_slider"
        )

        depth_map = {
            "مبتدئ": 2,
            "سهل": 3,
            "متوسط": 6,
            "صعب": 10,
            "خبير": 14,
            "عبقري": 24,
        }
        time_map = {
            "مبتدئ": 1.0,
            "سهل": 2.0,
            "متوسط": 5.0,
            "صعب": 8.0,
            "خبير": 12.0,
            "عبقري": 20.0,
        }

        chosen_depth = depth_map[difficulty]
        chosen_time = time_map[difficulty]
        st.markdown(
            f'<div style="font-family:Tajawal;font-size:0.8rem;'
            f'color:#666;direction:rtl;margin-top:-5px;margin-bottom:4px">'
            f'عمق {chosen_depth} | وقت {chosen_time:.0f}ث'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            new_game_pressed = st.button(
                "🆕 لعبة جديدة",
                use_container_width=True,
                key="btn_new_game"
            )
        with btn_col2:
            history_len = len(st.session_state.get('move_history', []))
            undo_enabled = (
                st.session_state.get("game_started", False) and history_len > 0
            )
            undo_pressed = st.button(
                "↩️ تراجع",
                use_container_width=True,
                disabled=not undo_enabled,
                key="btn_undo_sidebar"
            )

        if new_game_pressed:
            if "أبيض" in color_choice:
                player_c = WHITE
                ai_c = BLACK
            else:
                player_c = BLACK
                ai_c = WHITE
            init_game(player_c, ai_c, chosen_depth, chosen_time)
            st.rerun()

        if undo_pressed and st.session_state.get("game_started"):
            undo_move()
            st.rerun()

        # ─── إحصائيات اللعبة ───
        if st.session_state.get("game_started"):
            st.markdown("---")
            st.markdown(
                '<div class="section-header">📊 إحصائيات</div>',
                unsafe_allow_html=True
            )
            board = st.session_state['board']
            wm, wk, bm, bk = get_piece_counts(board)
            wt = wm + wk
            bt = bm + bk
            st.markdown(
                f'<div class="info-card">'
                f'<div class="piece-count">'
                f'<div class="piece-side">'
                f'<div style="font-size:1.2rem">⬜</div>'
                f'<div class="piece-num">{wt}</div>'
                f'<div class="piece-sub">{wm}♟ {wk}👑</div>'
                f'</div>'
                f'<div style="font-size:1.1rem;color:#555">⚔️</div>'
                f'<div class="piece-side">'
                f'<div style="font-size:1.2rem">⬛</div>'
                f'<div class="piece-num">{bt}</div>'
                f'<div class="piece-sub">{bm}♟ {bk}👑</div>'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            tt_stats = get_tt_stats()
            move_count = st.session_state.get('move_count', 0)
            st.markdown(
                f'<div style="direction:rtl;font-family:Tajawal;margin:5px 0">'
                f'<span class="stat-pill sg">🎯 {move_count} حركة</span>'
                f'<span class="stat-pill sb">💾 {tt_stats["size"]:,}</span>'
                f'<span class="stat-pill so">📈 {tt_stats["hit_rate"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            ai_info = st.session_state.get('ai_info', '')
            if ai_info:
                st.markdown(
                    f'<div class="info-card" style="font-size:0.82rem;'
                    f'direction:rtl">🤖 {ai_info}</div>',
                    unsafe_allow_html=True
                )

        # ─── سجل الحركات ───
        move_history = st.session_state.get('move_history', [])
        if move_history:
            st.markdown("---")
            st.markdown(
                '<div class="section-header">📜 سجل الحركات</div>',
                unsafe_allow_html=True
            )
            with st.container(height=230):
                for move_idx, move_item in enumerate(move_history, 1):
                    who_icon = move_item[0]
                    mv_str = move_item[1]
                    mv_type = move_item[2] if len(move_item) > 2 else "➡️"
                    is_latest = (move_idx == len(move_history))
                    row_class = "history-row last-move" if is_latest else "history-row"
                    st.markdown(
                        f'<div class="{row_class}">'
                        f'<span class="h-num">{move_idx}</span>'
                        f'<span class="h-who">{who_icon}</span>'
                        f'<span class="h-move">{mv_str}</span>'
                        f'<span class="h-type">{mv_type}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

    # ════════════════════════════════════════
    # المنطقة الرئيسية
    # ════════════════════════════════════════
    st.markdown(
        '<div class="main-title">♟️ داما الذكاء الاصطناعي</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-title">'
        'Minimax عمق 24 | Alpha-Beta | TT 1M | LMR | '
        'Quiescence | Aspiration | Safety | Forks | PST'
        '</div>',
        unsafe_allow_html=True
    )

    # ─── شاشة الترحيب ───
    if not st.session_state.get("game_started"):
        st.markdown("---")
        render_index()
        st.markdown(
            '<div style="font-family:Tajawal;font-size:1.05rem;'
            'font-weight:700;color:#FFD700;text-align:center;'
            'margin:14px 0 8px;direction:rtl">✨ مميزات البرنامج</div>',
            unsafe_allow_html=True
        )
        welcome_col1, welcome_col2 = st.columns(2)
        with welcome_col1:
            st.markdown("""
            <div class="welcome-feature">
                <span class="wf-icon">🧠</span>
                <div>
                    <div class="wf-title">ذكاء اصطناعي عبقري</div>
                    <div class="wf-desc"> Minimax بعمق 24 مع Aspiration Windows وكتاب افتتاحيات كلاسيكية </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">🛡️</span>
                <div>
                    <div class="wf-title">تحليل السلامة الكامل</div>
                    <div class="wf-desc"> يكشف القطع المهددة لحظياً ويتجنب إعطاء الخصم فرص الأكل </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">🍴</span>
                <div>
                    <div class="wf-title">كشف الشوكات والفخاخ</div>
                    <div class="wf-desc"> يبني مواقف تهدد عدة قطع في آنٍ واحد ويخدع الخصم بتكتيكات متقدمة </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with welcome_col2:
            st.markdown("""
            <div class="welcome-feature">
                <span class="wf-icon">⚡</span>
                <div>
                    <div class="wf-title">سرعة قصوى</div>
                    <div class="wf-desc"> TT بحجم مليون موضع + Zobrist Hashing + LMR + Counter Moves </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">💡</span>
                <div>
                    <div class="wf-title">مساعد استراتيجي عبقري</div>
                    <div class="wf-desc"> أفضل 5 حركات مع تقييم تفصيلي ونصائح بالعربية حسب المرحلة </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">🔬</span>
                <div>
                    <div class="wf-title">Quiescence Search</div>
                    <div class="wf-desc"> يتابع الأكل الإجباري تلقائياً لتجنب السقوط في فخاخ الخصم </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")
        st.info("👈 اضغط **'🆕 لعبة جديدة'** لبدء اللعب", icon="🎮")
        demo_board = Board(variant="english")
        st.markdown(
            f'<div class="board-wrap">'
            f'{render_board(demo_board)}'
            f'</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # ─── تنفيذ حركة AI ───
    if (st.session_state.get('pending_ai') and not st.session_state.get('game_over')):
        with st.spinner("🤖 المحرك يحسب أفضل حركة..."):
            play_ai_move()
        st.rerun()

    board = st.session_state['board']
    player_color = st.session_state['player_color']
    ai_color = st.session_state['ai_color']
    threatened = st.session_state.get('threatened_sqs', set())

    # ─── تخطيط ثنائي: رقعة | تحليل ───
    col_board, col_analysis = st.columns([1.05, 0.95])

    # ════════════════════════════════════════
    # عمود الرقعة
    # ════════════════════════════════════════
    with col_board:
        # رسالة الحالة
        if st.session_state.get('game_over'):
            winner = st.session_state.get('winner')
            if winner == 'player':
                st.markdown(
                    '<div class="status-box status-win">'
                    '🎉 مبروك! لقد فزت! 🏆'
                    '</div>',
                    unsafe_allow_html=True
                )
                if not st.session_state.get('celebrated'):
                    st.balloons()
                    st.session_state['celebrated'] = True
            elif winner == 'ai':
                st.markdown(
                    '<div class="status-box status-lose">'
                    '💻 الكمبيوتر فاز هذه المرة! حاول مجدداً 💪'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-box status-draw">'
                    '🤝 انتهت اللعبة بالتعادل!'
                    '</div>',
                    unsafe_allow_html=True
                )
        else:
            if board.turn == player_color:
                available_moves = len(get_legal_moves(board))
                threatened_warning = (
                    f" | ⚠️ {len(threatened)} قطعة مهددة!" if threatened else ""
                )
                st.markdown(
                    f'<div class="status-box status-player">'
                    f'👤 دورك الآن | {available_moves} حركة متاحة'
                    f'{threatened_warning}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-box status-ai">'
                    '🤖 دور المحرك، يرجى الانتظار...'
                    '</div>',
                    unsafe_allow_html=True
                )

        # رسم الرقعة
        board_svg = render_board(
            board,
            st.session_state.get('last_move', ''),
            st.session_state.get('hint_move', ''),
            threatened
        )
        st.markdown(
            f'<div class="board-wrap">{board_svg}</div>',
            unsafe_allow_html=True
        )

        # ─── أدوات اللاعب (فقط في دوره) ───
        if (not st.session_state.get('game_over') and board.turn == player_color):
            legal_moves = get_legal_moves(board)
            if legal_moves:
                move_labels = []
                move_mapping = {}
                for mv in legal_moves:
                    base_label = fmt(mv)
                    display_label = base_label
                    if _is_capture(mv):
                        display_label += f" ⚔️×{_capture_count(mv)}"
                    elif _is_promotion(mv):
                        display_label += " 👑"
                    move_labels.append(display_label)
                    move_mapping[display_label] = mv
                
                # استخدام سلسلة نصية كمفتاح لتجنب مشاكل المزامنة (Index Out Of Bounds)
                selected_label = st.selectbox(
                    "🎯 اختر حركتك:",
                    options=move_labels,
                    key="move_selectbox"
                )
                
                action_c1, action_c2, action_c3 = st.columns(3)
                with action_c1:
                    if st.button(
                        "▶️ العب!",
                        use_container_width=True,
                        type="primary",
                        key="btn_play_move"
                    ):
                        chosen_move = move_mapping[selected_label]
                        play_human_move(chosen_move)
                        st.rerun()
                with action_c2:
                    history_len_now = len(
                        st.session_state.get('move_history', [])
                    )
                    if st.button(
                        "↩️ تراجع",
                        use_container_width=True,
                        key="btn_undo_inline",
                        disabled=(history_len_now == 0)
                    ):
                        undo_move()
                        st.rerun()
                with action_c3:
                    if st.button(
                        "🔄 تحديث",
                        use_container_width=True,
                        key="btn_refresh"
                    ):
                        st.rerun()
                # عرض التلميح النصي
                current_hint = st.session_state.get('hint_move', '')
                if current_hint:
                    st.markdown(
                        f'<div class="hint-box">'
                        f'💡 <b>التلميح المقترح:</b> {current_hint}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.warning("⚠️ لا توجد حركات متاحة!")

    # ════════════════════════════════════════
    # عمود التحليل
    # ════════════════════════════════════════
    with col_analysis:
        st.markdown(
            '<div class="section-header">🧠 لوحة التحليل الذكي</div>',
            unsafe_allow_html=True
        )
        if not st.session_state.get('game_over'):
            # شريط التقييم اللحظي
            try:
                raw_score = evaluate_position(board, player_color)
                pct = eval_to_pct(raw_score)
                marker_pos = max(2, min(98, int(pct)))
                if raw_score > 100:
                    score_color = "#00E676"
                elif raw_score < -100:
                    score_color = "#EF5350"
                else:
                    score_color = "#FFFFFF"
                st.markdown(
                    f'<div class="eval-container">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-family:Tajawal;font-size:0.82rem;color:#888;'
                    f'margin-bottom:4px">'
                    f'<span>🤖 AI</span>'
                    f'<span style="color:{score_color};font-weight:700">'
                    f'التقييم: {raw_score:+.0f}'
                    f'</span>'
                    f'<span>👤 أنت</span>'
                    f'</div>'
                    f'<div class="eval-bar-bg">'
                    f'<div class="eval-marker" '
                    f'style="left:{marker_pos}%"></div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass

            # معلومات المرحلة
            try:
                fen_phase = get_board_fen(board)
                wp_ph, bp_ph = parse_fen_pieces(fen_phase)
                total_ph = len(wp_ph) + len(bp_ph)
                phase_val = _game_phase(total_ph)
                phase_label = _phase_label(phase_val)
                st.markdown(
                    f'<div style="font-family:Tajawal;font-size:0.82rem;'
                    f'color:#888;direction:rtl;margin:3px 0 8px">'
                    f'🎯 {phase_label} | {total_ph} قطعة على الرقعة'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass

            # أزرار التحليل
            hint_depth = min(
                st.session_state.get('depth', 10), MAX_DEPTH
            )
            analysis_btn_col, quick_btn_col = st.columns(2)
            with analysis_btn_col:
                deep_analysis_pressed = st.button(
                    f"🧠 تحليل عبقري",
                    use_container_width=True,
                    help=f"تحليل عميق بعمق {hint_depth} مستوى",
                    key="btn_deep_analysis"
                )
            with quick_btn_col:
                quick_hint_pressed = st.button(
                    "⚡ تلميح سريع",
                    use_container_width=True,
                    help="تلميح سريع بعمق 5 مستويات",
                    key="btn_quick_hint"
                )

            if deep_analysis_pressed:
                analysis_time_limit = min(
                    st.session_state.get('time_limit', 5.0) * 2, 18.0
                )
                with st.spinner(
                    f"🔬 جاري التحليل العميق بعمق {hint_depth}... "
                    f"(قد يستغرق حتى {analysis_time_limit:.0f}ث)"
                ):
                    t_analysis_start = time.time()
                    deep_analysis = analyze_position(
                        board, player_color, ai_color,
                        depth=hint_depth, time_limit=analysis_time_limit
                    )
                    t_elapsed = time.time() - t_analysis_start
                    deep_analysis['analysis_time'] = f"{t_elapsed:.1f}ث"
                    best_mv_str = deep_analysis.get("best_move_str", "")
                    if best_mv_str:
                        st.session_state['hint_move'] = best_mv_str
                    st.session_state['analysis'] = deep_analysis
                    st.session_state['show_analysis'] = True
                    st.rerun()

            if quick_hint_pressed:
                with st.spinner("⚡ جاري حساب التلميح السريع..."):
                    t_analysis_start = time.time()
                    # استخدام analyze_position مع عمق منخفض للحصول على بيانات ديناميكية دقيقة
                    quick_analysis = analyze_position(
                        board, player_color, ai_color,
                        depth=5, time_limit=2.0
                    )
                    t_elapsed = time.time() - t_analysis_start
                    quick_analysis['analysis_time'] = f"{t_elapsed:.1f}ث"
                    
                    best_mv_str = quick_analysis.get("best_move_str", "")
                    if best_mv_str:
                        st.session_state['hint_move'] = best_mv_str
                        
                    # تمييز التحليل السريع
                    quick_analysis['top_moves'][0]['label'] = "تلميح سريع ⚡"
                    quick_analysis['threats'].append("⚡ هذا تحليل سريع بعمق 5 مستويات")
                    
                    st.session_state['analysis'] = quick_analysis
                    st.session_state['show_analysis'] = True
                    st.rerun()

            # عرض نتيجة التحليل
            if (st.session_state.get('show_analysis') and st.session_state.get('analysis') is not None):
                st.markdown(
                    '<div class="analysis-card">',
                    unsafe_allow_html=True
                )
                render_analysis_panel(st.session_state['analysis'])
                st.markdown('</div>', unsafe_allow_html=True)
                if st.button(
                    "✖ إغلاق التحليل",
                    use_container_width=True,
                    key="btn_close_analysis"
                ):
                    st.session_state['show_analysis'] = False
                    st.session_state['hint_move'] = ""
                    st.rerun()

            # نصائح عامة حسب المرحلة
            elif not st.session_state.get('show_analysis'):
                try:
                    fen_tip = get_board_fen(board)
                    wp_tip, bp_tip = parse_fen_pieces(fen_tip)
                    total_tip = len(wp_tip) + len(bp_tip)
                    phase_tip = _game_phase(total_tip)
                    if phase_tip >= 0.75:
                        tip_text = (
                            "📚 **نصيحة الافتتاح:** سيطر على مربعات المركز "
                            "وحافظ على صفك الخلفي لمنع التتويج المبكر للخصم."
                        )
                    elif phase_tip >= 0.35:
                        tip_text = (
                            "⚔️ **نصيحة وسط اللعبة:** ابحث عن الشوكات "
                            "وسلاسل الأكل المتعددة، وأنشئ ضغطاً متواصلاً."
                        )
                    else:
                        tip_text = (
                            "🎯 **نصيحة نهاية اللعبة:** الملوك أقوى بكثير، "
                            "اسعَ لتتويج قطعة وسيطر على الزوايا المزدوجة."
                        )
                    st.markdown(
                        f'<div class="hint-box">{tip_text}</div>',
                        unsafe_allow_html=True
                    )
                except Exception:
                    pass

        else:
            # ─── إحصائيات نهاية اللعبة ───
            winner_final = st.session_state.get('winner')
            if winner_final == 'player':
                result_icon = "🏆"
                result_text = "أحسنت! انتصرت على المحرك!"
                result_color = "#FFD700"
            elif winner_final == 'ai':
                result_icon = "💻"
                result_text = "المحرك فاز هذه المرة!"
                result_color = "#EF5350"
            else:
                result_icon = "🤝"
                result_text = "انتهت اللعبة بالتعادل!"
                result_color = "#64B5F6"

            total_moves_final = len(st.session_state.get('move_history', []))
            captures_w_final = st.session_state.get('captures_w', 0)
            captures_b_final = st.session_state.get('captures_b', 0)
            tt_final = get_tt_stats()

            player_icon = "⬜" if st.session_state.get('player_color') == WHITE else "⬛"
            ai_icon = "⬛" if st.session_state.get('player_color') == WHITE else "⬜"

            if st.session_state.get('player_color') == WHITE:
                player_captures = captures_w_final
                ai_captures = captures_b_final
            else:
                player_captures = captures_b_final
                ai_captures = captures_w_final

            st.markdown(
                f'<div class="game-over-stats">'
                f'<div style="text-align:center;font-family:Tajawal;'
                f'font-size:1.45rem;font-weight:900;color:{result_color};'
                f'margin-bottom:14px">'
                f'{result_icon} {result_text}'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">إجمالي الحركات</div>'
                f'<div class="analysis-value">🎯 {total_moves_final} حركة</div>'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">عمليات الأكل</div>'
                f'<div class="analysis-value">'
                f'{player_icon} اللاعب: {player_captures} &nbsp;|&nbsp; '
                f'{ai_icon} AI: {ai_captures}'
                f'</div>'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">إحصائيات المحرك</div>'
                f'<div class="analysis-value">'
                f'💾 {tt_final["size"]:,} موضع محلل<br>'
                f'📈 {tt_final["hit_rate"]} معدل الإصابة<br>'
                f'🔍 {tt_final["hits"]:,} إصابة / '
                f'{tt_final["stores"]:,} تخزين'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            if st.button(
                "🆕 لعبة جديدة",
                use_container_width=True,
                type="primary",
                key="btn_new_game_end"
            ):
                color_radio_val = st.session_state.get('color_radio', '⬜ أبيض (تبدأ أنت)')
                if "أبيض" in color_radio_val:
                    pc_end = WHITE
                    ac_end = BLACK
                else:
                    pc_end = BLACK
                    ac_end = WHITE
                init_game(pc_end, ac_end, chosen_depth, chosen_time)
                st.rerun()


# ════════════════════════════════════════════
# نقطة الدخول
# ════════════════════════════════════════════
if __name__ == "__main__":
    main()
