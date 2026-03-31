"""
لعبة الداما الكلاسيكية - واجهة Streamlit المتقدمة
====================================================
المميزات:
- فهرس تفاعلي للبرنامج
- مساعد ذكي عبقري بتحليل عميق
- إحصائيات متقدمة
- سجل حركات تفاعلي
- لوحة تحليل مباشر
- شريط تقييم لحظي
- دعم كامل للغة العربية RTL
"""
import re
import time
import streamlit as st

try:
    from draughts import Board, WHITE, BLACK
    DRAUGHTS_OK = True
except ImportError:
    DRAUGHTS_OK = False
    WHITE, BLACK = 2, 1

from engine import (
    get_legal_moves,
    get_board_fen,
    format_move_to_string,
    parse_fen_pieces,
    evaluate_position,
    find_best_move,
    analyze_position,
    _is_capture,
    _is_promotion,
    _phase_label,
    _game_phase,
    clear_transposition_table,
    get_tt_stats,
    DRAUGHTS_AVAILABLE,
    MAX_DEPTH,
)

st.set_page_config(
    page_title="داما AI | لعبة الداما الذكية",
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
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FFD700 0%, #FF8C00 50%, #FF4500 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding: 12px 0 4px;
        letter-spacing: 2px;
    }

    .sub-title {
        text-align: center;
        font-family: 'Tajawal', sans-serif;
        color: #8899AA;
        font-size: 1rem;
        margin: 0 0 8px;
        letter-spacing: 1px;
    }

    .index-container {
        background: linear-gradient(135deg, rgba(30,40,60,0.95), rgba(20,30,50,0.95));
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }

    .index-title {
        font-size: 1.3rem;
        font-weight: 900;
        color: #FFD700;
        margin-bottom: 12px;
        border-bottom: 2px solid rgba(255,215,0,0.3);
        padding-bottom: 8px;
    }

    .index-item {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        border: 1px solid transparent;
    }

    .index-item:hover {
        background: rgba(255,215,0,0.1);
        border-color: rgba(255,215,0,0.3);
    }

    .index-icon {
        font-size: 1.2rem;
        margin-left: 10px;
    }

    .index-label {
        font-size: 0.95rem;
        color: #DDD;
        font-weight: 700;
    }

    .index-desc {
        font-size: 0.75rem;
        color: #888;
        margin-right: auto;
    }

    .status-box {
        text-align: center;
        padding: 10px 16px;
        border-radius: 10px;
        font-family: 'Tajawal', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        margin: 6px 0;
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
        font-size: 1.4rem;
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
        background: linear-gradient(135deg, rgba(15,25,50,0.98), rgba(20,35,70,0.98));
        border: 2px solid rgba(0,200,100,0.4);
        border-radius: 14px;
        padding: 18px;
        margin: 10px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        box-shadow: 0 4px 20px rgba(0,200,100,0.15);
    }

    .analysis-title {
        font-size: 1.2rem;
        font-weight: 900;
        color: #00CC66;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .analysis-section {
        margin: 10px 0;
        padding: 10px;
        background: rgba(255,255,255,0.04);
        border-radius: 8px;
        border-right: 3px solid rgba(0,200,100,0.5);
    }

    .analysis-label {
        font-size: 0.8rem;
        color: #888;
        margin-bottom: 4px;
    }

    .analysis-value {
        font-size: 0.95rem;
        color: #EEE;
        font-weight: 700;
    }

    .move-card {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }

    .move-card.best {
        background: rgba(0,200,100,0.15);
        border-color: rgba(0,200,100,0.4);
    }

    .move-card.good {
        background: rgba(255,200,0,0.08);
        border-color: rgba(255,200,0,0.3);
    }

    .move-card.neutral {
        background: rgba(100,100,100,0.1);
    }

    .move-rank {
        font-size: 1.1rem;
        margin-left: 8px;
    }

    .move-str {
        font-size: 1rem;
        font-weight: 900;
        color: #FFF;
        font-family: monospace;
        min-width: 80px;
    }

    .move-label {
        font-size: 0.8rem;
        color: #AAA;
        margin-right: auto;
    }

    .eval-container {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 6px 0;
        font-family: 'Tajawal', sans-serif;
    }

    .eval-bar-bg {
        height: 12px;
        border-radius: 6px;
        background: linear-gradient(to left, #EF5350 0%, #FF8C00 30%, #888 50%, #66BB6A 70%, #00E676 100%);
        position: relative;
        margin: 6px 0;
        overflow: hidden;
    }

    .eval-marker {
        position: absolute;
        top: 0;
        width: 3px;
        height: 100%;
        background: white;
        border-radius: 2px;
        transition: left 0.5s ease;
    }

    .info-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 14px;
        margin: 8px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }

    .piece-count {
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding: 6px;
    }

    .piece-side {
        text-align: center;
    }

    .piece-num {
        font-size: 2rem;
        font-weight: 900;
    }

    .piece-sub {
        font-size: 0.78rem;
        color: #999;
    }

    .history-row {
        display: flex;
        align-items: center;
        padding: 5px 8px;
        margin: 2px 0;
        border-radius: 6px;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        font-size: 0.88rem;
    }

    .history-row:nth-child(odd) {
        background: rgba(255,255,255,0.03);
    }

    .history-row.last-move {
        background: rgba(255,215,0,0.12);
        border: 1px solid rgba(255,215,0,0.3);
        font-weight: 700;
    }

    .h-num {
        color: #666;
        width: 24px;
        flex-shrink: 0;
    }

    .h-who {
        width: 28px;
        flex-shrink: 0;
    }

    .h-move {
        color: #EEE;
        font-family: monospace;
        flex: 1;
    }

    .h-type {
        font-size: 0.75rem;
        color: #888;
    }

    .stButton > button {
        font-family: 'Tajawal', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        transition: all 0.2s !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00C853, #00E676) !important;
        color: #000 !important;
        border: none !important;
    }

    .board-wrap {
        display: flex;
        justify-content: center;
        padding: 8px 0;
    }

    .stat-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-family: 'Tajawal', sans-serif;
        margin: 2px 3px;
        font-weight: 700;
    }

    .stat-green {
        background: rgba(0,200,80,0.2);
        color: #00E676;
    }

    .stat-blue {
        background: rgba(0,150,255,0.2);
        color: #64B5F6;
    }

    .stat-orange {
        background: rgba(255,150,0,0.2);
        color: #FFB74D;
    }

    .stat-red {
        background: rgba(255,80,80,0.2);
        color: #EF9A9A;
    }

    .section-header {
        font-family: 'Tajawal', sans-serif;
        font-size: 1.1rem;
        font-weight: 900;
        color: #FFD700;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255,215,0,0.2);
        margin: 12px 0 8px;
        direction: rtl;
    }

    .welcome-feature {
        display: flex;
        align-items: flex-start;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 10px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        gap: 12px;
    }

    .welcome-feature-icon {
        font-size: 1.6rem;
        flex-shrink: 0;
    }

    .welcome-feature-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #FFD700;
        margin-bottom: 2px;
    }

    .welcome-feature-desc {
        font-size: 0.8rem;
        color: #999;
        line-height: 1.4;
    }

    .game-over-stats {
        background: linear-gradient(135deg, rgba(15,25,50,0.98), rgba(20,35,70,0.98));
        border: 2px solid rgba(255,215,0,0.3);
        border-radius: 14px;
        padding: 20px;
        margin: 10px 0;
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }

    .hint-box {
        background: rgba(0,200,100,0.08);
        border: 1px solid rgba(0,200,100,0.3);
        border-radius: 8px;
        padding: 10px 14px;
        margin: 6px 0;
        font-family: 'Tajawal', sans-serif;
        font-size: 0.9rem;
        direction: rtl;
        color: #88FFBB;
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


def count_pieces(board):
    """حساب القطع لكل جانب - يُرجع (w_men, w_kings, b_men, b_kings)"""
    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    w_men   = sum(1 for _, k in wp if not k)
    w_kings = sum(1 for _, k in wp if k)
    b_men   = sum(1 for _, k in bp if not k)
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
    """تحديد الفائز: 'player' | 'ai' | 'draw' | None"""
    if not is_game_over(board):
        return None
    wm, wk, bm, bk = count_pieces(board)
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


def eval_to_percent(score: float) -> float:
    """تحويل نقاط التقييم لنسبة مئوية (0-100) حيث 50 = تعادل"""
    clamped = max(-1000.0, min(1000.0, float(score)))
    return 50.0 + clamped * 0.05


# ════════════════════════════════════════════
# رسم الرقعة SVG
# ════════════════════════════════════════════
def _draw_arrow(svg_parts, move_str, sq_coords,
                color, marker_id, dash_attr, opacity_val):
    """رسم سهم على الرقعة لتمثيل الحركة"""
    if not move_str:
        return
    raw_nums = re.findall(r'\d+', move_str)
    valid_nums = []
    for n in raw_nums:
        try:
            num = int(n)
            if num in sq_coords:
                valid_nums.append(num)
        except ValueError:
            continue
    if len(valid_nums) < 2:
        return
    points_str = " ".join(
        f"{sq_coords[n][0]},{sq_coords[n][1]}" for n in valid_nums
    )
    svg_parts.append(
        f'<polyline points="{points_str}" fill="none" '
        f'stroke="{color}" stroke-width="6" {dash_attr} '
        f'marker-end="url(#{marker_id})" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{opacity_val}"/>'
    )


def render_board(board, last_move="", hint_move="") -> str:
    """
    رسم رقعة الداما كـ SVG كامل.
    - last_move: الحركة الأخيرة (يُرسم عليها سهم برتقالي)
    - hint_move: التلميح (يُرسم عليها سهم أخضر منقط)
    """
    CELL_SIZE   = 66
    BOARD_SIZE  = CELL_SIZE * 8
    MARGIN      = 30
    TOTAL_SIZE  = BOARD_SIZE + MARGIN * 2
    PIECE_R     = 26
    INNER_R     = 18

    COLOR_LIGHT_SQ  = "#F0D9B5"
    COLOR_DARK_SQ   = "#B58863"
    COLOR_FRAME     = "#4A2C10"
    COLOR_SQ_NUM    = "rgba(255,255,255,0.28)"
    COLOR_LAST_HL   = "rgba(255,220,50,0.32)"
    COLOR_HINT_HL   = "rgba(0,220,80,0.22)"

    fen = get_board_fen(board)
    white_pieces, black_pieces = parse_fen_pieces(fen)

    piece_map = {}
    for sq, is_king in white_pieces:
        piece_map[sq] = ('w', is_king)
    for sq, is_king in black_pieces:
        piece_map[sq] = ('b', is_king)

    highlight_last = set()
    if last_move:
        for n in re.findall(r'\d+', last_move):
            try:
                highlight_last.add(int(n))
            except ValueError:
                pass

    highlight_hint = set()
    if hint_move:
        for n in re.findall(r'\d+', hint_move):
            try:
                highlight_hint.add(int(n))
            except ValueError:
                pass

    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {TOTAL_SIZE} {TOTAL_SIZE}" width="100%" '
        f'style="max-width:{TOTAL_SIZE}px;display:block;margin:0 auto">'
    )

    svg_parts.append(
        f"""<defs>
          <filter id="piece-shadow">
            <feDropShadow dx="1" dy="2" stdDeviation="3" flood-opacity="0.6"/>
          </filter>
          <filter id="king-glow">
            <feGaussianBlur stdDeviation="3" result="blur_out"/>
            <feMerge>
              <feMergeNode in="blur_out"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <radialGradient id="white-grad" cx="38%" cy="32%" r="60%">
            <stop offset="0%"   stop-color="#FFFFFF"/>
            <stop offset="55%"  stop-color="#EDD9A3"/>
            <stop offset="100%" stop-color="#C8A050"/>
          </radialGradient>
          <radialGradient id="black-grad" cx="38%" cy="32%" r="60%">
            <stop offset="0%"   stop-color="#666666"/>
            <stop offset="55%"  stop-color="#2A2A2A"/>
            <stop offset="100%" stop-color="#0A0A0A"/>
          </radialGradient>
          <marker id="last-arrow" viewBox="0 0 10 10" refX="8" refY="5"
                  markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0 0 L10 5 L0 10z" fill="#FF4500"/>
          </marker>
          <marker id="hint-arrow" viewBox="0 0 10 10" refX="8" refY="5"
                  markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0 0 L10 5 L0 10z" fill="#00DD55"/>
          </marker>
        </defs>"""
    )

    svg_parts.append(
        f'<rect x="0" y="0" width="{TOTAL_SIZE}" height="{TOTAL_SIZE}" '
        f'rx="10" fill="{COLOR_FRAME}"/>'
    )
    svg_parts.append(
        f'<rect x="{MARGIN - 5}" y="{MARGIN - 5}" '
        f'width="{BOARD_SIZE + 10}" height="{BOARD_SIZE + 10}" '
        f'rx="5" fill="#2D1A08" stroke="#7A5028" stroke-width="1.5"/>'
    )

    for col_idx in range(8):
        cx = MARGIN + col_idx * CELL_SIZE + CELL_SIZE // 2
        svg_parts.append(
            f'<text x="{cx}" y="{MARGIN - 10}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{chr(65 + col_idx)}</text>'
        )
    for row_idx in range(8):
        cy = MARGIN + row_idx * CELL_SIZE + CELL_SIZE // 2 + 5
        svg_parts.append(
            f'<text x="{MARGIN - 14}" y="{cy}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{8 - row_idx}</text>'
        )

    sq_number = 0
    sq_coords = {}

    for row in range(8):
        for col in range(8):
            x_pos = MARGIN + col * CELL_SIZE
            y_pos = MARGIN + row * CELL_SIZE
            is_dark_square = (row + col) % 2 == 1
            sq_fill = COLOR_DARK_SQ if is_dark_square else COLOR_LIGHT_SQ

            svg_parts.append(
                f'<rect x="{x_pos}" y="{y_pos}" '
                f'width="{CELL_SIZE}" height="{CELL_SIZE}" fill="{sq_fill}"/>'
            )

            if is_dark_square:
                sq_number += 1
                center_x = x_pos + CELL_SIZE // 2
                center_y = y_pos + CELL_SIZE // 2
                sq_coords[sq_number] = (center_x, center_y)

                if sq_number in highlight_last:
                    svg_parts.append(
                        f'<rect x="{x_pos}" y="{y_pos}" '
                        f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                        f'fill="{COLOR_LAST_HL}"/>'
                    )

                if sq_number in highlight_hint:
                    svg_parts.append(
                        f'<rect x="{x_pos}" y="{y_pos}" '
                        f'width="{CELL_SIZE}" height="{CELL_SIZE}" '
                        f'fill="{COLOR_HINT_HL}"/>'
                    )

                svg_parts.append(
                    f'<text x="{x_pos + 4}" y="{y_pos + 14}" '
                    f'font-size="10" fill="{COLOR_SQ_NUM}" '
                    f'font-family="monospace">{sq_number}</text>'
                )

                if sq_number in piece_map:
                    piece_color, is_king = piece_map[sq_number]
                    gradient_id   = "url(#white-grad)" if piece_color == 'w' else "url(#black-grad)"
                    stroke_color  = "#BFA070" if piece_color == 'w' else "#111111"
                    inner_color   = "#D4B896" if piece_color == 'w' else "#2A2A2A"

                    svg_parts.append(
                        f'<circle cx="{center_x + 1}" cy="{center_y + 3}" '
                        f'r="{PIECE_R}" fill="rgba(0,0,0,0.4)"/>'
                    )
                    svg_parts.append(
                        f'<circle cx="{center_x}" cy="{center_y}" '
                        f'r="{PIECE_R}" fill="{gradient_id}" '
                        f'stroke="{stroke_color}" stroke-width="2.5" '
                        f'filter="url(#piece-shadow)"/>'
                    )
                    svg_parts.append(
                        f'<circle cx="{center_x}" cy="{center_y}" '
                        f'r="{INNER_R}" fill="none" stroke="{inner_color}" '
                        f'stroke-width="1.5" opacity="0.5"/>'
                    )

                    if is_king:
                        crown_color = "#DAA520" if piece_color == 'w' else "#FFD700"
                        svg_parts.append(
                            f'<text x="{center_x}" y="{center_y + 8}" '
                            f'text-anchor="middle" font-size="24" '
                            f'fill="{crown_color}" font-weight="bold" '
                            f'filter="url(#king-glow)">♛</text>'
                        )

    svg_parts.append(
        f'<rect x="{MARGIN}" y="{MARGIN}" width="{BOARD_SIZE}" '
        f'height="{BOARD_SIZE}" fill="none" stroke="{COLOR_FRAME}" '
        f'stroke-width="2"/>'
    )

    _draw_arrow(
        svg_parts, last_move, sq_coords,
        "#FF4500", "last-arrow", "", "0.82"
    )
    _draw_arrow(
        svg_parts, hint_move, sq_coords,
        "#00DD55", "hint-arrow", 'stroke-dasharray="10,6"', "0.92"
    )

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


