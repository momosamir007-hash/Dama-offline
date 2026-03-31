"""
لعبة الداما الكلاسيكية - واجهة Streamlit المتقدمة
====================================================
المميزات:
- فهرس تفاعلي للبرنامج
- مساعد ذكي عبقري بتحليل عميق
- إحصائيات متقدمة
- سجل حركات تفاعلي
- لوحة تحليل مباشر
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
    find_best_move,
    evaluate_position,
    analyze_position,
    parse_fen_pieces,
    DRAUGHTS_AVAILABLE,
    get_legal_moves,
    get_board_fen,
    format_move_to_string,
    clear_transposition_table,
    get_tt_stats,
    _is_capture,
    _is_promotion,
    _phase_label,
    _game_phase,
    MAX_DEPTH,
)

st.set_page_config(
    page_title="داما AI | لعبة الداما الذكية",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ════════════════════════════════════════════
# الـ CSS الكامل
# ════════════════════════════════════════════
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700;900&display=swap');

    /* ═══ الكلاسات العامة ═══ */
    html, body, [class*="css"] { direction: rtl; }

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
        text-shadow: none;
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

    /* ═══ فهرس البرنامج ═══ */
    .index-container {
        background: linear-gradient(135deg,
            rgba(30,40,60,0.95), rgba(20,30,50,0.95));
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
        cursor: pointer;
        transition: all 0.2s;
        border: 1px solid transparent;
        text-decoration: none;
    }
    .index-item:hover {
        background: rgba(255,215,0,0.1);
        border-color: rgba(255,215,0,0.3);
    }
    .index-icon { font-size: 1.2rem; margin-left: 10px; }
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

    /* ═══ لوحة الحالة ═══ */
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
        background: linear-gradient(135deg,#1B5E20,#2E7D32);
        color:#FFF; border:2px solid #4CAF50;
    }
    .status-ai {
        background: linear-gradient(135deg,#B71C1C,#C62828);
        color:#FFF; border:2px solid #EF5350;
    }
    .status-win {
        background: linear-gradient(135deg,#F9A825,#FFD54F);
        color:#1A1A1A; border:2px solid #FFD700;
        font-size:1.4rem; animation: pulse 1s infinite;
    }
    .status-lose {
        background: linear-gradient(135deg,#37474F,#546E7A);
        color:#FFF; border:2px solid #78909C;
    }
    .status-draw {
        background: linear-gradient(135deg,#0D47A1,#1565C0);
        color:#FFF; border:2px solid #42A5F5;
    }
    @keyframes pulse {
        0%,100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }

    /* ═══ بطاقة التحليل الذكي ═══ */
    .analysis-card {
        background: linear-gradient(135deg,
            rgba(15,25,50,0.98), rgba(20,35,70,0.98));
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

    /* ═══ أفضل الحركات ═══ */
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
    .move-rank { font-size: 1.1rem; margin-left: 8px; }
    .move-str {
        font-size: 1rem;
        font-weight: 900;
        color: #FFF;
        font-family: monospace;
        min-width: 80px;
    }
    .move-label { font-size: 0.8rem; color: #AAA; margin-right: auto; }

    /* ═══ شريط التقييم ═══ */
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
        background: linear-gradient(to left,
            #EF5350 0%, #FF8C00 30%, #888 50%, #66BB6A 70%, #00E676 100%);
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

    /* ═══ بطاقة المعلومات ═══ */
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
    .piece-side { text-align: center; }
    .piece-num { font-size: 2rem; font-weight: 900; }
    .piece-sub { font-size: 0.78rem; color: #999; }

    /* ═══ سجل الحركات ═══ */
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
    .h-num { color: #666; width: 24px; flex-shrink: 0; }
    .h-who { width: 28px; flex-shrink: 0; }
    .h-move { color: #EEE; font-family: monospace; flex: 1; }
    .h-type { font-size: 0.75rem; color: #888; }

    /* ═══ الأزرار ═══ */
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
        background: linear-gradient(135deg,#00C853,#00E676) !important;
        color: #000 !important;
        border: none !important;
    }

    /* ═══ الرقعة ═══ */
    .board-wrap {
        display: flex;
        justify-content: center;
        padding: 8px 0;
    }

    /* ═══ إحصائيات AI ═══ */
    .stat-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-family: 'Tajawal', sans-serif;
        margin: 2px 3px;
        font-weight: 700;
    }
    .stat-green { background:rgba(0,200,80,0.2); color:#00E676; }
    .stat-blue  { background:rgba(0,150,255,0.2); color:#64B5F6; }
    .stat-orange{ background:rgba(255,150,0,0.2); color:#FFB74D; }
    .stat-red   { background:rgba(255,80,80,0.2); color:#EF9A9A; }

    /* ═══ قسم الفهرس ═══ */
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
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# دوال مساعدة
# ════════════════════════════════════════════
def fmt(move) -> str:
    r = format_move_to_string(move)
    return r if r and r != "?" else "?"


def count_pieces(board):
    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    wm = sum(1 for _, k in wp if not k)
    wk = sum(1 for _, k in wp if k)
    bm = sum(1 for _, k in bp if not k)
    bk = sum(1 for _, k in bp if k)
    return wm, wk, bm, bk


def is_game_over(board) -> bool:
    try:
        if hasattr(board, 'is_over') and board.is_over():
            return True
    except Exception:
        pass
    return len(get_legal_moves(board)) == 0


def get_winner(board, player_color, ai_color):
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
    return 'player' if board.turn == ai_color else 'ai'


def eval_pct(score: float) -> float:
    """تحويل النقاط لنسبة مئوية (0-100)"""
    clamped = max(-1000, min(1000, score))
    return 50 + clamped * 0.05


# ════════════════════════════════════════════
# رسم الرقعة SVG
# ════════════════════════════════════════════
def _arrow(parts, mv_str, coords, color, marker, dash, opacity):
    if not mv_str:
        return
    nums = [int(n) for n in re.findall(r'\d+', mv_str) if int(n) in coords]
    if len(nums) < 2:
        return
    pts = " ".join(f"{coords[n][0]},{coords[n][1]}" for n in nums)
    parts.append(
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{color}" stroke-width="6" {dash} '
        f'marker-end="url(#{marker})" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{opacity}"/>'
    )


def render_board(board, last_move="", hint_move="", selected_sq=None) -> str:
    CELL = 66
    BSZ  = CELL * 8
    MAR  = 30
    TOT  = BSZ + MAR * 2
    PR   = 26
    IR   = 18

    C_LIGHT = "#F0D9B5"
    C_DARK  = "#B58863"
    C_FRAME = "#4A2C10"
    C_NUM   = "rgba(255,255,255,0.28)"

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    pm = {}
    for sq, k in wp:
        pm[sq] = ('w', k)
    for sq, k in bp:
        pm[sq] = ('b', k)

    hl_last = set(int(n) for n in re.findall(r'\d+', last_move)) if last_move else set()
    hl_hint = set(int(n) for n in re.findall(r'\d+', hint_move)) if hint_move else set()

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {TOT} {TOT}" width="100%" '
        f'style="max-width:{TOT}px;display:block;margin:0 auto">'
    ]

    svg.append(f"""<defs>
      <filter id="sh">
        <feDropShadow dx="1" dy="2" stdDeviation="3" flood-opacity="0.6"/>
      </filter>
      <filter id="glow">
        <feGaussianBlur stdDeviation="3" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <radialGradient id="wg" cx="38%" cy="32%" r="60%">
        <stop offset="0%" stop-color="#FFFFFF"/>
        <stop offset="55%" stop-color="#EDD9A3"/>
        <stop offset="100%" stop-color="#C8A050"/>
      </radialGradient>
      <radialGradient id="bg" cx="38%" cy="32%" r="60%">
        <stop offset="0%" stop-color="#666"/>
        <stop offset="55%" stop-color="#2A2A2A"/>
        <stop offset="100%" stop-color="#0A0A0A"/>
      </radialGradient>
      <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="5" markerHeight="5" orient="auto">
        <path d="M0 0 L10 5 L0 10z" fill="#FF4500"/>
      </marker>
      <marker id="hint-arr" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="5" markerHeight="5" orient="auto">
        <path d="M0 0 L10 5 L0 10z" fill="#00DD55"/>
      </marker>
    </defs>""")

    # إطار خشبي
    svg.append(
        f'<rect x="0" y="0" width="{TOT}" height="{TOT}" rx="10" fill="{C_FRAME}"/>'
    )
    svg.append(
        f'<rect x="{MAR-5}" y="{MAR-5}" width="{BSZ+10}" height="{BSZ+10}" '
        f'rx="5" fill="#2D1A08" stroke="#7A5028" stroke-width="1.5"/>'
    )

    # حروف وأرقام
    for i in range(8):
        cx = MAR + i * CELL + CELL // 2
        svg.append(
            f'<text x="{cx}" y="{MAR - 10}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{chr(65+i)}</text>'
        )
        cy = MAR + i * CELL + CELL // 2 + 5
        svg.append(
            f'<text x="{MAR - 14}" y="{cy}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{8-i}</text>'
        )

    sq_n = 0
    coords = {}

    for r in range(8):
        for c in range(8):
            x = MAR + c * CELL
            y = MAR + r * CELL
            dark = (r + c) % 2 == 1
            fill = C_DARK if dark else C_LIGHT
            svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{fill}"/>')

            if dark:
                sq_n += 1
                cx = x + CELL // 2
                cy = y + CELL // 2
                coords[sq_n] = (cx, cy)

                # تظليل
                if sq_n in hl_last:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="rgba(255,220,50,0.32)"/>'
                    )
                if sq_n in hl_hint:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="rgba(0,220,80,0.22)"/>'
                    )
                if selected_sq and sq_n == selected_sq:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="rgba(0,120,255,0.30)"/>'
                    )

                # رقم المربع
                svg.append(
                    f'<text x="{x+4}" y="{y+14}" font-size="10" '
                    f'fill="{C_NUM}" font-family="monospace">{sq_n}</text>'
                )

                # القطعة
                if sq_n in pm:
                    col, is_k = pm[sq_n]
                    g   = "url(#wg)" if col == 'w' else "url(#bg)"
                    stk = "#BFA070" if col == 'w' else "#111"
                    inn = "#D4B896" if col == 'w' else "#2A2A2A"

                    # ظل
                    svg.append(
                        f'<circle cx="{cx+1}" cy="{cy+3}" r="{PR}" '
                        f'fill="rgba(0,0,0,0.4)"/>'
                    )
                    # جسم
                    svg.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{PR}" '
                        f'fill="{g}" stroke="{stk}" stroke-width="2.5" '
                        f'filter="url(#sh)"/>'
                    )
                    # حلقة داخلية
                    svg.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{IR}" '
                        f'fill="none" stroke="{inn}" '
                        f'stroke-width="1.5" opacity="0.5"/>'
                    )
                    # ملك
                    if is_k:
                        cr = "#DAA520" if col == 'w' else "#FFD700"
                        svg.append(
                            f'<text x="{cx}" y="{cy+8}" '
                            f'text-anchor="middle" font-size="24" '
                            f'fill="{cr}" font-weight="bold" '
                            f'filter="url(#glow)">♛</text>'
                        )

    # حدود الرقعة
    svg.append(
        f'<rect x="{MAR}" y="{MAR}" width="{BSZ}" height="{BSZ}" '
        f'fill="none" stroke="{C_FRAME}" stroke-width="2"/>'
    )

    # أسهم
    _arrow(svg, last_move, coords, "#FF4500", "arr", "", "0.82")
    _arrow(svg, hint_move, coords, "#00DD55", "hint-arr",
           'stroke-dasharray="10,6"', "0.92")

    svg.append('</svg>')
    return '\n'.join(svg)


# ════════════════════════════════════════════
# فهرس البرنامج التفاعلي
# ════════════════════════════════════════════
def render_index():
    """عرض فهرس تفاعلي لأقسام البرنامج"""
    st.markdown("""
    <div class="index-container">
        <div class="index-title">📋 فهرس البرنامج</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;direction:rtl">

            <div class="index-item">
                <span class="index-icon">🎮</span>
                <span>
                    <div class="index-label">رقعة اللعب</div>
                    <div class="index-desc">8×8 | 12 قطعة</div>
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
                    <div class="index-desc">تحليل عميق + نصائح</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">📊</span>
                <span>
                    <div class="index-label">الإحصائيات</div>
                    <div class="index-desc">TT | History | Killers</div>
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
                    <div class="index-desc">صعوبة | لون | وقت</div>
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
                    <div class="index-desc">تقييم لحظي + أفضل الحركات</div>
                </span>
            </div>

        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# لوحة التحليل الذكي
