"""
لعبة الداما الكلاسيكية - واجهة Streamlit المتقدمة الكاملة
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
    _capture_count,
    _phase_label,
    _game_phase,
    clear_transposition_table,
    get_tt_stats,
    DRAUGHTS_AVAILABLE,
    MAX_DEPTH,
    _detect_ui_threats,
)

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

    html, body, [class*="css"] { direction: rtl; }

    .main-title {
        text-align: center;
        font-family: 'Tajawal', sans-serif;
        font-size: 2.6rem;
        font-weight: 900;
        background: linear-gradient(135deg,#FFD700 0%,#FF8C00 50%,#FF4500 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0; padding: 10px 0 2px;
        letter-spacing: 2px;
    }
    .sub-title {
        text-align: center;
        font-family: 'Tajawal', sans-serif;
        color: #8899AA; font-size: 0.92rem;
        margin: 0 0 6px; letter-spacing: 1px;
    }
    .index-container {
        background: linear-gradient(135deg,rgba(30,40,60,0.97),rgba(20,30,50,0.97));
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: 12px; padding: 18px;
        margin: 8px 0; font-family: 'Tajawal', sans-serif; direction: rtl;
    }
    .index-title {
        font-size: 1.2rem; font-weight: 900; color: #FFD700;
        margin-bottom: 10px;
        border-bottom: 2px solid rgba(255,215,0,0.3); padding-bottom: 6px;
    }
    .index-item {
        display: flex; align-items: center;
        padding: 7px 10px; margin: 3px 0;
        border-radius: 7px; border: 1px solid transparent;
    }
    .index-item:hover {
        background: rgba(255,215,0,0.1);
        border-color: rgba(255,215,0,0.3);
    }
    .index-icon { font-size: 1.15rem; margin-left: 9px; }
    .index-label { font-size: 0.9rem; color: #DDD; font-weight: 700; }
    .index-desc  { font-size: 0.72rem; color: #888; }
    .status-box {
        text-align: center; padding: 9px 14px;
        border-radius: 10px; font-family: 'Tajawal', sans-serif;
        font-size: 1rem; font-weight: 700; margin: 5px 0; direction: rtl;
    }
    .status-player {
        background: linear-gradient(135deg,#1B5E20,#2E7D32);
        color:#FFF; border: 2px solid #4CAF50;
    }
    .status-ai {
        background: linear-gradient(135deg,#B71C1C,#C62828);
        color:#FFF; border: 2px solid #EF5350;
    }
    .status-win {
        background: linear-gradient(135deg,#F9A825,#FFD54F);
        color:#1A1A1A; border: 2px solid #FFD700;
        font-size:1.35rem; animation: pulse 1s infinite;
    }
    .status-lose {
        background: linear-gradient(135deg,#37474F,#546E7A);
        color:#FFF; border: 2px solid #78909C;
    }
    .status-draw {
        background: linear-gradient(135deg,#0D47A1,#1565C0);
        color:#FFF; border: 2px solid #42A5F5;
    }
    @keyframes pulse {
        0%,100% { transform:scale(1); }
        50% { transform:scale(1.02); }
    }
    .analysis-card {
        background: linear-gradient(135deg,rgba(12,22,45,0.99),rgba(18,32,65,0.99));
        border: 2px solid rgba(0,200,100,0.4);
        border-radius: 14px; padding: 16px; margin: 8px 0;
        font-family: 'Tajawal', sans-serif; direction: rtl;
        box-shadow: 0 4px 22px rgba(0,200,100,0.12);
    }
    .analysis-title {
        font-size: 1.1rem; font-weight: 900; color: #00CC66;
        margin-bottom: 8px;
    }
    .analysis-section {
        margin: 8px 0; padding: 9px;
        background: rgba(255,255,255,0.035);
        border-radius: 7px;
        border-right: 3px solid rgba(0,200,100,0.45);
    }
    .analysis-label { font-size: 0.78rem; color: #888; margin-bottom: 3px; }
    .analysis-value { font-size: 0.92rem; color: #EEE; font-weight: 700; }
    .move-card {
        display: flex; align-items: center;
        padding: 7px 11px; margin: 3px 0;
        border-radius: 7px; border: 1px solid rgba(255,255,255,0.1);
        font-family: 'Tajawal', sans-serif; direction: rtl;
    }
    .move-card.best    { background:rgba(0,200,100,0.14); border-color:rgba(0,200,100,0.38); }
    .move-card.good    { background:rgba(255,200,0,0.07);  border-color:rgba(255,200,0,0.28); }
    .move-card.neutral { background:rgba(100,100,100,0.09); }
    .move-card.bad     { background:rgba(255,60,60,0.07);   border-color:rgba(255,60,60,0.25); }
    .move-rank  { font-size:1.05rem; margin-left:7px; }
    .move-str   { font-size:0.95rem; font-weight:900; color:#FFF; font-family:monospace; min-width:75px; }
    .move-label { font-size:0.75rem; color:#AAA; margin-right:auto; }
    .move-badge {
        font-size:0.68rem; padding:2px 6px; border-radius:10px;
        margin-right:4px; font-weight:700;
    }
    .badge-cap  { background:rgba(255,80,80,0.25);  color:#FF8888; }
    .badge-prom { background:rgba(255,200,0,0.25);  color:#FFD700; }
    .eval-container {
        background: rgba(255,255,255,0.045);
        border-radius: 8px; padding: 9px 13px; margin: 5px 0;
        font-family: 'Tajawal', sans-serif;
    }
    .eval-bar-bg {
        height: 13px; border-radius: 6px;
        background: linear-gradient(to left,
            #EF5350 0%,#FF8C00 25%,#FFC107 40%,
            #888 50%,
            #66BB6A 60%,#00C853 75%,#00E676 100%);
        position: relative; margin: 5px 0; overflow: hidden;
    }
    .eval-marker {
        position: absolute; top: 0; width: 3px; height: 100%;
        background: white; border-radius: 2px;
        box-shadow: 0 0 4px rgba(255,255,255,0.8);
    }
    .info-card {
        background: rgba(255,255,255,0.038);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 9px; padding: 12px; margin: 7px 0;
        font-family: 'Tajawal', sans-serif; direction: rtl;
    }
    .piece-count {
        display: flex; justify-content: space-around;
        align-items: center; padding: 5px;
    }
    .piece-side { text-align: center; }
    .piece-num  { font-size: 1.9rem; font-weight: 900; }
    .piece-sub  { font-size: 0.76rem; color: #999; }
    .history-row {
        display: flex; align-items: center;
        padding: 4px 7px; margin: 2px 0; border-radius: 5px;
        font-family: 'Tajawal', sans-serif; direction: rtl; font-size: 0.86rem;
    }
    .history-row:nth-child(odd) { background: rgba(255,255,255,0.028); }
    .history-row.last-move {
        background: rgba(255,215,0,0.11);
        border: 1px solid rgba(255,215,0,0.28); font-weight: 700;
    }
    .h-num  { color:#666; width:22px; flex-shrink:0; }
    .h-who  { width:26px; flex-shrink:0; }
    .h-move { color:#EEE; font-family:monospace; flex:1; }
    .h-type { font-size:0.72rem; color:#888; }
    .stButton > button {
        font-family:'Tajawal',sans-serif !important;
        font-weight:700 !important; border-radius:8px !important;
        transition: all 0.18s !important;
    }
    .stButton > button:hover {
        transform:translateY(-1px) !important;
        box-shadow:0 5px 18px rgba(0,0,0,0.38) !important;
    }
    .stButton > button[kind="primary"] {
        background:linear-gradient(135deg,#00C853,#00E676) !important;
        color:#000 !important; border:none !important;
    }
    .board-wrap { display:flex; justify-content:center; padding:6px 0; }
    .stat-pill {
        display:inline-block; padding:3px 9px; border-radius:18px;
        font-size:0.76rem; font-family:'Tajawal',sans-serif;
        margin:2px 2px; font-weight:700;
    }
    .sg { background:rgba(0,200,80,0.18);   color:#00E676; }
    .sb { background:rgba(0,150,255,0.18);  color:#64B5F6; }
    .so { background:rgba(255,150,0,0.18);  color:#FFB74D; }
    .sr { background:rgba(255,80,80,0.18);  color:#EF9A9A; }
    .section-header {
        font-family:'Tajawal',sans-serif; font-size:1.05rem;
        font-weight:900; color:#FFD700; padding:7px 0;
        border-bottom:1px solid rgba(255,215,0,0.18);
        margin:10px 0 7px; direction:rtl;
    }
    .hint-box {
        background:rgba(0,200,100,0.07);
        border:1px solid rgba(0,200,100,0.28);
        border-radius:7px; padding:9px 13px; margin:5px 0;
        font-family:'Tajawal',sans-serif; font-size:0.88rem;
        direction:rtl; color:#88FFBB;
    }
    .safety-box {
        display:flex; gap:8px; margin:6px 0; direction:rtl;
    }
    .safety-item {
        flex:1; text-align:center; padding:8px;
        border-radius:8px; font-family:'Tajawal',sans-serif;
    }
    .safety-good { background:rgba(0,200,80,0.12); border:1px solid rgba(0,200,80,0.3); }
    .safety-bad  { background:rgba(255,60,60,0.12); border:1px solid rgba(255,60,60,0.3); }
    .safety-num  { font-size:1.5rem; font-weight:900; }
    .safety-lbl  { font-size:0.72rem; color:#999; }
    .welcome-feature {
        display:flex; align-items:flex-start;
        padding:9px 13px; margin:5px 0; border-radius:9px;
        background:rgba(255,255,255,0.035);
        border:1px solid rgba(255,255,255,0.07);
        font-family:'Tajawal',sans-serif; direction:rtl; gap:11px;
    }
    .wf-icon  { font-size:1.5rem; flex-shrink:0; }
    .wf-title { font-size:0.92rem; font-weight:700; color:#FFD700; margin-bottom:2px; }
    .wf-desc  { font-size:0.78rem; color:#999; line-height:1.4; }
    .game-over-stats {
        background:linear-gradient(135deg,rgba(12,22,45,0.99),rgba(18,32,65,0.99));
        border:2px solid rgba(255,215,0,0.28);
        border-radius:13px; padding:18px; margin:8px 0;
        font-family:'Tajawal',sans-serif; direction:rtl;
    }
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# دوال مساعدة
# ════════════════════════════════════════════
def fmt(move) -> str:
    r = format_move_to_string(move)
    return r if r and r != "?" else "حركة"


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


def eval_to_pct(score: float) -> float:
    return max(2.0, min(98.0, 50.0 + float(score) / 80.0))


# ════════════════════════════════════════════
# رسم الرقعة SVG
# ════════════════════════════════════════════
def _draw_arrow(parts, mv_str, coords, color, marker, dash, opacity):
    if not mv_str:
        return
    nums = []
    for n in re.findall(r'\d+', mv_str):
        try:
            v = int(n)
            if v in coords:
                nums.append(v)
        except ValueError:
            pass
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


def render_board(board, last_move="", hint_move="",
                 threatened_squares=None) -> str:
    """رسم رقعة الداما SVG كامل مع تظليل القطع المهددة"""
    CELL  = 66
    BSZ   = CELL * 8
    MAR   = 30
    TOT   = BSZ + MAR * 2
    PR    = 26
    IR    = 18
    TS    = threatened_squares or set()

    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    pm = {}
    for sq, k in wp:
        pm[sq] = ('w', k)
    for sq, k in bp:
        pm[sq] = ('b', k)

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
        f'viewBox="0 0 {TOT} {TOT}" width="100%" '
        f'style="max-width:{TOT}px;display:block;margin:0 auto">'
    )
    svg.append(f"""<defs>
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
        <stop offset="0%"   stop-color="#FFFFFF"/>
        <stop offset="55%"  stop-color="#EDD9A3"/>
        <stop offset="100%" stop-color="#C8A050"/>
      </radialGradient>
      <radialGradient id="bg" cx="38%" cy="32%" r="60%">
        <stop offset="0%"   stop-color="#666"/>
        <stop offset="55%"  stop-color="#2A2A2A"/>
        <stop offset="100%" stop-color="#0A0A0A"/>
      </radialGradient>
      <marker id="la" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="5" markerHeight="5" orient="auto">
        <path d="M0 0 L10 5 L0 10z" fill="#FF4500"/>
      </marker>
      <marker id="ha" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="5" markerHeight="5" orient="auto">
        <path d="M0 0 L10 5 L0 10z" fill="#00DD55"/>
      </marker>
    </defs>""")

    svg.append(
        f'<rect x="0" y="0" width="{TOT}" height="{TOT}" rx="10" fill="#4A2C10"/>'
    )
    svg.append(
        f'<rect x="{MAR-5}" y="{MAR-5}" width="{BSZ+10}" height="{BSZ+10}" '
        f'rx="5" fill="#2D1A08" stroke="#7A5028" stroke-width="1.5"/>'
    )

    for i in range(8):
        cx = MAR + i * CELL + CELL // 2
        svg.append(
            f'<text x="{cx}" y="{MAR-10}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{chr(65+i)}</text>'
        )
    for i in range(8):
        cy = MAR + i * CELL + CELL // 2 + 5
        svg.append(
            f'<text x="{MAR-14}" y="{cy}" text-anchor="middle" '
            f'font-size="13" fill="#C8942A" font-family="monospace" '
            f'font-weight="bold">{8-i}</text>'
        )

    sq_n = 0
    coords = {}

    for row in range(8):
        for col in range(8):
            x = MAR + col * CELL
            y = MAR + row * CELL
            dark = (row + col) % 2 == 1
            svg.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'fill="{"#B58863" if dark else "#F0D9B5"}"/>'
            )

            if dark:
                sq_n += 1
                cx = x + CELL // 2
                cy = y + CELL // 2
                coords[sq_n] = (cx, cy)

                if sq_n in hl_last:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="rgba(255,220,50,0.30)"/>'
                    )
                if sq_n in hl_hint:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="rgba(0,220,80,0.20)"/>'
                    )
                # تظليل القطع المهددة
                if sq_n in TS:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="rgba(255,30,30,0.22)"/>'
                    )
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                        f'fill="none" stroke="rgba(255,60,60,0.6)" stroke-width="2"/>'
                    )

                svg.append(
                    f'<text x="{x+4}" y="{y+14}" font-size="10" '
                    f'fill="rgba(255,255,255,0.26)" '
                    f'font-family="monospace">{sq_n}</text>'
                )

                if sq_n in pm:
                    pc, is_k = pm[sq_n]
                    grad   = "url(#wg)" if pc == 'w' else "url(#bg)"
                    stk    = "#BFA070" if pc == 'w' else "#111"
                    inn    = "#D4B896" if pc == 'w' else "#2A2A2A"
                    danger = sq_n in TS

                    svg.append(
                        f'<circle cx="{cx+1}" cy="{cy+3}" r="{PR}" '
                        f'fill="rgba(0,0,0,0.4)"/>'
                    )
                    extra_filter = ' filter="url(#danger-glow)"' if danger else ' filter="url(#sh)"'
                    extra_stroke = ' stroke="#FF4444" stroke-width="3.5"' if danger else f' stroke="{stk}" stroke-width="2.5"'
                    svg.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{PR}" fill="{grad}"'
                        f'{extra_stroke}{extra_filter}/>'
                    )
                    svg.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{IR}" fill="none" '
                        f'stroke="{inn}" stroke-width="1.5" opacity="0.5"/>'
                    )

                    if is_k:
                        cr = "#DAA520" if pc == 'w' else "#FFD700"
                        svg.append(
                            f'<text x="{cx}" y="{cy+8}" text-anchor="middle" '
                            f'font-size="24" fill="{cr}" font-weight="bold" '
                            f'filter="url(#glow)">♛</text>'
                        )

                    # تحذير خطر
                    if danger:
                        svg.append(
                            f'<text x="{cx+18}" y="{cy-14}" font-size="14" '
                            f'fill="#FF4444">⚠</text>'
                        )

    svg.append(
        f'<rect x="{MAR}" y="{MAR}" width="{BSZ}" height="{BSZ}" '
        f'fill="none" stroke="#4A2C10" stroke-width="2"/>'
    )

    _draw_arrow(svg, last_move, coords, "#FF4500", "la", "", "0.80")
    _draw_arrow(svg, hint_move, coords,
                "#00DD55", "ha", 'stroke-dasharray="10,6"', "0.90")

    svg.append('</svg>')
    return '\n'.join(svg)


# ════════════════════════════════════════════
# فهرس البرنامج
# ════════════════════════════════════════════
def render_index():
    st.markdown("""
    <div class="index-container">
        <div class="index-title">📋 فهرس البرنامج</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;direction:rtl">

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
                    <div class="index-desc">Minimax+AB | عمق 24</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">💡</span>
                <span>
                    <div class="index-label">مساعد عبقري</div>
                    <div class="index-desc">تحليل عميق + 5 حركات</div>
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
                    <div class="index-desc">Forks + Traps</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">⚡</span>
                <span>
                    <div class="index-label">Aspiration Windows</div>
                    <div class="index-desc">بحث أسرع وأذكى</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">🔬</span>
                <span>
                    <div class="index-label">Quiescence Search</div>
                    <div class="index-desc">استقرار الأكل عمق 10</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">📚</span>
                <span>
                    <div class="index-label">كتاب الافتتاحيات</div>
                    <div class="index-desc">6 افتتاحيات مدروسة</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">🔀</span>
                <span>
                    <div class="index-label">Zobrist Hashing</div>
                    <div class="index-desc">TT بحجم 1M إدخال</div>
                </span>
            </div>

            <div class="index-item">
                <span class="index-icon">📊</span>
                <span>
                    <div class="index-label">PST + Structure</div>
                    <div class="index-desc">تقييم موضعي متقدم</div>
                </span>
            </div>

        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# لوحة التحليل