# ════════════════════════════════════════════
# فهرس البرنامج
# ════════════════════════════════════════════
def render_index():
    """عرض فهرس تفاعلي كامل لأقسام البرنامج"""
    st.markdown("""
    <div class="index-container">
        <div class="index-title">📋 فهرس البرنامج</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;direction:rtl">

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
                    <div class="index-desc">Minimax + Alpha-Beta | عمق 20</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">💡</span>
                <span>
                    <div class="index-label">المساعد الذكي</div>
                    <div class="index-desc">تحليل عميق + نصائح استراتيجية</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">📊</span>
                <span>
                    <div class="index-label">الإحصائيات</div>
                    <div class="index-desc">TT | History | Killers | LMR</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">📜</span>
                <span>
                    <div class="index-label">سجل الحركات</div>
                    <div class="index-desc">كامل مع أنواع الحركات</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">⚙️</span>
                <span>
                    <div class="index-label">الإعدادات</div>
                    <div class="index-desc">صعوبة | لون | وقت التفكير</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">📚</span>
                <span>
                    <div class="index-label">كتاب الافتتاحيات</div>
                    <div class="index-desc">حركات مدروسة مسبقاً</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">🔬</span>
                <span>
                    <div class="index-label">لوحة التحليل</div>
                    <div class="index-desc">تقييم لحظي + أفضل 3 حركات</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">⚔️</span>
                <span>
                    <div class="index-label">Quiescence Search</div>
                    <div class="index-desc">متابعة الأكل حتى الاستقرار</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">🔀</span>
                <span>
                    <div class="index-label">Zobrist Hashing</div>
                    <div class="index-desc">هاش سريع 64-bit للمواقف</div>
                </span>
            </div>

        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# لوحة التحليل الذكي
# ════════════════════════════════════════════
def render_analysis_panel(analysis: dict):
    """عرض نتائج التحليل العميق بشكل منسق"""
    if not analysis or "error" in analysis:
        error_msg = analysis.get("error", "خطأ غير معروف") if analysis else "لا يوجد تحليل"
        st.error(f"❌ {error_msg}")
        return

    st.markdown(
        '<div class="analysis-title">🧠 تحليل المحرك العبقري</div>',
        unsafe_allow_html=True
    )

    col_adv, col_phase = st.columns(2)
    with col_adv:
        advantage_text = analysis.get('advantage', 'غير متاح')
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">التفوق الحالي</div>'
            f'<div class="analysis-value">{advantage_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col_phase:
        phase_text = analysis.get('phase', 'غير متاح')
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">مرحلة اللعبة</div>'
            f'<div class="analysis-value">🎯 {phase_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    recommendation = analysis.get('recommendation', '')
    if recommendation:
        recommendation_html = recommendation.replace('\n', '<br>')
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">💬 توصية المحرك</div>'
            f'<div class="analysis-value" style="line-height:1.7">'
            f'{recommendation_html}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    top_moves = analysis.get('top_moves', [])
    if top_moves:
        st.markdown(
            '<div class="analysis-label" style="margin-top:10px">'
            '🏆 أفضل الحركات:'
            '</div>',
            unsafe_allow_html=True
        )
        rank_icons  = ["🥇", "🥈", "🥉"]
        card_styles = ["best", "good", "neutral"]
        for idx, mv_data in enumerate(top_moves):
            icon      = rank_icons[idx] if idx < len(rank_icons) else "▪️"
            card_cls  = card_styles[idx] if idx < len(card_styles) else "neutral"
            mv_str    = mv_data.get('move', '?')
            mv_label  = mv_data.get('label', '')
            mv_score  = mv_data.get('score', 0)
            st.markdown(
                f'<div class="move-card {card_cls}">'
                f'<span class="move-rank">{icon}</span>'
                f'<span class="move-str">{mv_str}</span>'
                f'<span class="move-label">{mv_label} | {mv_score:+.0f}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    threats = analysis.get('threats', [])
    if threats:
        st.markdown(
            '<div class="analysis-label" style="margin-top:10px">'
            '⚠️ التهديدات والملاحظات:'
            '</div>',
            unsafe_allow_html=True
        )
        for threat_text in threats:
            st.markdown(
                f'<div style="font-family:Tajawal;font-size:0.88rem;'
                f'color:#CCC;padding:3px 0;direction:rtl">'
                f'{threat_text}</div>',
                unsafe_allow_html=True
            )

    reached = analysis.get('reached_depth', 0)
    analysis_time = analysis.get('analysis_time', '')
    time_text = f" | ⏱ {analysis_time}" if analysis_time else ""
    st.markdown(
        f'<div style="margin-top:10px;font-family:Tajawal;font-size:0.8rem;'
        f'color:#666;direction:rtl">'
        f'🔬 عمق البحث المحقق: <b style="color:#888">{reached}</b>'
        f'{time_text}</div>',
        unsafe_allow_html=True
    )


# ════════════════════════════════════════════
# إدارة حالة اللعبة
# ════════════════════════════════════════════
def init_game(player_color, ai_color, depth, time_limit):
    """تهيئة لعبة جديدة وإعادة ضبط كل المتغيرات"""
    clear_transposition_table()
    board = Board(variant="english")
    st.session_state['board']          = board
    st.session_state['player_color']   = player_color
    st.session_state['ai_color']       = ai_color
    st.session_state['depth']          = depth
    st.session_state['time_limit']     = time_limit
    st.session_state['move_history']   = []
    st.session_state['game_over']      = False
    st.session_state['winner']         = None
    st.session_state['last_move']      = ""
    st.session_state['hint_move']      = ""
    st.session_state['ai_info']        = ""
    st.session_state['game_started']   = True
    st.session_state['pending_ai']     = (board.turn == ai_color)
    st.session_state['celebrated']     = False
    st.session_state['analysis']       = None
    st.session_state['show_analysis']  = False
    st.session_state['move_count']     = 0
    st.session_state['captures_w']     = 0
    st.session_state['captures_b']     = 0


def play_human_move():
    """تنفيذ الحركة المختارة من اللاعب البشري"""
    if st.session_state.get('game_over'):
        return

    board       = st.session_state['board']
    legal_moves = get_legal_moves(board)
    move_index  = st.session_state.get("move_select", 0)

    if not (0 <= move_index < len(legal_moves)):
        st.warning("⚠️ اختر حركة صحيحة من القائمة")
        return

    chosen_move = legal_moves[move_index]
    move_str    = fmt(chosen_move)
    is_cap      = _is_capture(chosen_move)
    is_prom     = _is_promotion(chosen_move)

    board.push(chosen_move)

    if is_cap:
        move_type = "⚔️"
    elif is_prom:
        move_type = "👑"
    else:
        move_type = "➡️"

    st.session_state['move_history'].append(("👤", move_str, move_type))
    st.session_state['last_move']      = move_str
    st.session_state['hint_move']      = ""
    st.session_state['analysis']       = None
    st.session_state['show_analysis']  = False
    st.session_state['move_count']     = st.session_state.get('move_count', 0) + 1

    if is_cap:
        st.session_state['captures_w'] = st.session_state.get('captures_w', 0) + 1

    if is_game_over(board):
        st.session_state['game_over'] = True
        st.session_state['winner']    = get_winner(
            board,
            st.session_state['player_color'],
            st.session_state['ai_color']
        )
    else:
        st.session_state['pending_ai'] = True


def play_ai_move():
    """تنفيذ حركة الذكاء الاصطناعي"""
    board      = st.session_state['board']
    ai_color   = st.session_state['ai_color']
    depth      = st.session_state['depth']
    time_limit = st.session_state.get('time_limit', 5.0)

    best_move, score, reached_depth = find_best_move(
        board,
        ai_color,
        max_depth=depth,
        time_limit=time_limit
    )

    if best_move is not None:
        move_str  = fmt(best_move)
        is_cap    = _is_capture(best_move)
        is_prom   = _is_promotion(best_move)

        board.push(best_move)

        if is_cap:
            move_type = "⚔️"
        elif is_prom:
            move_type = "👑"
        else:
            move_type = "➡️"

        st.session_state['move_history'].append(("🤖", move_str, move_type))
        st.session_state['last_move']  = move_str
        st.session_state['hint_move']  = ""
        st.session_state['analysis']   = None
        st.session_state['move_count'] = st.session_state.get('move_count', 0) + 1

        if is_cap:
            st.session_state['captures_b'] = st.session_state.get('captures_b', 0) + 1

        tt_stats = get_tt_stats()
        st.session_state['ai_info'] = (
            f"عمق: **{reached_depth}** | "
            f"تقييم: **{score:+.0f}** | "
            f"جدول: **{tt_stats['size']:,}** إدخال"
        )

        if is_game_over(board):
            st.session_state['game_over'] = True
            st.session_state['winner']    = get_winner(
                board,
                st.session_state['player_color'],
                ai_color
            )
        else:
            st.session_state['pending_ai'] = False
    else:
        st.session_state['game_over']   = True
        st.session_state['winner']      = 'player'
        st.session_state['pending_ai']  = False


def undo_move():
    """
    التراجع عن آخر حركتين (اللاعب + AI).
    يُعيد بناء الرقعة من الصفر باستخدام السجل المتبقي.
    """
    history = st.session_state.get('move_history', [])
    if not history:
        return

    moves_to_remove = min(2, len(history))
    remaining_history = history[:-moves_to_remove]

    new_board = Board(variant="english")
    for _, mv_str, _ in remaining_history:
        legal_in_sim = get_legal_moves(new_board)
        matched = None
        for lm in legal_in_sim:
            if fmt(lm) == mv_str or str(lm) == mv_str:
                matched = lm
                break
        if matched is not None:
            new_board.push(matched)

    last_move_str = remaining_history[-1][1] if remaining_history else ""

    st.session_state['board']         = new_board
    st.session_state['move_history']  = remaining_history
    st.session_state['game_over']     = False
    st.session_state['winner']        = None
    st.session_state['last_move']     = last_move_str
    st.session_state['hint_move']     = ""
    st.session_state['pending_ai']    = False
    st.session_state['celebrated']    = False
    st.session_state['analysis']      = None
    st.session_state['show_analysis'] = False


# ════════════════════════════════════════════
# الواجهة الرئيسية
# ════════════════════════════════════════════
def main():
    inject_css()

    # ─── فحص المكتبة ───
    if not DRAUGHTS_OK or not DRAUGHTS_AVAILABLE:
        st.error("❌ مكتبة `pydraughts` غير مثبتة!")
        st.info("قم بتثبيتها بتنفيذ الأمر التالي:")
        st.code("pip install pydraughts", language="bash")
        st.markdown(
            "بعد التثبيت أعد تشغيل التطبيق.",
            unsafe_allow_html=False
        )
        st.stop()

    # ════════════════════════════════════════
    # الشريط الجانبي
    # ════════════════════════════════════════
    with st.sidebar:
        st.markdown(
            '<div style="text-align:center;font-family:Tajawal;'
            'font-size:1.5rem;font-weight:900;color:#FFD700;'
            'padding:10px 0 4px">♟️ داما AI</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="text-align:center;font-family:Tajawal;'
            'font-size:0.8rem;color:#666;padding-bottom:8px">'
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
            key="color_choice_radio"
        )

        difficulty = st.select_slider(
            "🎯 مستوى الصعوبة",
            options=["مبتدئ", "سهل", "متوسط", "صعب", "خبير", "عبقري"],
            value="متوسط",
            key="difficulty_slider"
        )

        depth_map = {
            "مبتدئ": 2,
            "سهل":   3,
            "متوسط": 5,
            "صعب":   8,
            "خبير":  12,
            "عبقري": 20,
        }
        time_map = {
            "مبتدئ": 1.0,
            "سهل":   2.0,
            "متوسط": 4.0,
            "صعب":   6.0,
            "خبير":  10.0,
            "عبقري": 15.0,
        }

        chosen_depth      = depth_map[difficulty]
        chosen_time_limit = time_map[difficulty]

        st.markdown(
            f'<div style="font-family:Tajawal;font-size:0.82rem;'
            f'color:#777;direction:rtl;margin-top:-6px;margin-bottom:4px">'
            f'عمق البحث: {chosen_depth} | وقت التفكير: {chosen_time_limit:.0f}ث</div>',
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
            undo_disabled = not (
                st.session_state.get("game_started") and history_len > 0
            )
            undo_pressed = st.button(
                "↩️ تراجع",
                use_container_width=True,
                disabled=undo_disabled,
                key="btn_undo"
            )

        if new_game_pressed:
            if "أبيض" in color_choice:
                player_c = WHITE
                ai_c     = BLACK
            else:
                player_c = BLACK
                ai_c     = WHITE
            init_game(player_c, ai_c, chosen_depth, chosen_time_limit)
            st.rerun()

        if undo_pressed and st.session_state.get("game_started"):
            undo_move()
            st.rerun()

        # ─── إحصائيات اللعبة في الشريط الجانبي ───
        if st.session_state.get("game_started"):
            st.markdown("---")
            st.markdown(
                '<div class="section-header">📊 إحصائيات</div>',
                unsafe_allow_html=True
            )

            board = st.session_state['board']
            wm, wk, bm, bk = count_pieces(board)
            wt = wm + wk
            bt = bm + bk

            st.markdown(
                f'<div class="info-card">'
                f'<div class="piece-count">'
                f'<div class="piece-side">'
                f'<div style="font-size:1.3rem">⬜</div>'
                f'<div class="piece-num">{wt}</div>'
                f'<div class="piece-sub">{wm} رجل {'  ' if wm else ""}{wk}{"👑" if wk else ""}</div>'
                f'</div>'
                f'<div style="font-size:1.3rem;color:#555">⚔️</div>'
                f'<div class="piece-side">'
                f'<div style="font-size:1.3rem">⬛</div>'
                f'<div class="piece-num">{bt}</div>'
                f'<div class="piece-sub">{bm} رجل {"  " if bm else ""}{bk}{"👑" if bk else ""}</div>'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            tt_stats = get_tt_stats()
            move_count = st.session_state.get('move_count', 0)

            st.markdown(
                f'<div style="direction:rtl;font-family:Tajawal;margin:6px 0">'
                f'<span class="stat-pill stat-green">🎯 {move_count} حركة</span>'
                f'<span class="stat-pill stat-blue">💾 {tt_stats["size"]:,} TT</span>'
                f'<span class="stat-pill stat-orange">📈 {tt_stats["hit_rate"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            ai_info = st.session_state.get('ai_info', '')
            if ai_info:
                st.markdown(
                    f'<div class="info-card" style="font-size:0.85rem;'
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
                with st.container(height=240):
                    for move_idx, move_item in enumerate(move_history, 1):
                        who_icon  = move_item[0]
                        mv_str    = move_item[1]
                        mv_type   = move_item[2] if len(move_item) > 2 else "➡️"
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
        'Minimax | Alpha-Beta | Transposition Table | LMR | Quiescence Search | عمق حتى 20'
        '</div>',
        unsafe_allow_html=True
    )

    # ─── شاشة الترحيب (قبل بدء اللعبة) ───
    if not st.session_state.get("game_started"):
        st.markdown("---")

        render_index()

        st.markdown(
            '<div style="font-family:Tajawal;font-size:1.1rem;'
            'font-weight:700;color:#FFD700;text-align:center;'
            'margin:16px 0 10px;direction:rtl">'
            '✨ مميزات البرنامج'
            '</div>',
            unsafe_allow_html=True
        )

        feat_col1, feat_col2 = st.columns(2)
        with feat_col1:
            st.markdown("""
            <div class="welcome-feature">
                <span class="welcome-feature-icon">🧠</span>
                <div>
                    <div class="welcome-feature-title">ذكاء اصطناعي متقدم</div>
                    <div class="welcome-feature-desc">
                        محرك Minimax مع Alpha-Beta Pruning
                        وعمق بحث يصل لـ 20 مستوى
                    </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="welcome-feature-icon">⚡</span>
                <div>
                    <div class="welcome-feature-title">بحث فائق السرعة</div>
                    <div class="welcome-feature-desc">
                        Transposition Table مع Zobrist Hashing
                        و Late Move Reduction
                    </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="welcome-feature-icon">📚</span>
                <div>
                    <div class="welcome-feature-title">كتاب الافتتاحيات</div>
                    <div class="welcome-feature-desc">
                        حركات افتتاحية مدروسة مسبقاً
                        لبداية لعبة قوية
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with feat_col2:
            st.markdown("""
            <div class="welcome-feature">
                <span class="welcome-feature-icon">💡</span>
                <div>
                    <div class="welcome-feature-title">مساعد ذكي عبقري</div>
                    <div class="welcome-feature-desc">
                        تحليل عميق للموقف مع أفضل 3 حركات
                        ونصائح استراتيجية باللغة العربية
                    </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="welcome-feature-icon">🎯</span>
                <div>
                    <div class="welcome-feature-title">Quiescence Search</div>
                    <div class="welcome-feature-desc">
                        متابعة حركات الأكل حتى الاستقرار
                        لتجنب أفق البحث
                    </div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="welcome-feature-icon">📊</span>
                <div>
                    <div class="welcome-feature-title">إحصائيات مباشرة</div>
                    <div class="welcome-feature-desc">
                        شريط تقييم لحظي وإحصائيات
                        المحرك التفصيلية
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.info(
            "👈 اضغط **'🆕 لعبة جديدة'** في الشريط الجانبي لبدء اللعب",
            icon="🎮"
        )

        demo_board = Board(variant="english")
        st.markdown(
            f'<div class="board-wrap">{render_board(demo_board)}</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # ─── تنفيذ حركة AI إذا كان دوره ───
    if st.session_state.get('pending_ai') and not st.session_state.get('game_over'):
        with st.spinner("🤖 المحرك يحسب أفضل حركة..."):
            play_ai_move()
        st.rerun()

    board        = st.session_state['board']
    player_color = st.session_state['player_color']
    ai_color     = st.session_state['ai_color']

    # ─── تخطيط ثنائي: رقعة | لوحة تحليل ───
    col_board, col_analysis = st.columns([1.1, 0.9])

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
                available_moves_count = len(get_legal_moves(board))
                st.markdown(
                    f'<div class="status-box status-player">'
                    f'👤 دورك الآن | {available_moves_count} حركة متاحة'
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

        # الرقعة
        board_svg = render_board(
            board,
            st.session_state.get('last_move', ''),
            st.session_state.get('hint_move', '')
        )
        st.markdown(
            f'<div class="board-wrap">{board_svg}</div>',
            unsafe_allow_html=True
        )

        # ─── أدوات اللاعب (فقط في دوره) ───
        if not st.session_state.get('game_over') and board.turn == player_color:
            legal_moves = get_legal_moves(board)
            if legal_moves:
                move_labels = []
                for mv in legal_moves:
                    label = fmt(mv)
                    if _is_capture(mv):
                        label += "  ⚔️"
                    elif _is_promotion(mv):
                        label += "  👑"
                    move_labels.append(label)

                st.selectbox(
                    "🎯 اختر حركتك:",
                    range(len(move_labels)),
                    format_func=lambda i: f"[{i + 1}] {move_labels[i]}",
                    key="move_select"
                )

                action_col1, action_col2, action_col3 = st.columns(3)

                with action_col1:
                    if st.button(
                        "▶️ العب!",
                        use_container_width=True,
                        type="primary",
                        key="btn_play_move"
                    ):
                        play_human_move()
                        st.rerun()

                with action_col2:
                    if st.button(
                        "↩️ تراجع",
                        use_container_width=True,
                        key="btn_undo_inline",
                        disabled=(len(st.session_state.get('move_history', [])) == 0)
                    ):
                        undo_move()
                        st.rerun()

                with action_col3:
                    if st.button(
                        "🔄 تحديث",
                        use_container_width=True,
                        key="btn_refresh"
                    ):
                        st.rerun()

                # عرض التلميح النصي إن وُجد
                hint_mv = st.session_state.get('hint_move', '')
                if hint_mv:
                    st.markdown(
                        f'<div class="hint-box">'
                        f'💡 <b>التلميح المقترح:</b> {hint_mv}'
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

            # ─── شريط التقييم اللحظي ───
            try:
                raw_score = evaluate_position(board, player_color)
                pct       = eval_to_percent(raw_score)
                marker_pos = max(2, min(98, int(pct)))

                score_color = "#00E676" if raw_score > 50 else (
                    "#EF5350" if raw_score < -50 else "#FFFFFF"
                )
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
                    f'<div class="eval-marker" style="left:{marker_pos}%"></div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass

            # ─── معلومات المرحلة ───
            try:
                fen_for_phase = get_board_fen(board)
                wp_ph, bp_ph  = parse_fen_pieces(fen_for_phase)
                total_ph      = len(wp_ph) + len(bp_ph)
                phase_val     = _game_phase(total_ph)
                phase_lbl     = _phase_label(phase_val)
                st.markdown(
                    f'<div style="font-family:Tajawal;font-size:0.82rem;'
                    f'color:#888;direction:rtl;margin:4px 0 8px">'
                    f'🎯 مرحلة اللعبة: <b style="color:#CCC">{phase_lbl}</b> '
                    f'| القطع: <b style="color:#CCC">{total_ph}</b>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass

            # ─── أزرار التحليل ───
            hint_depth = min(st.session_state.get('depth', 8), MAX_DEPTH)

            analysis_btn_col, quick_btn_col = st.columns(2)

            with analysis_btn_col:
                analysis_btn_pressed = st.button(
                    "🧠 تحليل عبقري",
                    use_container_width=True,
                    help=f"تحليل معمق بعمق {hint_depth} مستوى - قد يستغرق بعض الوقت",
                    key="btn_deep_analysis"
                )

            with quick_btn_col:
                quick_hint_pressed = st.button(
                    "💡 تلميح سريع",
                    use_container_width=True,
                    help="تلميح سريع بعمق 4 مستويات",
                    key="btn_quick_hint"
                )

            if analysis_btn_pressed:
                analysis_time_limit = min(
                    st.session_state.get('time_limit', 5.0) * 2,
                    15.0
                )
                with st.spinner(
                    f"🔬 جاري التحليل العميق بعمق {hint_depth} مستوى... "
                    f"(قد يستغرق {analysis_time_limit:.0f} ثانية)"
                ):
                    t_start  = time.time()
                    analysis = analyze_position(
                        board,
                        player_color,
                        ai_color,
                        depth=hint_depth,
                        time_limit=analysis_time_limit
                    )
                    t_elapsed = time.time() - t_start
                    analysis['analysis_time'] = f"{t_elapsed:.1f}ث"

                    if "best_move_str" in analysis and analysis["best_move_str"]:
                        st.session_state['hint_move'] = analysis["best_move_str"]

                    st.session_state['analysis']      = analysis
                    st.session_state['show_analysis'] = True
                st.rerun()

            if quick_hint_pressed:
                with st.spinner("⚡ جاري حساب التلميح السريع..."):
                    hint_move_result, _, _ = find_best_move(
                        board,
                        player_color,
                        max_depth=4,
                        time_limit=1.5
                    )
                    if hint_move_result is not None:
                        hint_str = fmt(hint_move_result)
                        st.session_state['hint_move'] = hint_str

                        quick_analysis = {
                            "best_move":      hint_move_result,
                            "best_move_str":  hint_str,
                            "score":          0,
                            "reached_depth":  4,
                            "top_moves": [{
                                "move":  hint_str,
                                "score": 0,
                                "label": "تلميح سريع ⚡",
                            }],
                            "threats":        ["⚡ تحليل سريع بعمق 4"],
                            "phase":          "—",
                            "advantage":      "—",
                            "recommendation": f"💡 **التلميح السريع: {hint_str}**",
                            "analysis_time":  "سريع",
                        }
                        st.session_state['analysis']      = quick_analysis
                        st.session_state['show_analysis'] = True
                st.rerun()

            # ─── عرض نتيجة التحليل ───
            if (st.session_state.get('show_analysis') and
                    st.session_state.get('analysis') is not None):

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
                    st.session_state['hint_move']     = ""
                    st.rerun()

            # ─── نصائح عامة حسب المرحلة ───
            if not st.session_state.get('show_analysis'):
                try:
                    fen_tips  = get_board_fen(board)
                    wp_t, bp_t = parse_fen_pieces(fen_tips)
                    total_t   = len(wp_t) + len(bp_t)
                    phase_t   = _game_phase(total_t)

                    if phase_t >= 0.8:
                        tip_text = (
                            "📚 **نصيحة الافتتاح:** سيطر على مربعات المركز "
                            "وحافظ على صفك الخلفي لمنع التتويج المبكر للخصم."
                        )
                    elif phase_t >= 0.4:
                        tip_text = (
                            "⚔️ **نصيحة وسط اللعبة:** ابحث عن سلاسل الأكل "
                            "المتعددة وحاول إنشاء ضغط متواصل على الجانبين."
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

            total_moves = len(st.session_state.get('move_history', []))
            captures_w  = st.session_state.get('captures_w', 0)
            captures_b  = st.session_state.get('captures_b', 0)
            tt_final    = get_tt_stats()

            st.markdown(
                f'<div class="game-over-stats">'
                f'<div style="text-align:center;font-family:Tajawal;'
                f'font-size:1.5rem;font-weight:900;color:{result_color};'
                f'margin-bottom:14px">{result_icon} {result_text}</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">إجمالي الحركات</div>'
                f'<div class="analysis-value">🎯 {total_moves} حركة</div>'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">عمليات الأكل</div>'
                f'<div class="analysis-value">'
                f'⬜ اللاعب: {captures_w} &nbsp;|&nbsp; ⬛ AI: {captures_b}'
                f'</div>'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">إحصائيات المحرك</div>'
                f'<div class="analysis-value">'
                f'💾 {tt_final["size"]:,} موضع في الجدول<br>'
                f'📈 {tt_final["hit_rate"]} معدل الإصابة<br>'
                f'🔍 {tt_final["hits"]:,} إصابة من {tt_final["stores"]:,} تخزين'
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
                if "أبيض" in st.session_state.get('color_choice_radio', 'أبيض'):
                    pc_end = WHITE
                    ac_end = BLACK
                else:
                    pc_end = BLACK
                    ac_end = WHITE
                init_game(pc_end, ac_end, chosen_depth, chosen_time_limit)
                st.rerun()


# ════════════════════════════════════════════
# نقطة الدخول
# ════════════════════════════════════════════
if __name__ == "__main__":
    main()