# ════════════════════════════════════════════
def render_analysis_panel(analysis: dict):
    """عرض نتائج التحليل العميق"""
    if "error" in analysis:
        st.error(analysis["error"])
        return

    # ─ العنوان ─
    st.markdown("""
    <div class="analysis-title">
        🧠 تحليل المحرك العبقري
    </div>
    """, unsafe_allow_html=True)

    # ─ الفائدة + المرحلة ─
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="analysis-section">
            <div class="analysis-label">التفوق الحالي</div>
            <div class="analysis-value">{analysis['advantage']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="analysis-section">
            <div class="analysis-label">مرحلة اللعبة</div>
            <div class="analysis-value">🎯 {analysis['phase']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ─ التوصية ─
    st.markdown(f"""
    <div class="analysis-section">
        <div class="analysis-label">💬 توصية المحرك</div>
        <div class="analysis-value" style="line-height:1.7">
            {analysis['recommendation'].replace(chr(10), '<br>')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─ أفضل 3 حركات ─
    st.markdown("""
    <div class="analysis-label" style="margin-top:10px">
        🏆 أفضل الحركات:
    </div>
    """, unsafe_allow_html=True)

    ranks = ["🥇", "🥈", "🥉"]
    styles = ["best", "good", "neutral"]
    for i, mv in enumerate(analysis.get("top_moves", [])):
        st.markdown(f"""
        <div class="move-card {styles[i]}">
            <span class="move-rank">{ranks[i]}</span>
            <span class="move-str">{mv['move']}</span>
            <span class="move-label">{mv['label']} | {mv['score']:+.0f}</span>
        </div>
        """, unsafe_allow_html=True)

    # ─ التهديدات ─
    st.markdown("""
    <div class="analysis-label" style="margin-top:10px">
        ⚠️ التهديدات والملاحظات:
    </div>
    """, unsafe_allow_html=True)
    for t in analysis.get("threats", []):
        st.markdown(
            f'<div style="font-family:Tajawal;font-size:0.88rem;'
            f'color:#CCC;padding:3px 0;direction:rtl">{t}</div>',
            unsafe_allow_html=True
        )

    # ─ عمق البحث ─
    depth = analysis.get("reached_depth", 0)
    st.markdown(
        f'<div style="margin-top:10px;font-family:Tajawal;'
        f'font-size:0.8rem;color:#666;direction:rtl">'
        f'🔬 عمق البحث المحقق: <b style="color:#888">{depth}</b></div>',
        unsafe_allow_html=True
    )


# ════════════════════════════════════════════
# إدارة الحالة
# ════════════════════════════════════════════
def init_game(player_color, ai_color, depth, time_limit):
    clear_transposition_table()
    board = Board(variant="english")
    st.session_state.update({
        'board':         board,
        'player_color':  player_color,
        'ai_color':      ai_color,
        'depth':         depth,
        'time_limit':    time_limit,
        'move_history':  [],
        'game_over':     False,
        'winner':        None,
        'last_move':     "",
        'hint_move':     "",
        'ai_info':       "",
        'game_started':  True,
        'pending_ai':    board.turn == ai_color,
        'celebrated':    False,
        'analysis':      None,
        'show_analysis': False,
        'move_count':    0,
        'captures_w':    0,
        'captures_b':    0,
    })


def play_human_move():
    if st.session_state.game_over:
        return
    board = st.session_state.board
    legal = get_legal_moves(board)
    idx   = st.session_state.get("move_select", 0)
    if not (0 <= idx < len(legal)):
        return

    move = legal[idx]
    ms   = fmt(move)
    is_cap = _is_capture(move)

    board.push(move)
    mtype = "⚔️" if is_cap else ("👑" if _is_promotion(move) else "➡️")

    st.session_state.move_history.append(("👤", ms, mtype))
    st.session_state.last_move    = ms
    st.session_state.hint_move    = ""
    st.session_state.analysis     = None
    st.session_state.show_analysis = False
    st.session_state.move_count  += 1
    if is_cap:
        st.session_state.captures_w += 1

    if is_game_over(board):
        st.session_state.game_over = True
        st.session_state.winner = get_winner(
            board,
            st.session_state.player_color,
            st.session_state.ai_color
        )
    else:
        st.session_state.pending_ai = True


def play_ai_move():
    board      = st.session_state.board
    ai_color   = st.session_state.ai_color
    depth      = st.session_state.depth
    time_limit = st.session_state.get('time_limit', 5.0)

    best, score, reached = find_best_move(
        board, ai_color,
        max_depth=depth,
        time_limit=time_limit
    )

    if best:
        ms     = fmt(best)
        is_cap = _is_capture(best)
        board.push(best)

        mtype = "⚔️" if is_cap else ("👑" if _is_promotion(best) else "➡️")
        st.session_state.move_history.append(("🤖", ms, mtype))
        st.session_state.last_move  = ms
        st.session_state.hint_move  = ""
        st.session_state.analysis   = None
        st.session_state.move_count += 1
        if is_cap:
            st.session_state.captures_b += 1
        st.session_state.ai_info = (
            f"عمق: **{reached}** | تقييم: **{score:+.0f}** | "
            f"جدول: **{get_tt_stats()['size']:,}** إدخال"
        )

        if is_game_over(board):
            st.session_state.game_over = True
            st.session_state.winner = get_winner(
                board,
                st.session_state.player_color,
                ai_color
            )
        else:
            st.session_state.pending_ai = False
    else:
        st.session_state.game_over  = True
        st.session_state.winner     = 'player'
        st.session_state.pending_ai = False


def undo_move():
    history = st.session_state.move_history
    if not history:
        return
    to_remove = min(2, len(history))
    remaining = history[:-to_remove]

    board = Board(variant="english")
    for _, mv_str, _ in remaining:
        legal = get_legal_moves(board)
        for lm in legal:
            if fmt(lm) == mv_str or str(lm) == mv_str:
                board.push(lm)
                break

    last = remaining[-1][1] if remaining else ""
    st.session_state.update({
        'board':        board,
        'move_history': remaining,
        'game_over':    False,
        'winner':       None,
        'last_move':    last,
        'hint_move':    "",
        'pending_ai':   False,
        'celebrated':   False,
        'analysis':     None,
        'show_analysis': False,
    })


# ════════════════════════════════════════════
# الواجهة الرئيسية
# ════════════════════════════════════════════
def main():
    inject_css()

    if not DRAUGHTS_OK or not DRAUGHTS_AVAILABLE:
        st.error("❌ مكتبة `pydraughts` غير مثبتة!")
        st.code("pip install pydraughts", language="bash")
        st.stop()

    # ════ الشريط الجانبي ════
    with st.sidebar:
        st.markdown(
            '<div style="text-align:center;font-family:Tajawal;'
            'font-size:1.4rem;font-weight:900;color:#FFD700;'
            'padding:8px 0">♟️ داما AI</div>',
            unsafe_allow_html=True
        )

        # ─ الفهرس ─
        with st.expander("📋 فهرس البرنامج", expanded=False):
            render_index()

        st.markdown("---")
        st.markdown('<div class="section-header">⚙️ إعدادات اللعبة</div>',
                    unsafe_allow_html=True)

        color_choice = st.radio(
            "🎨 لونك:",
            ["⬜ أبيض (تبدأ أنت)", "⬛ أسود (يبدأ الكمبيوتر)"],
            index=0, label_visibility="collapsed"
        )

        difficulty = st.select_slider(
            "🎯 مستوى الصعوبة",
            options=["مبتدئ", "سهل", "متوسط", "صعب", "خبير", "عبقري"],
            value="متوسط"
        )
        depth_map = {
            "مبتدئ": 2, "سهل": 3, "متوسط": 5,
            "صعب": 8, "خبير": 12, "عبقري": 20
        }
        time_map = {
            "مبتدئ": 1.0, "سهل": 2.0, "متوسط": 4.0,
            "صعب": 6.0, "خبير": 10.0, "عبقري": 15.0
        }
        depth      = depth_map[difficulty]
        time_limit = time_map[difficulty]

        st.markdown(
            f'<div style="font-family:Tajawal;font-size:0.8rem;'
            f'color:#666;direction:rtl;margin-top:-8px">'
            f'عمق {depth} | وقت {time_limit:.0f}ث</div>',
            unsafe_allow_html=True
        )

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            new_game = st.button("🆕 جديدة", use_container_width=True)
        with c2:
            undo = st.button(
                "↩️ تراجع",
                use_container_width=True,
                disabled=not (
                    st.session_state.get("game_started") and
                    len(st.session_state.get("move_history", [])) > 0
                )
            )

        if new_game:
            pc = WHITE if "أبيض" in color_choice else BLACK
            ac = BLACK if "أبيض" in color_choice else WHITE
            init_game(pc, ac, depth, time_limit)
            st.rerun()

        if undo and st.session_state.get("game_started"):
            undo_move()
            st.rerun()

        # ─ الإحصائيات ─
        if st.session_state.get("game_started"):
            st.markdown("---")
            st.markdown(
                '<div class="section-header">📊 إحصائيات</div>',
                unsafe_allow_html=True
            )

            board = st.session_state.board
            wm, wk, bm, bk = count_pieces(board)
            wt = wm + wk
            bt = bm + bk

            st.markdown(f"""
            <div class="info-card">
                <div class="piece-count">
                    <div class="piece-side">
                        <div style="font-size:1.3rem">⬜</div>
                        <div class="piece-num">{wt}</div>
                        <div class="piece-sub">
                            {wm}🔵 {wk}👑
                        </div>
                    </div>
                    <div style="font-size:1.2rem;color:#555">⚔️</div>
                    <div class="piece-side">
                        <div style="font-size:1.3rem">⬛</div>
                        <div class="piece-num">{bt}</div>
                        <div class="piece-sub">
                            {bm}🔵 {bk}👑
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # إحصائيات TT
            tt = get_tt_stats()
            st.markdown(f"""
            <div style="direction:rtl;font-family:Tajawal">
                <span class="stat-pill stat-green">
                    🎯 {st.session_state.get('move_count',0)} حركة
                </span>
                <span class="stat-pill stat-blue">
                    💾 {tt['size']:,} TT
                </span>
                <span class="stat-pill stat-orange">
                    📈 {tt['hit_rate']} hits
                </span>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.get('ai_info'):
                st.markdown(
                    f'<div class="info-card" style="font-size:0.85rem;'
                    f'direction:rtl">🤖 {st.session_state.ai_info}</div>',
                    unsafe_allow_html=True
                )

            # ─ سجل الحركات ─
            history = st.session_state.get("move_history", [])
            if history:
                st.markdown("---")
                st.markdown(
                    '<div class="section-header">📜 سجل الحركات</div>',
                    unsafe_allow_html=True
                )
                with st.container(height=220):
                    for i, item in enumerate(history, 1):
                        who, mv = item[0], item[1]
                        mtype = item[2] if len(item) > 2 else "➡️"
                        is_last = i == len(history)
                        cls = "history-row last-move" if is_last else "history-row"
                        st.markdown(
                            f'<div class="{cls}">'
                            f'<span class="h-num">{i}</span>'
                            f'<span class="h-who">{who}</span>'
                            f'<span class="h-move">{mv}</span>'
                            f'<span class="h-type">{mtype}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

    # ════ المنطقة الرئيسية ════

    # العنوان
    st.markdown(
        '<div class="main-title">♟️ داما الذكاء الاصطناعي</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-title">'
        'Minimax | Alpha-Beta | TT | LMR | Quiescence | عمق حتى 20'
        '</div>',
        unsafe_allow_html=True
    )

    # شاشة الترحيب
    if not st.session_state.get("game_started"):
        st.markdown("---")

        # عرض الفهرس في الصفحة الرئيسية أيضاً
        render_index()

        st.info("👈 اضغط **'🆕 جديدة'** في الشريط الجانبي للبدء", icon="🎮")
        demo = Board(variant="english")
        st.markdown(
            f'<div class="board-wrap">{render_board(demo)}</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # دور AI
    if st.session_state.pending_ai and not st.session_state.game_over:
        with st.spinner("🤖 المحرك يحسب أفضل حركة..."):
            play_ai_move()
        st.rerun()

    board        = st.session_state.board
    player_color = st.session_state.player_color
    ai_color     = st.session_state.ai_color

    # ─ تخطيط ثنائي: رقعة + تحليل ─
    col_board, col_analysis = st.columns([1.1, 0.9])

    with col_board:
        # رسالة الحالة
        if st.session_state.game_over:
            winner = st.session_state.winner
            if winner == 'player':
                st.markdown(
                    '<div class="status-box status-win">🎉 مبروك! فزت! 🏆</div>',
                    unsafe_allow_html=True
                )
                if not st.session_state.get("celebrated"):
                    st.balloons()
                    st.session_state.celebrated = True
            elif winner == 'ai':
                st.markdown(
                    '<div class="status-box status-lose">'
                    '💻 الكمبيوتر فاز! حاول مرة أخرى 💪</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-box status-draw">🤝 تعادل!</div>',
                    unsafe_allow_html=True
                )
        else:
            if board.turn == player_color:
                legal_n = len(get_legal_moves(board))
                st.markdown(
                    f'<div class="status-box status-player">'
                    f'👤 دورك | {legal_n} حركة متاحة</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-box status-ai">🤖 دور المحرك...</div>',
                    unsafe_allow_html=True
                )

        # الرقعة
        svg = render_board(
            board,
            st.session_state.get("last_move", ""),
            st.session_state.get("hint_move", "")
        )
        st.markdown(
            f'<div class="board-wrap">{svg}</div>',
            unsafe_allow_html=True
        )

        # ─ أدوات اللاعب ─
        if not st.session_state.game_over and board.turn == player_color:
            legal = get_legal_moves(board)
            if legal:
                labels = [fmt(m) for m in legal]

                st.selectbox(
                    "🎯 الحركة:",
                    range(len(labels)),
                    format_func=lambda i: (
                        f"[{i+1}] {labels[i]}"
                        f"{'  ⚔️' if _is_capture(legal[i]) else ''}"
                        f"{'  👑' if _is_promotion(legal[i]) else ''}"
                    ),
                    key="move_select"
                )

                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button(
                        "▶️ العب!", use_container_width=True, type="primary"
                    ):
                        play_human_move()
                        st.rerun()
                with b2:
                    if st.button("↩️ تراجع", use_container_width=True):
                        undo_move()
                        st.rerun()
                with b3:
                    if st.button("🔄 تحديث", use_container_width=True):
                        st.rerun()

    # ════ لوحة التحليل الجانبية ════
    with col_analysis:
        st.markdown(
            '<div class="section-header">🧠 لوحة التحليل الذكي</div>',
            unsafe_allow_html=True
        )

        if not st.session_state.game_over:
            # شريط التقييم اللحظي
            try:
                raw_score = evaluate_position(board, player_color)
                pct = eval_pct(raw_score)
                marker_pos = int(pct)
                st.markdown(f"""
                <div class="eval-container">
                    <div style="display:flex;justify-content:space-between;
                        font-family:Tajawal;font-size:0.8rem;color:#888">
                        <span>🤖 AI</span>
                        <span>⚖️ {raw_score:+.0f}</span>
                        <span>👤 أنت</span>
                    </div>
                    <div class="eval-bar-bg">
                        <div class="eval-marker"
                             style="left:{marker_pos}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                pass

            # ─ زر التحليل العبقري ─
            depth_for_hint = st.session_state.get('depth', 8)
            hint_depth = min(depth_for_hint, MAX_DEPTH)

            ba, bb = st.columns(2)
            with ba:
                if st.button(
                    "🧠 تحليل عبقري",
                    use_container_width=True,
                    help=f"تحليل بعمق {hint_depth} مستوى"
                ):
                    with st.spinner(
                        f"🔬 جاري التحليل العميق (عمق {hint_depth})..."
                    ):
                        t0 = time.time()
                        analysis = analyze_position(
                            board,
                            player_color,
                            ai_color,
                            depth=hint_depth,
                            time_limit=min(
                                st.session_state.get('time_limit', 5.0),
                                12.0
                            )
                        )
                        elapsed = time.time() - t0
                        analysis['analysis_time'] = f"{elapsed:.1f}ث"

                        if "best_move_str" in analysis:
                            st.session_state.hint_move = (
                                analysis["best_move_str"]
                            )
                        st.session_state.analysis     = analysis
                        st.session_state.show_analysis = True
                    st.rerun()

            with bb:
                if st.button(
                    "💡 تلميح سريع",
                    use_container_width=True,
                    help="تلميح سريع بعمق 4"
                ):
                    with st.spinner("⚡ تلميح سريع..."):
                        hm, _, _ = find_best_move(
                            board, player_color,
                            max_depth=4, time_limit=1.5
                        )
                        if hm:
                            st.session_state.hint_move = fmt(hm)
                    st.rerun()

            # ─ عرض نتيجة التحليل ─
            if (st.session_state.get('show_analysis') and
                    st.session_state.get('analysis')):
                analysis = st.session_state.analysis
                with st.container():
                    st.markdown(
                        '<div class="analysis-card">',
                        unsafe_allow_html=True
                    )
                    render_analysis_panel(analysis)
                    if 'analysis_time' in analysis:
                        st.markdown(
                            f'<div style="text-align:left;font-size:0.75rem;'
                            f'color:#555;margin-top:6px">'
                            f'⏱ {analysis["analysis_time"]}</div>',
                            unsafe_allow_html=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                if st.button("✖ إغلاق التحليل", use_container_width=True):
                    st.session_state.show_analysis = False
                    st.session_state.hint_move = ""
                    st.rerun()

        else:
            # ─ إحصائيات نهاية اللعبة ─
            st.markdown("""
            <div class="analysis-card">
                <div class="analysis-title">📊 إحصائيات المباراة</div>
            """, unsafe_allow_html=True)

            total_moves = len(st.session_state.get('move_history', []))
            cap_w = st.session_state.get('captures_w', 0)
            cap_b = st.session_state.get('captures_b', 0)
            tt = get_tt_stats()

            st.markdown(f"""
            <div class="analysis-section">
                <div class="analysis-label">إجمالي الحركات</div>
                <div class="analysis-value">🎯 {total_moves} حركة</div>
            </div>
            <div class="analysis-section">
                <div class="analysis-label">الأكل</div>
                <div class="analysis-value">
                    ⬜ {cap_w} &nbsp;|&nbsp; ⬛ {cap_b}
                </div>
            </div>
            <div class="analysis-section">
                <div class="analysis-label">إحصائيات المحرك</div>
                <div class="analysis-value">
                    💾 {tt['size']:,} موضع محلل
                    <br>📈 {tt['hit_rate']} معدل الإصابة
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button(
                "🆕 لعبة جديدة", use_container_width=True, type="primary"
            ):
                pc = WHITE if "أبيض" in st.session_state.get(
                    'color_choice', "أبيض"
                ) else BLACK
                ac = BLACK if pc == WHITE else WHITE
                init_game(pc, ac, depth, time_limit)
                st.rerun()


if __name__ == "__main__":
    main()
