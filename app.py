"""
لعبة الداما الكلاسيكية (8x8 - 12 قطعة) بواجهة رسومية - Streamlit
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
)

st.set_page_config(
    page_title="لعبة الداما | Checkers AI",
    page_icon="🎮",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ════════════════════════════════════════════
# دوال مساعدة
# ════════════════════════════════════════════
def format_move(move):
    result = format_move_to_string(move)
    return result if result else "حركة"


def count_pieces(board):
    fen = get_board_fen(board)
    wp, bp = parse_fen_pieces(fen)
    w_men = sum(1 for _, k in wp if not k)
    w_kings = sum(1 for _, k in wp if k)
    b_men = sum(1 for _, k in bp if not k)
    b_kings = sum(1 for _, k in bp if k)
    return w_men, w_kings, b_men, b_kings


def is_game_over(board):
    try:
        if hasattr(board, 'is_over') and board.is_over():
            return True
    except Exception:
        pass
    return len(get_legal_moves(board)) == 0


def get_winner(board, player_color, ai_color):
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

    if board.turn == ai_color:
        return 'player'
    else:
        return 'ai'


# ════════════════════════════════════════════
# رسم الرقعة بـ SVG
# ════════════════════════════════════════════
def _draw_arrow(svg_parts, move_str, sq_coords, color, marker, dash, opacity):
    if not move_str:
        return
    nums = [int(n) for n in re.findall(r'\d+', move_str)]
    valid = [n for n in nums if n in sq_coords]
    if len(valid) < 2:
        return
    pts = " ".join(f"{sq_coords[n][0]},{sq_coords[n][1]}" for n in valid)
    svg_parts.append(
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{color}" stroke-width="5" {dash} '
        f'marker-end="url(#{marker})" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{opacity}"/>'
    )


def render_board_svg(board, last_move_str="", hint_move_str=""):
    CELL = 60
    BOARD_SIZE = CELL * 8
    MARGIN = 24
    TOTAL = BOARD_SIZE + MARGIN * 2
    PIECE_R = 23
    INNER_R = 16

    LIGHT_SQ = "#F0D9B5"
    DARK_SQ = "#B58863"
    WHITE_STROKE = "#C8A96E"
    BLACK_STROKE = "#111111"
    CROWN_W = "#B8860B"
    CROWN_B = "#FFD700"
    FRAME_COLOR = "#5D3A1A"
    NUM_COLOR = "rgba(255,255,255,0.35)"

    fen = get_board_fen(board)
    white_pieces, black_pieces = parse_fen_pieces(fen)
    piece_map = {}
    for sq, is_king in white_pieces:
        piece_map[sq] = ('white', is_king)
    for sq, is_king in black_pieces:
        piece_map[sq] = ('black', is_king)

    highlight_squares = set()
    if last_move_str:
        for n in re.findall(r'\d+', last_move_str):
            try:
                highlight_squares.add(int(n))
            except ValueError:
                pass

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {TOTAL} {TOTAL}" width="100%" '
        f'style="max-width:{TOTAL}px;display:block;margin:0 auto;">'
    ]

    svg.append("""<defs>
        <filter id="ps" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.5"/>
        </filter>
        <radialGradient id="wg" cx="40%" cy="35%" r="55%">
            <stop offset="0%" stop-color="#FFFFFF"/>
            <stop offset="100%" stop-color="#E8D5B0"/>
        </radialGradient>
        <radialGradient id="bg" cx="40%" cy="35%" r="55%">
            <stop offset="0%" stop-color="#555555"/>
            <stop offset="100%" stop-color="#1A1A1A"/>
        </radialGradient>
        <marker id="arrow" viewBox="0 0 10 10" refX="7" refY="5"
                markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF4500"/>
        </marker>
        <marker id="hint-arrow" viewBox="0 0 10 10" refX="7" refY="5"
                markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#00FF00"/>
        </marker>
    </defs>""")

    svg.append(f'<rect x="0" y="0" width="{TOTAL}" height="{TOTAL}" rx="6" fill="{FRAME_COLOR}"/>')

    for i in range(8):
        cx = MARGIN + i * CELL + CELL // 2
        svg.append(f'<text x="{cx}" y="{MARGIN - 7}" text-anchor="middle" font-size="12" fill="#D4A76A" font-family="monospace">{chr(65 + i)}</text>')
        cy = MARGIN + i * CELL + CELL // 2 + 4
        svg.append(f'<text x="{MARGIN - 10}" y="{cy}" text-anchor="middle" font-size="12" fill="#D4A76A" font-family="monospace">{8 - i}</text>')

    sq_num = 0
    sq_coords = {}

    for r in range(8):
        for c in range(8):
            x = MARGIN + c * CELL
            y = MARGIN + r * CELL
            is_dark = (r + c) % 2 == 1
            fill = DARK_SQ if is_dark else LIGHT_SQ
            svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{fill}"/>')

            if is_dark:
                sq_num += 1
                cx_p = x + CELL // 2
                cy_p = y + CELL // 2
                sq_coords[sq_num] = (cx_p, cy_p)

                if sq_num in highlight_squares:
                    svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="rgba(255,255,50,0.3)"/>')

                svg.append(f'<text x="{x + 4}" y="{y + 14}" font-size="10" fill="{NUM_COLOR}" font-family="monospace">{sq_num}</text>')

                if sq_num in piece_map:
                    color, is_king = piece_map[sq_num]
                    grad = "url(#wg)" if color == 'white' else "url(#bg)"
                    stroke = WHITE_STROKE if color == 'white' else BLACK_STROKE
                    inner_s = "#D4B896" if color == 'white' else "#333333"

                    svg.append(f'<circle cx="{cx_p}" cy="{cy_p}" r="{PIECE_R}" fill="{grad}" stroke="{stroke}" stroke-width="2" filter="url(#ps)"/>')
                    svg.append(f'<circle cx="{cx_p}" cy="{cy_p}" r="{INNER_R}" fill="none" stroke="{inner_s}" stroke-width="1.5" opacity="0.6"/>')

                    if is_king:
                        crown_c = CROWN_W if color == 'white' else CROWN_B
                        svg.append(f'<text x="{cx_p}" y="{cy_p + 7}" text-anchor="middle" font-size="20" fill="{crown_c}" font-weight="bold">♛</text>')

    svg.append(f'<rect x="{MARGIN}" y="{MARGIN}" width="{BOARD_SIZE}" height="{BOARD_SIZE}" fill="none" stroke="{FRAME_COLOR}" stroke-width="2"/>')

    _draw_arrow(svg, last_move_str, sq_coords, "#FF4500", "arrow", "", "0.85")
    _draw_arrow(svg, hint_move_str, sq_coords, "#00FF00", "hint-arrow", 'stroke-dasharray="8,8"', "0.9")

    svg.append('</svg>')
    return '\n'.join(svg)


# ════════════════════════════════════════════
# إدارة حالة اللعبة
# ════════════════════════════════════════════
def init_game(player_color, ai_color, depth):
    board = Board(variant="english")
    st.session_state.board = board
    st.session_state.player_color = player_color
    st.session_state.ai_color = ai_color
    st.session_state.depth = depth
    st.session_state.move_history = []
    st.session_state.game_over = False
    st.session_state.winner = None
    st.session_state.last_move = ""
    st.session_state.hint_move = ""
    st.session_state.ai_info = ""
    st.session_state.game_started = True
    st.session_state.pending_ai = False
    st.session_state.celebrated = False

    if board.turn == ai_color:
        st.session_state.pending_ai = True


def play_human_move():
    if st.session_state.game_over:
        return
    board = st.session_state.board
    legal_moves = get_legal_moves(board)
    idx = st.session_state.get("move_select", 0)

    if not (0 <= idx < len(legal_moves)):
        return

    move = legal_moves[idx]
    move_str = format_move(move)
    board.push(move)

    st.session_state.move_history.append(("👤", move_str))
    st.session_state.last_move = move_str
    st.session_state.hint_move = ""

    if is_game_over(board):
        st.session_state.game_over = True
        st.session_state.winner = get_winner(board, st.session_state.player_color, st.session_state.ai_color)
    else:
        st.session_state.pending_ai = True


def play_ai_move():
    board = st.session_state.board
    ai_color = st.session_state.ai_color
    depth = st.session_state.depth

    best_move, score, reached = find_best_move(board, ai_color, max_depth=depth, time_limit=3.5)

    if best_move:
        move_str = format_move(best_move)
        board.push(best_move)
        st.session_state.move_history.append(("🤖", move_str))
        st.session_state.last_move = move_str
        st.session_state.hint_move = ""
        st.session_state.ai_info = f"العمق: {reached} | التقييم: {score:+.1f}"

        if is_game_over(board):
            st.session_state.game_over = True
            st.session_state.winner = get_winner(board, st.session_state.player_color, ai_color)
        else:
            st.session_state.pending_ai = False
    else:
        st.session_state.game_over = True
        st.session_state.winner = 'player'
        st.session_state.pending_ai = False


def undo_move():
    board = st.session_state.board
    history = st.session_state.move_history
    moves_to_undo = min(2, len(history))
    if moves_to_undo == 0:
        return
    for _ in range(moves_to_undo):
        try:
            board.pop()
            history.pop()
        except Exception:
            break
    st.session_state.game_over = False
    st.session_state.winner = None
    st.session_state.last_move = ""
    st.session_state.hint_move = ""
    st.session_state.pending_ai = False


def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
        .main-title{text-align:center;font-family:'Tajawal',sans-serif;font-size:2.4rem;font-weight:900;background:linear-gradient(135deg,#FFD700,#FF8C00);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0;padding:10px 0}
        .sub-title{text-align:center;font-family:'Tajawal',sans-serif;color:#888;font-size:1rem;margin-top:-10px;margin-bottom:20px}
        .board-container{display:flex;justify-content:center;padding:10px 0}
        .status-box{text-align:center;padding:12px 20px;border-radius:10px;font-family:'Tajawal',sans-serif;font-size:1.1rem;font-weight:700;margin:10px auto;max-width:500px}
        .status-player{background:linear-gradient(135deg,#1B5E20,#2E7D32);color:#FFF;border:2px solid #4CAF50}
        .status-ai{background:linear-gradient(135deg,#B71C1C,#C62828);color:#FFF;border:2px solid #EF5350}
        .status-win{background:linear-gradient(135deg,#F9A825,#FFD54F);color:#1A1A1A;border:2px solid #FFD700;font-size:1.3rem}
        .status-lose{background:linear-gradient(135deg,#424242,#616161);color:#FFF;border:2px solid #9E9E9E}
        .status-draw{background:linear-gradient(135deg,#0D47A1,#1565C0);color:#FFF;border:2px solid #42A5F5}
        .info-card{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;margin:8px 0;font-family:'Tajawal',sans-serif}
        .piece-count{display:flex;justify-content:space-around;align-items:center;padding:8px}
        .piece-side{text-align:center;font-family:'Tajawal',sans-serif}
        .piece-num{font-size:1.8rem;font-weight:900}
        .history-item{font-family:'Tajawal',monospace;padding:2px 0;font-size:0.9rem}
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════
# الواجهة الرئيسية
# ════════════════════════════════════════════
def main():
    inject_css()

    if not DRAUGHTS_OK or not DRAUGHTS_AVAILABLE:
        st.error("❌ مكتبة `pydraughts` غير مثبتة!")
        st.code("pip install pydraughts", language="bash")
        st.stop()

    st.markdown('<div class="main-title">♟️ لعبة الداما الكلاسيكية</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">8×8 | 12 قطعة | محرك Minimax</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## ⚙️ إعدادات اللعبة")
        color_choice = st.radio("🎨 اختر لونك:", ["⬜ أبيض (تبدأ أنت)", "⬛ أسود (يبدأ الكمبيوتر)"], index=0)
        difficulty = st.select_slider("🎯 مستوى الصعوبة:", options=["سهل", "متوسط", "صعب", "خبير"], value="متوسط")

        depth_map = {"سهل": 2, "متوسط": 4, "صعب": 5, "خبير": 6}
        depth = depth_map[difficulty]

        st.markdown("---")
        col_new, col_undo = st.columns(2)
        with col_new:
            new_game = st.button("🆕 لعبة جديدة", use_container_width=True)
        with col_undo:
            undo = st.button("↩️ تراجع", use_container_width=True, disabled=not st.session_state.get("game_started", False))

        if new_game:
            if "أبيض" in color_choice:
                init_game(WHITE, BLACK, depth)
            else:
                init_game(BLACK, WHITE, depth)
            st.rerun()

        if undo and st.session_state.get("game_started"):
            undo_move()
            st.rerun()

        if st.session_state.get("game_started"):
            board = st.session_state.board
            w_men, w_kings, b_men, b_kings = count_pieces(board)
            w_total = w_men + w_kings
            b_total = b_men + b_kings

            st.markdown("---")
            st.markdown("### 📊 إحصائيات")
            king_w = f"+ {w_kings} ملك" if w_kings else ""
            king_b = f"+ {b_kings} ملك" if b_kings else ""
            st.markdown(f"""
                <div class="info-card"><div class="piece-count">
                    <div class="piece-side">
                        <div style="font-size:1.5rem">⬜</div>
                        <div class="piece-num">{w_total}</div>
                        <div style="font-size:0.8rem">{w_men} قطعة {king_w}</div>
                    </div>
                    <div style="font-size:1.5rem;color:#666">⚔️</div>
                    <div class="piece-side">
                        <div style="font-size:1.5rem">⬛</div>
                        <div class="piece-num">{b_total}</div>
                        <div style="font-size:0.8rem">{b_men} قطعة {king_b}</div>
                    </div>
                </div></div>
            """, unsafe_allow_html=True)

            st.markdown(f"📝 عدد الحركات: **{len(st.session_state.move_history)}**")
            if st.session_state.ai_info:
                st.markdown(f"🧠 {st.session_state.ai_info}")

            if st.session_state.move_history:
                st.markdown("---")
                st.markdown("### 📜 سجل الحركات")
                with st.container(height=250):
                    for i, (who, mv) in enumerate(st.session_state.move_history, 1):
                        st.markdown(f'<div class="history-item">{i}. {who} {mv}</div>', unsafe_allow_html=True)

    if not st.session_state.get("game_started"):
        st.markdown("---")
        st.info("👈 اضغط **'لعبة جديدة'** في الشريط الجانبي للبدء")
        demo = Board(variant="english")
        st.markdown(f'<div class="board-container">{render_board_svg(demo)}</div>', unsafe_allow_html=True)
        st.stop()

    if st.session_state.pending_ai and not st.session_state.game_over:
        with st.spinner("🤖 الكمبيوتر يفكر..."):
            play_ai_move()
        st.rerun()

    board = st.session_state.board
    player_color = st.session_state.player_color
    ai_color = st.session_state.ai_color

    if st.session_state.game_over:
        winner = st.session_state.winner
        if winner == 'player':
            st.markdown('<div class="status-box status-win">🎉 مبروك! لقد فزت!</div>', unsafe_allow_html=True)
            if not st.session_state.get("celebrated"):
                st.balloons()
                st.session_state.celebrated = True
        elif winner == 'ai':
            st.markdown('<div class="status-box status-lose">💻 الكمبيوتر فاز! حاول مرة أخرى</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-draw">🤝 تعادل!</div>', unsafe_allow_html=True)
    else:
        if board.turn == player_color:
            st.markdown('<div class="status-box status-player">👤 دورك الآن</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-ai">🤖 دور الكمبيوتر</div>', unsafe_allow_html=True)

    board_svg = render_board_svg(board, st.session_state.get("last_move", ""), st.session_state.get("hint_move", ""))
    st.markdown(f'<div class="board-container">{board_svg}</div>', unsafe_allow_html=True)

    if not st.session_state.game_over and board.turn == player_color:
        legal_moves = get_legal_moves(board)
        if legal_moves:
            st.markdown("---")
            move_labels = [format_move(m) for m in legal_moves]

            col_sel, col_btn, col_hint = st.columns([2, 1, 1])
            with col_sel:
                st.selectbox("🎯 اختر حركتك:", range(len(move_labels)), format_func=lambda i: f"[{i}] {move_labels[i]}", key="move_select")
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("▶️ العب!", use_container_width=True, type="primary"):
                    play_human_move()
                    st.rerun()
            with col_hint:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💡 مساعدة", use_container_width=True):
                    with st.spinner("جاري تحليل الرقعة..."):
                        hint_mv, _, _ = find_best_move(board, player_color, max_depth=4, time_limit=2.0)
                        if hint_mv:
                            st.session_state.hint_move = format_move(hint_mv)
                    st.rerun()


if __name__ == "__main__":
    main()
