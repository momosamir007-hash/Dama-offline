"""
لعبة الداما الكلاسيكية (8x8 - 12 قطعة) بواجهة رسومية - Streamlit
نسخة محسّنة مع:
- إصلاح celebrated flag
- تحسين RTL/LTR
- رسالة خطأ واضحة عند عدم وجود المكتبة
- تحسين تجربة المستخدم
"""
import re
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
    parse_fen_pieces,
    DRAUGHTS_AVAILABLE,
    get_legal_moves,
    get_board_fen,
    format_move_to_string,
    clear_transposition_table,
)

st.set_page_config(
    page_title="لعبة الداما | Checkers AI",
    page_icon="🎮",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ════════════════════════════════════════════
# CSS المحسّن
# ════════════════════════════════════════════
def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');

        /* ─── العناوين ─── */
        .main-title {
            text-align: center;
            font-family: 'Tajawal', sans-serif;
            font-size: 2.4rem;
            font-weight: 900;
            background: linear-gradient(135deg, #FFD700, #FF8C00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0;
            padding: 10px 0;
        }
        .sub-title {
            text-align: center;
            font-family: 'Tajawal', sans-serif;
            color: #888;
            font-size: 1rem;
            margin-top: -10px;
            margin-bottom: 20px;
        }

        /* ─── الرقعة ─── */
        .board-container {
            display: flex;
            justify-content: center;
            padding: 10px 0;
        }

        /* ─── صناديق الحالة ─── */
        .status-box {
            text-align: center;
            padding: 12px 20px;
            border-radius: 10px;
            font-family: 'Tajawal', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            margin: 10px auto;
            max-width: 500px;
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
            font-size: 1.3rem;
        }
        .status-lose {
            background: linear-gradient(135deg, #424242, #616161);
            color: #FFF;
            border: 2px solid #9E9E9E;
        }
        .status-draw {
            background: linear-gradient(135deg, #0D47A1, #1565C0);
            color: #FFF;
            border: 2px solid #42A5F5;
        }

        /* ─── بطاقات المعلومات ─── */
        .info-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            font-family: 'Tajawal', sans-serif;
            direction: rtl;
        }
        .piece-count {
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 8px;
        }
        .piece-side {
            text-align: center;
            font-family: 'Tajawal', sans-serif;
        }
        .piece-num {
            font-size: 1.8rem;
            font-weight: 900;
        }

        /* ─── سجل الحركات ─── */
        .history-item {
            font-family: 'Tajawal', monospace;
            padding: 3px 0;
            font-size: 0.9rem;
            direction: rtl;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .history-item:last-child {
            border-bottom: none;
            font-weight: 700;
            color: #FFD700;
        }

        /* ─── شريط التقدم الزمني ─── */
        .eval-bar {
            height: 8px;
            border-radius: 4px;
            background: linear-gradient(to right, #EF5350, #fff, #4CAF50);
            margin: 4px 0;
        }

        /* ─── تحسين الأزرار ─── */
        .stButton > button {
            font-family: 'Tajawal', sans-serif;
            font-weight: 700;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }

        /* ─── تحسين selectbox ─── */
        .stSelectbox label {
            font-family: 'Tajawal', sans-serif;
            direction: rtl;
        }
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# دوال مساعدة
# ════════════════════════════════════════════
def format_move(move) -> str:
    """تنسيق الحركة للعرض"""
    result = format_move_to_string(move)
    return result if result and result != "?" else "حركة"


def count_pieces(board) -> tuple:
    """حساب القطع لكل جانب"""
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
    """تحديد الفائز"""
    if not is_game_over(board):
        return None

    w_men, w_kings, b_men, b_kings = count_pieces(board)
    w_total = w_men + w_kings
    b_total = b_men + b_kings

    if w_total == 0 and b_total == 0:
        return 'draw'
    if w_total == 0:
        return 'ai' if player_color == WHITE else 'player'
    if b_total == 0:
        return 'ai' if player_color == BLACK else 'player'

    # من لا يملك حركات يخسر
    if board.turn == ai_color:
        return 'player'
    return 'ai'


def get_eval_percentage(board, player_color, ai_color) -> float:
    """
    حساب نسبة تفوق اللاعب (0-100).
    50 = تعادل, >50 = اللاعب أفضل
    """
    try:
        score = evaluate_position(board, ai_color)
        # تحويل النقاط إلى نسبة (0-100)
        normalized = 50 + (score / 10)
        # اللاعب معكوس AI
        player_pct = 100 - max(0, min(100, normalized))
        return player_pct
    except Exception:
        return 50.0


# ════════════════════════════════════════════
# رسم الرقعة بـ SVG
# ════════════════════════════════════════════
def _draw_arrow(svg_parts, move_str, sq_coords,
                color, marker, dash, opacity):
    """رسم سهم على الرقعة"""
    if not move_str:
        return
    nums = [int(n) for n in re.findall(r'\d+', move_str)]
    valid = [n for n in nums if n in sq_coords]
    if len(valid) < 2:
        return
    pts = " ".join(
        f"{sq_coords[n][0]},{sq_coords[n][1]}" for n in valid
    )
    svg_parts.append(
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{color}" stroke-width="5" {dash} '
        f'marker-end="url(#{marker})" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{opacity}"/>'
    )


def render_board_svg(board, last_move_str="", hint_move_str="") -> str:
    """رسم رقعة الداما كـ SVG"""
    CELL      = 64
    BOARD_SZ  = CELL * 8
    MARGIN    = 28
    TOTAL     = BOARD_SZ + MARGIN * 2
    PIECE_R   = 25
    INNER_R   = 17

    # الألوان
    LIGHT_SQ    = "#F0D9B5"
    DARK_SQ     = "#B58863"
    WHITE_FILL  = "url(#wg)"
    BLACK_FILL  = "url(#bg)"
    WHITE_STR   = "#C8A96E"
    BLACK_STR   = "#111111"
    CROWN_W     = "#B8860B"
    CROWN_B     = "#FFD700"
    FRAME_C     = "#5D3A1A"
    NUM_C       = "rgba(255,255,255,0.30)"
    HINT_SQ_C   = "rgba(0,255,0,0.15)"
    LAST_SQ_C   = "rgba(255,255,50,0.30)"

    fen = get_board_fen(board)
    white_pieces, black_pieces = parse_fen_pieces(fen)

    piece_map = {}
    for sq, is_king in white_pieces:
        piece_map[sq] = ('white', is_king)
    for sq, is_king in black_pieces:
        piece_map[sq] = ('black', is_king)

    # مربعات آخر حركة
    highlight_last = set()
    if last_move_str:
        for n in re.findall(r'\d+', last_move_str):
            try:
                highlight_last.add(int(n))
            except ValueError:
                pass

    # مربعات التلميح
    highlight_hint = set()
    if hint_move_str:
        for n in re.findall(r'\d+', hint_move_str):
            try:
                highlight_hint.add(int(n))
            except ValueError:
                pass

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {TOTAL} {TOTAL}" width="100%" '
        f'style="max-width:{TOTAL}px;display:block;margin:0 auto;">'
    ]

    # ─── التعريفات ───
    svg.append(f"""<defs>
        <filter id="ps" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="1" dy="2" stdDeviation="2.5"
                flood-opacity="0.55"/>
        </filter>
        <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <radialGradient id="wg" cx="38%" cy="32%" r="58%">
            <stop offset="0%"   stop-color="#FFFFFF"/>
            <stop offset="60%"  stop-color="#EDD9A3"/>
            <stop offset="100%" stop-color="#C8A96E"/>
        </radialGradient>
        <radialGradient id="bg" cx="38%" cy="32%" r="58%">
            <stop offset="0%"   stop-color="#666666"/>
            <stop offset="60%"  stop-color="#2A2A2A"/>
            <stop offset="100%" stop-color="#111111"/>
        </radialGradient>
        <radialGradient id="sq_light" cx="50%" cy="50%" r="70%">
            <stop offset="0%"   stop-color="#F8E8C8"/>
            <stop offset="100%" stop-color="#E8C990"/>
        </radialGradient>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
                markerWidth="5" markerHeight="5"
                orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF4500"/>
        </marker>
        <marker id="hint-arrow" viewBox="0 0 10 10" refX="8" refY="5"
                markerWidth="5" markerHeight="5"
                orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#00CC44"/>
        </marker>
    </defs>""")

    # ─── الإطار ───
    svg.append(
        f'<rect x="0" y="0" width="{TOTAL}" height="{TOTAL}" '
        f'rx="8" fill="{FRAME_C}"/>'
    )
    svg.append(
        f'<rect x="{MARGIN - 4}" y="{MARGIN - 4}" '
        f'width="{BOARD_SZ + 8}" height="{BOARD_SZ + 8}" '
        f'rx="4" fill="#3D2010" stroke="#8B5E3C" stroke-width="1"/>'
    )

    # ─── الأحرف والأرقام ───
    for i in range(8):
        cx = MARGIN + i * CELL + CELL // 2
        svg.append(
            f'<text x="{cx}" y="{MARGIN - 9}" text-anchor="middle" '
            f'font-size="13" fill="#D4A76A" font-family="monospace" '
            f'font-weight="bold">{chr(65 + i)}</text>'
        )
        cy = MARGIN + i * CELL + CELL // 2 + 5
        svg.append(
            f'<text x="{MARGIN - 12}" y="{cy}" text-anchor="middle" '
            f'font-size="13" fill="#D4A76A" font-family="monospace" '
            f'font-weight="bold">{8 - i}</text>'
        )

    # ─── المربعات والقطع ───
    sq_num = 0
    sq_coords = {}

    for r in range(8):
        for c in range(8):
            x = MARGIN + c * CELL
            y = MARGIN + r * CELL
            is_dark = (r + c) % 2 == 1

            # لون المربع
            fill = DARK_SQ if is_dark else LIGHT_SQ
            svg.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" '
                f'height="{CELL}" fill="{fill}"/>'
            )

            if is_dark:
                sq_num += 1
                cx_p = x + CELL // 2
                cy_p = y + CELL // 2
                sq_coords[sq_num] = (cx_p, cy_p)

                # تظليل آخر حركة
                if sq_num in highlight_last:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" '
                        f'height="{CELL}" fill="{LAST_SQ_C}"/>'
                    )

                # تظليل التلميح
                if sq_num in highlight_hint:
                    svg.append(
                        f'<rect x="{x}" y="{y}" width="{CELL}" '
                        f'height="{CELL}" fill="{HINT_SQ_C}"/>'
                    )

                # رقم المربع
                svg.append(
                    f'<text x="{x + 4}" y="{y + 14}" font-size="10" '
                    f'fill="{NUM_C}" font-family="monospace">{sq_num}</text>'
                )

                # رسم القطعة
                if sq_num in piece_map:
                    color, is_king = piece_map[sq_num]
                    grad  = WHITE_FILL if color == 'white' else BLACK_FILL
                    s_clr = WHITE_STR  if color == 'white' else BLACK_STR
                    inner = "#D4B896"  if color == 'white' else "#333333"

                    # ظل القطعة
                    svg.append(
                        f'<circle cx="{cx_p + 1}" cy="{cy_p + 2}" '
                        f'r="{PIECE_R}" fill="rgba(0,0,0,0.35)"/>'
                    )
                    # القطعة الرئيسية
                    svg.append(
                        f'<circle cx="{cx_p}" cy="{cy_p}" r="{PIECE_R}" '
                        f'fill="{grad}" stroke="{s_clr}" stroke-width="2" '
                        f'filter="url(#ps)"/>'
                    )
                    # الحلقة الداخلية
                    svg.append(
                        f'<circle cx="{cx_p}" cy="{cy_p}" r="{INNER_R}" '
                        f'fill="none" stroke="{inner}" stroke-width="1.5" '
                        f'opacity="0.55"/>'
                    )
                    # رمز الملك
                    if is_king:
                        crown = CROWN_W if color == 'white' else CROWN_B
                        svg.append(
                            f'<text x="{cx_p}" y="{cy_p + 8}" '
                            f'text-anchor="middle" font-size="22" '
                            f'fill="{crown}" font-weight="bold" '
                            f'filter="url(#glow)">♛</text>'
                        )

    # ─── حدود الرقعة ───
    svg.append(
        f'<rect x="{MARGIN}" y="{MARGIN}" width="{BOARD_SZ}" '
        f'height="{BOARD_SZ}" fill="none" stroke="{FRAME_C}" '
        f'stroke-width="2"/>'
    )

    # ─── الأسهم ───
    _draw_arrow(svg, last_move_str, sq_coords,
                "#FF4500", "arrow", "", "0.80")
    _draw_arrow(svg, hint_move_str, sq_coords,
                "#00CC44", "hint-arrow",
                'stroke-dasharray="10,6"', "0.90")

    svg.append('</svg>')
    return '\n'.join(svg)


# ════════════════════════════════════════════
# إدارة حالة اللعبة
# ════════════════════════════════════════════
def init_game(player_color, ai_color, depth):
    """تهيئة لعبة جديدة"""
    clear_transposition_table()

    board = Board(variant="english")
    st.session_state.update({
        'board':        board,
        'player_color': player_color,
        'ai_color':     ai_color,
        'depth':        depth,
        'move_history': [],
        'game_over':    False,
        'winner':       None,
        'last_move':    "",
        'hint_move':    "",
        'ai_info':      "",
        'game_started': True,
        'pending_ai':   board.turn == ai_color,
        'celebrated':   False,   # ← إصلاح: يُعاد تعيينها دائماً
        'move_count':   0,
    })


def play_human_move():
    """تنفيذ حركة اللاعب"""
    if st.session_state.game_over:
        return

    board      = st.session_state.board
    legal_mvs  = get_legal_moves(board)
    idx        = st.session_state.get("move_select", 0)

    if not (0 <= idx < len(legal_mvs)):
        st.warning("اختر حركة صحيحة")
        return

    move     = legal_mvs[idx]
    move_str = format_move(move)
    board.push(move)

    st.session_state.move_history.append(("👤", move_str))
    st.session_state.last_move  = move_str
    st.session_state.hint_move  = ""
    st.session_state.move_count = st.session_state.get('move_count', 0) + 1

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
    """تنفيذ حركة الذكاء الاصطناعي"""
    board     = st.session_state.board
    ai_color  = st.session_state.ai_color
    depth     = st.session_state.depth

    best_move, score, reached = find_best_move(
        board, ai_color,
        max_depth=depth,
        time_limit=4.0
    )

    if best_move:
        move_str = format_move(best_move)
        board.push(best_move)

        st.session_state.move_history.append(("🤖", move_str))
        st.session_state.last_move  = move_str
        st.session_state.hint_move  = ""
        st.session_state.move_count = st.session_state.get('move_count', 0) + 1
        st.session_state.ai_info    = (
            f"عمق البحث: {reached} | "
            f"التقييم: {score:+.0f}"
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
        # لا حركات للـ AI → اللاعب فاز
        st.session_state.game_over   = True
        st.session_state.winner      = 'player'
        st.session_state.pending_ai  = False


def undo_move():
    """
    التراجع عن حركتين (حركة اللاعب + حركة AI).
    نظراً لعدم دعم board.pop() نعيد بناء الرقعة من الصفر.
    """
    history = st.session_state.move_history
    if not history:
        return

    moves_to_remove = min(2, len(history))
    remaining = history[:-moves_to_remove]

    # إعادة بناء الرقعة
    board = Board(variant="english")
    for _, mv_str in remaining:
        legal = get_legal_moves(board)
        matched = None
        for lm in legal:
            if format_move_to_string(lm) == mv_str or str(lm) == mv_str:
                matched = lm
                break
        if matched:
            board.push(matched)

    st.session_state.update({
        'board':       board,
        'move_history': remaining,
        'game_over':   False,
        'winner':      None,
        'last_move':   remaining[-1][1] if remaining else "",
        'hint_move':   "",
        'pending_ai':  False,
        'celebrated':  False,
    })


# ════════════════════════════════════════════
# الواجهة الرئيسية
# ════════════════════════════════════════════
def main():
    inject_css()

    # ─── فحص المكتبة ───
    if not DRAUGHTS_OK or not DRAUGHTS_AVAILABLE:
        st.error("❌ مكتبة `pydraughts` غير مثبتة!")
        st.info("قم بتثبيتها بالأمر:")
        st.code("pip install pydraughts", language="bash")
        st.markdown("ثم أعد تشغيل التطبيق.")
        st.stop()

    # ─── العنوان ───
    st.markdown(
        '<div class="main-title">♟️ لعبة الداما الكلاسيكية</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-title">8×8 | 12 قطعة | محرك Minimax + Alpha-Beta</div>',
        unsafe_allow_html=True
    )

    # ════ الشريط الجانبي ════
    with st.sidebar:
        st.markdown("## ⚙️ إعدادات اللعبة")

        color_choice = st.radio(
            "🎨 اختر لونك:",
            ["⬜ أبيض (تبدأ أنت)", "⬛ أسود (يبدأ الكمبيوتر)"],
            index=0
        )

        difficulty = st.select_slider(
            "🎯 مستوى الصعوبة:",
            options=["سهل", "متوسط", "صعب", "خبير"],
            value="متوسط"
        )
        depth_map  = {"سهل": 2, "متوسط": 4, "صعب": 6, "خبير": 8}
        depth      = depth_map[difficulty]

        st.markdown("---")

        col_new, col_undo = st.columns(2)
        with col_new:
            new_game = st.button(
                "🆕 لعبة جديدة",
                use_container_width=True
            )
        with col_undo:
            undo = st.button(
                "↩️ تراجع",
                use_container_width=True,
                disabled=not (
                    st.session_state.get("game_started") and
                    len(st.session_state.get("move_history", [])) > 0
                )
            )

        if new_game:
            p_color = WHITE if "أبيض" in color_choice else BLACK
            a_color = BLACK if "أبيض" in color_choice else WHITE
            init_game(p_color, a_color, depth)
            st.rerun()

        if undo and st.session_state.get("game_started"):
            undo_move()
            st.rerun()

        # ─── الإحصائيات ───
        if st.session_state.get("game_started"):
            board = st.session_state.board
            w_men, w_kings, b_men, b_kings = count_pieces(board)
            w_total = w_men + w_kings
            b_total = b_men + b_kings

            st.markdown("---")
            st.markdown("### 📊 إحصائيات")

            king_w = f"+ {w_kings}👑" if w_kings else ""
            king_b = f"+ {b_kings}👑" if b_kings else ""

            st.markdown(f"""
            <div class="info-card">
                <div class="piece-count">
                    <div class="piece-side">
                        <div style="font-size:1.5rem">⬜</div>
                        <div class="piece-num">{w_total}</div>
                        <div style="font-size:0.8rem">
                            {w_men} قطعة {king_w}
                        </div>
                    </div>
                    <div style="font-size:1.5rem;color:#666">⚔️</div>
                    <div class="piece-side">
                        <div style="font-size:1.5rem">⬛</div>
                        <div class="piece-num">{b_total}</div>
                        <div style="font-size:0.8rem">
                            {b_men} قطعة {king_b}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # عدد الحركات
            moves = len(st.session_state.move_history)
            st.markdown(f"📝 عدد الحركات: **{moves}**")

            # معلومات AI
            if st.session_state.ai_info:
                st.markdown(f"🧠 {st.session_state.ai_info}")

            # شريط التقييم
            if not st.session_state.game_over:
                pct = get_eval_percentage(
                    board,
                    st.session_state.player_color,
                    st.session_state.ai_color
                )
                st.markdown(f"⚖️ توازن: **{pct:.0f}%** للاعب")
                st.progress(int(pct))

            # ─── سجل الحركات ───
            if st.session_state.move_history:
                st.markdown("---")
                st.markdown("### 📜 سجل الحركات")
                with st.container(height=220):
                    for i, (who, mv) in enumerate(
                        st.session_state.move_history, 1
                    ):
                        st.markdown(
                            f'<div class="history-item">'
                            f'{i}. {who} {mv}</div>',
                            unsafe_allow_html=True
                        )

    # ════ المنطقة الرئيسية ════

    # ─── شاشة الترحيب ───
    if not st.session_state.get("game_started"):
        st.markdown("---")
        st.info(
            "👈 اضغط **'لعبة جديدة'** في الشريط الجانبي للبدء",
            icon="🎮"
        )
        demo = Board(variant="english")
        st.markdown(
            f'<div class="board-container">'
            f'{render_board_svg(demo)}</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # ─── دور الـ AI ───
    if st.session_state.pending_ai and not st.session_state.game_over:
        with st.spinner("🤖 الكمبيوتر يفكر..."):
            play_ai_move()
        st.rerun()

    board        = st.session_state.board
    player_color = st.session_state.player_color
    ai_color     = st.session_state.ai_color

    # ─── رسالة الحالة ───
    if st.session_state.game_over:
        winner = st.session_state.winner
        if winner == 'player':
            st.markdown(
                '<div class="status-box status-win">'
                '🎉 مبروك! لقد فزت! 🏆</div>',
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
                '<div class="status-box status-draw">'
                '🤝 تعادل!</div>',
                unsafe_allow_html=True
            )
    else:
        if board.turn == player_color:
            legal_count = len(get_legal_moves(board))
            st.markdown(
                f'<div class="status-box status-player">'
                f'👤 دورك الآن | {legal_count} حركة متاحة</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="status-box status-ai">'
                '🤖 دور الكمبيوتر...</div>',
                unsafe_allow_html=True
            )

    # ─── الرقعة ───
    board_svg = render_board_svg(
        board,
        st.session_state.get("last_move", ""),
        st.session_state.get("hint_move", "")
    )
    st.markdown(
        f'<div class="board-container">{board_svg}</div>',
        unsafe_allow_html=True
    )

    # ─── أدوات اللاعب ───
    if not st.session_state.game_over and board.turn == player_color:
        legal_moves = get_legal_moves(board)
        if legal_moves:
            st.markdown("---")
            move_labels = [format_move(m) for m in legal_moves]

            col_sel, col_btn, col_hint = st.columns([2.5, 1, 1])

            with col_sel:
                st.selectbox(
                    "🎯 اختر حركتك:",
                    range(len(move_labels)),
                    format_func=lambda i: f"[{i+1}] {move_labels[i]}",
                    key="move_select"
                )
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(
                    "▶️ العب!",
                    use_container_width=True,
                    type="primary"
                ):
                    play_human_move()
                    st.rerun()

            with col_hint:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💡 تلميح", use_container_width=True):
                    with st.spinner("جاري تحليل الرقعة..."):
                        hint_mv, h_score, _ = find_best_move(
                            board, player_color,
                            max_depth=4, time_limit=2.0
                        )
                    if hint_mv:
                        st.session_state.hint_move = format_move(hint_mv)
                        st.rerun()

        else:
            st.warning("⚠️ لا توجد حركات متاحة!")


if __name__ == "__main__":
    main()