# ════════════════════════════════════════════
def render_analysis_panel(analysis: dict):
    if not analysis or "error" in analysis:
        st.error(f"❌ {analysis.get('error', 'خطأ') if analysis else 'لا يوجد تحليل'}")
        return

    st.markdown(
        '<div class="analysis-title">🧠 تحليل المحرك العبقري</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">التفوق الحالي</div>'
            f'<div class="analysis-value">{analysis.get("advantage","—")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">مرحلة اللعبة</div>'
            f'<div class="analysis-value">🎯 {analysis.get("phase","—")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # السلامة
    tm = analysis.get("threatened_mine", 0)
    to = analysis.get("threatened_opp",  0)
    st.markdown(
        f'<div class="safety-box">'
        f'<div class="safety-item {"safety-bad" if tm > 0 else "safety-good"}">'
        f'<div class="safety-num">{"⚠️" if tm > 0 else "✅"} {tm}</div>'
        f'<div class="safety-lbl">قطعك المهددة</div>'
        f'</div>'
        f'<div class="safety-item {"safety-good" if to > 0 else "safety-item"}">'
        f'<div class="safety-num">{"🎯" if to > 0 else "—"} {to}</div>'
        f'<div class="safety-lbl">قطع الخصم المهددة</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # التوصية
    rec = analysis.get("recommendation", "")
    if rec:
        st.markdown(
            f'<div class="analysis-section">'
            f'<div class="analysis-label">💬 توصية المحرك</div>'
            f'<div class="analysis-value" style="line-height:1.7">'
            f'{rec.replace(chr(10),"<br>")}'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # أفضل 5 حركات
    top = analysis.get("top_moves", [])
    if top:
        st.markdown(
            '<div class="analysis-label" style="margin-top:9px">'
            '🏆 أفضل الحركات:</div>',
            unsafe_allow_html=True
        )
        icons  = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        styles = ["best", "good", "neutral", "neutral", "bad"]
        for i, mv in enumerate(top):
            ico   = icons[i]  if i < len(icons)  else "▪️"
            sty   = styles[i] if i < len(styles) else "neutral"
            ms    = mv.get("move", "?")
            lbl   = mv.get("label", "")
            sc    = mv.get("score", 0)
            cap   = mv.get("is_capture", False)
            prom  = mv.get("is_promotion", False)
            capn  = mv.get("cap_count", 0)
            badges = ""
            if cap:
                badges += f'<span class="move-badge badge-cap">⚔️ ×{capn}</span>'
            if prom:
                badges += '<span class="move-badge badge-prom">👑</span>'
            st.markdown(
                f'<div class="move-card {sty}">'
                f'<span class="move-rank">{ico}</span>'
                f'<span class="move-str">{ms}</span>'
                f'{badges}'
                f'<span class="move-label">{lbl} | {sc:+.0f}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # التهديدات
    threats = analysis.get("threats", [])
    if threats:
        st.markdown(
            '<div class="analysis-label" style="margin-top:9px">'
            '⚠️ التهديدات:</div>',
            unsafe_allow_html=True
        )
        for t in threats:
            st.markdown(
                f'<div style="font-family:Tajawal;font-size:0.86rem;'
                f'color:#CCC;padding:2px 0;direction:rtl">{t}</div>',
                unsafe_allow_html=True
            )

    # معلومات البحث
    rd = analysis.get("reached_depth", 0)
    at = analysis.get("analysis_time", "")
    st.markdown(
        f'<div style="margin-top:8px;font-family:Tajawal;font-size:0.78rem;'
        f'color:#555;direction:rtl">'
        f'🔬 عمق: <b style="color:#777">{rd}</b>'
        f'{" | ⏱ " + at if at else ""}'
        f'</div>',
        unsafe_allow_html=True
    )


# ════════════════════════════════════════════
# إدارة الحالة
# ════════════════════════════════════════════
def init_game(player_color, ai_color, depth, time_limit):
    clear_transposition_table()
    board = Board(variant="english")
    st.session_state.update({
        'board':           board,
        'player_color':    player_color,
        'ai_color':        ai_color,
        'depth':           depth,
        'time_limit':      time_limit,
        'move_history':    [],
        'game_over':       False,
        'winner':          None,
        'last_move':       "",
        'hint_move':       "",
        'ai_info':         "",
        'game_started':    True,
        'pending_ai':      board.turn == ai_color,
        'celebrated':      False,
        'analysis':        None,
        'show_analysis':   False,
        'move_count':      0,
        'captures_w':      0,
        'captures_b':      0,
        'threatened_sqs':  set(),
    })


def play_human_move():
    if st.session_state.get('game_over'):
        return
    board  = st.session_state['board']
    legal  = get_legal_moves(board)
    idx    = st.session_state.get("move_select", 0)
    if not (0 <= idx < len(legal)):
        st.warning("⚠️ اختر حركة صحيحة")
        return

    move   = legal[idx]
    ms     = fmt(move)
    is_cap = _is_capture(move)
    is_pr  = _is_promotion(move)
    board.push(move)

    mtype = "⚔️" if is_cap else ("👑" if is_pr else "➡️")
    st.session_state['move_history'].append(("👤", ms, mtype))
    st.session_state['last_move']     = ms
    st.session_state['hint_move']     = ""
    st.session_state['analysis']      = None
    st.session_state['show_analysis'] = False
    st.session_state['move_count']    = st.session_state.get('move_count', 0) + 1
    st.session_state['threatened_sqs'] = set()

    if is_cap:
        st.session_state['captures_w'] = st.session_state.get('captures_w', 0) + 1

    if is_game_over(board):
        st.session_state['game_over'] = True
        st.session_state['winner']    = get_winner(
            board, st.session_state['player_color'], st.session_state['ai_color']
        )
    else:
        st.session_state['pending_ai'] = True


def play_ai_move():
    board      = st.session_state['board']
    ai_color   = st.session_state['ai_color']
    depth      = st.session_state['depth']
    tlimit     = st.session_state.get('time_limit', 5.0)

    best, score, reached = find_best_move(
        board, ai_color, max_depth=depth, time_limit=tlimit
    )

    if best is not None:
        ms     = fmt(best)
        is_cap = _is_capture(best)
        is_pr  = _is_promotion(best)
        board.push(best)

        mtype = "⚔️" if is_cap else ("👑" if is_pr else "➡️")
        st.session_state['move_history'].append(("🤖", ms, mtype))
        st.session_state['last_move']  = ms
        st.session_state['hint_move']  = ""
        st.session_state['analysis']   = None
        st.session_state['move_count'] = st.session_state.get('move_count', 0) + 1
        if is_cap:
            st.session_state['captures_b'] = st.session_state.get('captures_b', 0) + 1

        tt = get_tt_stats()
        st.session_state['ai_info'] = (
            f"عمق: **{reached}** | "
            f"تقييم: **{score:+.0f}** | "
            f"TT: **{tt['size']:,}** | "
            f"إصابة: **{tt['hit_rate']}**"
        )

        # حساب القطع المهددة بعد حركة AI
        try:
            fen = get_board_fen(board)
            wp, bp = parse_fen_pieces(fen)
            from engine import (_build_square_sets,
                                _is_square_attacked_by_black,
                                _is_square_attacked_by_white)
            w_set, b_set, w_kings, b_kings = _build_square_sets(wp, bp)
            all_p = w_set | b_set
            ts    = set()
            pc    = st.session_state['player_color']
            if pc == WHITE:
                for sq, _ in wp:
                    if _is_square_attacked_by_black(
                            sq, w_set, b_set, b_kings, all_p):
                        ts.add(sq)
            else:
                for sq, _ in bp:
                    if _is_square_attacked_by_white(
                            sq, w_set, b_set, w_kings, all_p):
                        ts.add(sq)
            st.session_state['threatened_sqs'] = ts
        except Exception:
            st.session_state['threatened_sqs'] = set()

        if is_game_over(board):
            st.session_state['game_over'] = True
            st.session_state['winner']    = get_winner(
                board, st.session_state['player_color'], ai_color
            )
        else:
            st.session_state['pending_ai'] = False
    else:
        st.session_state['game_over']  = True
        st.session_state['winner']     = 'player'
        st.session_state['pending_ai'] = False


def undo_move():
    history = st.session_state.get('move_history', [])
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
        'board':           board,
        'move_history':    remaining,
        'game_over':       False,
        'winner':          None,
        'last_move':       last,
        'hint_move':       "",
        'pending_ai':      False,
        'celebrated':      False,
        'analysis':        None,
        'show_analysis':   False,
        'threatened_sqs':  set(),
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
            'font-size:1.45rem;font-weight:900;color:#FFD700;'
            'padding:8px 0 3px">♟️ داما AI</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="text-align:center;font-family:Tajawal;'
            'font-size:0.78rem;color:#666;padding-bottom:6px">'
            'الداما الكلاسيكية بذكاء اصطناعي متقدم</div>',
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
            index=0, key="color_radio"
        )

        difficulty = st.select_slider(
            "🎯 مستوى الصعوبة",
            options=["مبتدئ", "سهل", "متوسط", "صعب", "خبير", "عبقري"],
            value="متوسط", key="diff_slider"
        )

        depth_map = {
            "مبتدئ": 2, "سهل": 3, "متوسط": 6,
            "صعب": 10, "خبير": 14, "عبقري": 24,
        }
        time_map = {
            "مبتدئ": 1.0, "سهل": 2.0, "متوسط": 5.0,
            "صعب": 8.0, "خبير": 12.0, "عبقري": 20.0,
        }
        ch_depth = depth_map[difficulty]
        ch_time  = time_map[difficulty]

        st.markdown(
            f'<div style="font-family:Tajawal;font-size:0.8rem;'
            f'color:#666;direction:rtl;margin-top:-5px;margin-bottom:4px">'
            f'عمق {ch_depth} | وقت {ch_time:.0f}ث</div>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        bc1, bc2 = st.columns(2)
        with bc1:
            new_game = st.button("🆕 جديدة", use_container_width=True, key="btn_new")
        with bc2:
            hist_len = len(st.session_state.get('move_history', []))
            undo_ok  = st.session_state.get("game_started") and hist_len > 0
            undo_btn = st.button("↩️ تراجع", use_container_width=True,
                                  disabled=not undo_ok, key="btn_undo")

        if new_game:
            pc = WHITE if "أبيض" in color_choice else BLACK
            ac = BLACK if pc == WHITE else WHITE
            init_game(pc, ac, ch_depth, ch_time)
            st.rerun()

        if undo_btn and st.session_state.get("game_started"):
            undo_move()
            st.rerun()

        # ─── الإحصائيات ───
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
                f'</div></div>',
                unsafe_allow_html=True
            )

            tt = get_tt_stats()
            mc = st.session_state.get('move_count', 0)
            st.markdown(
                f'<div style="direction:rtl;font-family:Tajawal;margin:5px 0">'
                f'<span class="stat-pill sg">🎯 {mc} حركة</span>'
                f'<span class="stat-pill sb">💾 {tt["size"]:,}</span>'
                f'<span class="stat-pill so">📈 {tt["hit_rate"]}</span>'
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
            history = st.session_state.get('move_history', [])
            if history:
                st.markdown("---")
                st.markdown(
                    '<div class="section-header">📜 سجل الحركات</div>',
                    unsafe_allow_html=True
                )
                with st.container(height=230):
                    for idx, item in enumerate(history, 1):
                        who  = item[0]
                        mvs  = item[1]
                        mtyp = item[2] if len(item) > 2 else "➡️"
                        cls  = "history-row last-move" if idx == len(history) else "history-row"
                        st.markdown(
                            f'<div class="{cls}">'
                            f'<span class="h-num">{idx}</span>'
                            f'<span class="h-who">{who}</span>'
                            f'<span class="h-move">{mvs}</span>'
                            f'<span class="h-type">{mtyp}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

    # ════ المنطقة الرئيسية ════
    st.markdown(
        '<div class="main-title">♟️ داما الذكاء الاصطناعي</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-title">'
        'Minimax 24 | Alpha-Beta | TT 1M | LMR | Quiescence | '
        'Aspiration | Safety | Forks | Traps'
        '</div>',
        unsafe_allow_html=True
    )

    # ─── شاشة الترحيب ───
    if not st.session_state.get("game_started"):
        st.markdown("---")
        render_index()
        st.markdown(
            '<div style="font-family:Tajawal;font-size:1.05rem;font-weight:700;'
            'color:#FFD700;text-align:center;margin:14px 0 8px;direction:rtl">'
            '✨ مميزات البرنامج</div>',
            unsafe_allow_html=True
        )

        wc1, wc2 = st.columns(2)
        with wc1:
            st.markdown("""
            <div class="welcome-feature">
                <span class="wf-icon">🧠</span>
                <div>
                    <div class="wf-title">ذكاء اصطناعي عبقري</div>
                    <div class="wf-desc">Minimax عمق 24 مع Aspiration Windows وكتاب افتتاحيات</div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">🛡️</span>
                <div>
                    <div class="wf-title">تحليل السلامة الكامل</div>
                    <div class="wf-desc">يكشف القطع المهددة ويتجنب إعطاء الخصم الأكل</div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">🍴</span>
                <div>
                    <div class="wf-title">كشف الشوكات والفخاخ</div>
                    <div class="wf-desc">يبني مواقف تهدد عدة قطع في آنٍ واحد</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with wc2:
            st.markdown("""
            <div class="welcome-feature">
                <span class="wf-icon">⚡</span>
                <div>
                    <div class="wf-title">سرعة قصوى</div>
                    <div class="wf-desc">TT 1M + Zobrist + LMR + Counter Moves</div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">💡</span>
                <div>
                    <div class="wf-title">مساعد استراتيجي</div>
                    <div class="wf-desc">أفضل 5 حركات مع تقييم وشرح بالعربية</div>
                </div>
            </div>
            <div class="welcome-feature">
                <span class="wf-icon">🔬</span>
                <div>
                    <div class="wf-title">Quiescence Search</div>
                    <div class="wf-desc">يتابع الأكل عمق 10 لتجنب أفق البحث</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.info("👈 اضغط **'🆕 جديدة'** لبدء اللعب", icon="🎮")
        st.markdown(
            f'<div class="board-wrap">'
            f'{render_board(Board(variant="english"))}'
            f'</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # ─── دور AI ───
    if st.session_state.get('pending_ai') and not st.session_state.get('game_over'):
        with st.spinner("🤖 المحرك يحسب أفضل حركة..."):
            play_ai_move()
        st.rerun()

    board        = st.session_state['board']
    player_color = st.session_state['player_color']
    ai_color     = st.session_state['ai_color']
    threatened   = st.session_state.get('threatened_sqs', set())

    # ─── تخطيط ثنائي ───
    col_board, col_analysis = st.columns([1.05, 0.95])

    # ════ عمود الرقعة ════
    with col_board:
        if st.session_state.get('game_over'):
            winner = st.session_state.get('winner')
            if winner == 'player':
                st.markdown(
                    '<div class="status-box status-win">🎉 مبروك! فزت! 🏆</div>',
                    unsafe_allow_html=True
                )
                if not st.session_state.get('celebrated'):
                    st.balloons()
                    st.session_state['celebrated'] = True
            elif winner == 'ai':
                st.markdown(
                    '<div class="status-box status-lose">💻 الكمبيوتر فاز! حاول مجدداً 💪</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-box status-draw">🤝 تعادل!</div>',
                    unsafe_allow_html=True
                )
        else:
            if board.turn == player_color:
                n = len(get_legal_moves(board))
                warn = f" | ⚠️ {len(threatened)} قطعة مهددة!" if threatened else ""
                st.markdown(
                    f'<div class="status-box status-player">'
                    f'👤 دورك | {n} حركة{warn}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="status-box status-ai">🤖 دور المحرك...</div>',
                    unsafe_allow_html=True
                )

        # الرقعة مع تظليل التهديدات
        st.markdown(
            f'<div class="board-wrap">'
            f'{render_board(board, st.session_state.get("last_move",""), st.session_state.get("hint_move",""), threatened)}'
            f'</div>',
            unsafe_allow_html=True
        )

        # ─── أدوات اللاعب ───
        if not st.session_state.get('game_over') and board.turn == player_color:
            legal = get_legal_moves(board)
            if legal:
                labels = []
                for mv in legal:
                    lbl = fmt(mv)
                    if _is_capture(mv):
                        lbl += f"  ⚔️×{_capture_count(mv)}"
                    elif _is_promotion(mv):
                        lbl += "  👑"
                    labels.append(lbl)

                st.selectbox(
                    "🎯 اختر حركتك:",
                    range(len(labels)),
                    format_func=lambda i: f"[{i+1}] {labels[i]}",
                    key="move_select"
                )

                ac1, ac2, ac3 = st.columns(3)
                with ac1:
                    if st.button("▶️ العب!", use_container_width=True,
                                  type="primary", key="btn_play"):
                        play_human_move()
                        st.rerun()
                with ac2:
                    if st.button("↩️ تراجع", use_container_width=True,
                                  key="btn_undo2",
                                  disabled=len(st.session_state.get('move_history',[])) == 0):
                        undo_move()
                        st.rerun()
                with ac3:
                    if st.button("🔄 تحديث", use_container_width=True, key="btn_ref"):
                        st.rerun()

                hint_mv = st.session_state.get('hint_move', '')
                if hint_mv:
                    st.markdown(
                        f'<div class="hint-box">💡 <b>التلميح:</b> {hint_mv}</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.warning("⚠️ لا توجد حركات متاحة!")

    # ════ عمود التحليل ════
    with col_analysis:
        st.markdown(
            '<div class="section-header">🧠 لوحة التحليل الذكي</div>',
            unsafe_allow_html=True
        )

        if not st.session_state.get('game_over'):
            # شريط التقييم
            try:
                raw  = evaluate_position(board, player_color)
                pct  = eval_to_pct(raw)
                col  = "#00E676" if raw > 100 else ("#EF5350" if raw < -100 else "#FFF")
                st.markdown(
                    f'<div class="eval-container">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-family:Tajawal;font-size:0.8rem;color:#888">'
                    f'<span>🤖 AI</span>'
                    f'<span style="color:{col};font-weight:700">{raw:+.0f}</span>'
                    f'<span>👤 أنت</span></div>'
                    f'<div class="eval-bar-bg">'
                    f'<div class="eval-marker" style="left:{pct:.0f}%"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass

            # معلومات المرحلة
            try:
                fen2    = get_board_fen(board)
                wp2, bp2 = parse_fen_pieces(fen2)
                tot2    = len(wp2) + len(bp2)
                ph2     = _game_phase(tot2)
                phl2    = _phase_label(ph2)
                st.markdown(
                    f'<div style="font-family:Tajawal;font-size:0.8rem;'
                    f'color:#888;direction:rtl;margin:3px 0 7px">'
                    f'🎯 {phl2} | {tot2} قطعة</div>',
                    unsafe_allow_html=True
                )
            except Exception:
                pass

            # أزرار التحليل
            hint_depth = min(st.session_state.get('depth', 10), MAX_DEPTH)
            ab1, ab2 = st.columns(2)

            with ab1:
                if st.button(
                    f"🧠 تحليل عبقري (عمق {hint_depth})",
                    use_container_width=True,
                    help="تحليل عميق شامل",
                    key="btn_deep"
                ):
                    tlim = min(st.session_state.get('time_limit', 5.0) * 2, 18.0)
                    with st.spinner(f"🔬 تحليل عمق {hint_depth}..."):
                        t0 = time.time()
                        an = analyze_position(
                            board, player_color, ai_color,
                            depth=hint_depth, time_limit=tlim
                        )
                        an['analysis_time'] = f"{time.time()-t0:.1f}ث"
                        if an.get("best_move_str"):
                            st.session_state['hint_move'] = an["best_move_str"]
                        st.session_state['analysis']      = an
                        st.session_state['show_analysis'] = True
                    st.rerun()

            with ab2:
                if st.button(
                    "⚡ تلميح سريع",
                    use_container_width=True,
                    help="بعمق 5 - أسرع",
                    key="btn_quick"
                ):
                    with st.spinner("⚡ تلميح..."):
                        hm, _, _ = find_best_move(
                            board, player_color, max_depth=5, time_limit=2.0
                        )
                        if hm is not None:
                            hs = fmt(hm)
                            st.session_state['hint_move'] = hs
                            st.session_state['analysis'] = {
                                "best_move":      hm,
                                "best_move_str":  hs,
                                "score":          0,
                                "reached_depth":  5,
                                "top_moves": [{
                                    "move": hs, "score": 0,
                                    "label": "تلميح سريع ⚡",
                                    "is_capture": _is_capture(hm),
                                    "is_promotion": _is_promotion(hm),
                                    "cap_count": _capture_count(hm),
                                }],
                                "threats":       ["⚡ تحليل سريع"],
                                "phase":         "—",
                                "advantage":     "—",
                                "recommendation": f"💡 **التلميح: {hs}**",
                                "threatened_mine": 0,
                                "threatened_opp":  0,
                            }
                            st.session_state['show_analysis'] = True
                    st.rerun()

            # عرض التحليل
            if st.session_state.get('show_analysis') and st.session_state.get('analysis'):
                st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                render_analysis_panel(st.session_state['analysis'])
                st.markdown('</div>', unsafe_allow_html=True)

                if st.button("✖ إغلاق", use_container_width=True, key="btn_close"):
                    st.session_state['show_analysis'] = False
                    st.session_state['hint_move']     = ""
                    st.rerun()

            # نصيحة المرحلة
            elif not st.session_state.get('show_analysis'):
                try:
                    fen3    = get_board_fen(board)
                    wp3, bp3 = parse_fen_pieces(fen3)
                    ph3     = _game_phase(len(wp3) + len(bp3))
                    if ph3 >= 0.75:
                        tip = "📚 *الافتتاح: سيطر على المركز وحافظ على الصف الخلفي*"
                    elif ph3 >= 0.35:
                        tip = "⚔️ *الوسط: ابحث عن الشوكات وسلاسل الأكل المتعددة*"
                    else:
                        tip = "🎯 *النهاية: الملوك أقوى - سيطر على الزوايا المزدوجة*"
                    st.markdown(
                        f'<div class="hint-box">{tip}</div>',
                        unsafe_allow_html=True
                    )
                except Exception:
                    pass

        else:
            # ─── إحصائيات النهاية ───
            winner_f = st.session_state.get('winner')
            r_icon  = "🏆" if winner_f == 'player' else ("💻" if winner_f == 'ai' else "🤝")
            r_text  = ("أحسنت! انتصرت!" if winner_f == 'player' else
                       ("المحرك فاز!" if winner_f == 'ai' else "تعادل!"))
            r_color = "#FFD700" if winner_f == 'player' else ("#EF5350" if winner_f == 'ai' else "#64B5F6")

            total_m = len(st.session_state.get('move_history', []))
            cap_w   = st.session_state.get('captures_w', 0)
            cap_b   = st.session_state.get('captures_b', 0)
            tt_f    = get_tt_stats()

            st.markdown(
                f'<div class="game-over-stats">'
                f'<div style="text-align:center;font-family:Tajawal;'
                f'font-size:1.45rem;font-weight:900;color:{r_color};'
                f'margin-bottom:12px">{r_icon} {r_text}</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">إجمالي الحركات</div>'
                f'<div class="analysis-value">🎯 {total_m} حركة</div>'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">الأكل</div>'
                f'<div class="analysis-value">⬜ {cap_w} | ⬛ {cap_b}</div>'
                f'</div>'
                f'<div class="analysis-section">'
                f'<div class="analysis-label">إحصائيات المحرك</div>'
                f'<div class="analysis-value">'
                f'💾 {tt_f["size"]:,} موضع<br>'
                f'📈 {tt_f["hit_rate"]} معدل إصابة<br>'
                f'🔍 {tt_f["hits"]:,} إصابة / {tt_f["stores"]:,} تخزين'
                f'</div></div></div>',
                unsafe_allow_html=True
            )

            if st.button("🆕 لعبة جديدة", use_container_width=True,
                          type="primary", key="btn_new_end"):
                pc = WHITE if "أبيض" in st.session_state.get('color_radio', 'أبيض') else BLACK
                ac = BLACK if pc == WHITE else WHITE
                init_game(pc, ac, ch_depth, ch_time)
                st.rerun()


if __name__ == "__main__":
    main()
