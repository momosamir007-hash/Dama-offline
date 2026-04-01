"""
🎲 المساعد الذكي للدومينو
الملف الرئيسي - مُصلح لعرض SVG بشكل صحيح
"""
import streamlit as st
import streamlit.components.v1 as components
import time

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import GameState, PlayerPosition, Move
from game_engine.rules import DominoRules
from ai_brain.mcts import MCTSEngine
from ai_brain.strategy import StrategyAnalyzer
from ai_brain.probability import ProbabilityEngine
from svg_renderer import DominoSVG
from streamlit_utils import (
    SessionManager, Formatter, NotificationManager,
    StyleManager, PlayerStats, ExportTools,
    generate_all_tiles, get_playable_tiles,
    PLAYER_NAMES, PLAYER_ICONS,
)
from config import GameConfig

# ─── إعداد ───
st.set_page_config(
    page_title="🎲 المساعد الذكي للدومينو",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

SessionManager.init()
StyleManager.load_css("assets/style.css")

# ─── CSS ───
st.markdown("""<style>
.rec-card{background:linear-gradient(135deg,#1B5E20,#2E7D32);
border-radius:14px;padding:20px;color:white;text-align:center;
margin:12px 0;box-shadow:0 6px 25px rgba(46,125,50,0.3)}
.rec-card h3{color:#A5D6A7;font-size:13px;margin-bottom:6px}
.rec-card h2{font-size:22px;margin:8px 0}
#MainMenu{visibility:hidden}footer{visibility:hidden}
header{visibility:hidden}
</style>""", unsafe_allow_html=True)

renderer = DominoSVG()


# ═══════════════════════════════════════
# الشريط الجانبي
# ═══════════════════════════════════════

with st.sidebar:
    st.markdown("## 🎲 المساعد الذكي")
    st.markdown("---")

    SessionManager.set('mcts_simulations', st.slider(
        "🧠 محاكاات AI", 200, 5000, 1000, 100
    ))
    SessionManager.set('mcts_time', st.slider(
        "⏱️ وقت التحليل", 1.0, 8.0, 3.0, 0.5
    ))
    SessionManager.set('show_probabilities',
        st.checkbox("📊 عرض الاحتمالات")
    )

    st.markdown("---")

    if st.button("🔄 لعبة جديدة", use_container_width=True, type="primary"):
        SessionManager.reset_game()
        st.rerun()

    st.markdown("---")
    with st.expander("📖 القواعد"):
        st.markdown("""
        - 4 لاعبين في فريقين
        - كل لاعب 7 أحجار
        - 🚫 لو ما عندك = دق
        - 🏆 أول من يخلّص يفوز
        """)

    st.markdown("---")
    st.caption("📷 صفحة الكاميرا في القائمة الجانبية")


# ═══════════════════════════════════════
# العنوان
# ═══════════════════════════════════════

st.markdown("""
<h1 style="text-align:center;
background:linear-gradient(90deg,#00d2ff,#3a7bd5);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
font-size:2.3em;margin-bottom:5px;">
🎲 المساعد الذكي للدومينو 🎲
</h1>
<p style="text-align:center;color:#888;margin-bottom:20px;">
حلل، خطط، واربح! 🏆
</p>
""", unsafe_allow_html=True)

phase = SessionManager.get('game_phase')


# ═══════════════════════════════════════
# مرحلة الإعداد
# ═══════════════════════════════════════

if phase == 'setup':
    st.markdown("### 📝 اختر أحجارك السبعة")
    st.caption("اضغط على الحجر لاختياره أو إلغائه")

    my_hand = SessionManager.get('my_hand_input') or []

    # عرض الأحجار المختارة
    if my_hand:
        renderer.display_hand(my_hand, title="أحجارك المختارة")
        st.success(f"✅ اخترت {len(my_hand)}/7 أحجار")
    else:
        st.info("👆 اضغط على الأحجار بالأسفل لاختيارها")

    st.markdown("---")

    # شبكة الأحجار
    all_tiles = generate_all_tiles()

    for row in range(0, len(all_tiles), 7):
        row_tiles = all_tiles[row:row + 7]
        cols = st.columns(7)
        for i, tile in enumerate(row_tiles):
            with cols[i]:
                is_sel = tile in my_hand
                emoji = "✅" if is_sel else "⬜"
                lbl = f"{emoji} [{tile.high}|{tile.low}]"

                if st.button(
                    lbl,
                    key=f"p_{tile.high}_{tile.low}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary",
                ):
                    cur = SessionManager.get('my_hand_input') or []
                    if is_sel:
                        cur.remove(tile)
                    elif len(cur) < 7:
                        cur.append(tile)
                    SessionManager.set('my_hand_input', cur)
                    st.rerun()

    # زر البدء
    st.markdown("---")
    _, center, _ = st.columns([1, 2, 1])
    with center:
        if len(my_hand) == 7:
            if st.button("🎮 ابدأ اللعب!", use_container_width=True, type="primary"):
                state = GameState()
                state.initialize_players()
                state.set_my_hand(my_hand.copy())
                SessionManager.set('game_state', state)
                SessionManager.set('game_started', True)
                SessionManager.set('game_phase', 'playing')
                st.rerun()
        elif my_hand:
            st.warning(f"⚠️ تحتاج {7 - len(my_hand)} أحجار أخرى")


# ═══════════════════════════════════════
# مرحلة اللعب
# ═══════════════════════════════════════

elif phase == 'playing':
    state = SessionManager.get('game_state')
    if not state:
        st.error("❌ خطأ! اضغط 'لعبة جديدة'")
        st.stop()

    # رسالة
    msg = SessionManager.get('message')
    if msg:
        mtype = SessionManager.get('message_type')
        if mtype == 'success':
            st.success(msg)
        elif mtype == 'warning':
            st.warning(msg)
        elif mtype == 'error':
            st.error(msg)
        else:
            st.info(msg)

    # ═══ الطاولة ═══
    st.markdown("### 🎯 الطاولة")
    renderer.display_board(state.board, width=900, height=180)

    # ═══ اللاعبون ═══
    with st.expander("👥 خريطة اللاعبين", expanded=True):
        renderer.display_players(state, width=720, height=400)

    st.markdown("---")

    current = state.current_turn

    # ═══════════════════════════════════
    # دوري
    # ═══════════════════════════════════
    if current == PlayerPosition.SOUTH:
        st.markdown("### 🎯 دورك! اختر حركتك")

        valid = state.get_valid_moves(PlayerPosition.SOUTH)
        real = [m for m in valid if not m.is_pass]
        has_pass = any(m.is_pass for m in valid)

        # ─── تحليل ذكي ───
        col_ai, col_rec = st.columns([1, 2])

        with col_ai:
            if st.button("🧠 تحليل ذكي", use_container_width=True, type="primary"):
                with st.spinner("⏳ الذكاء الاصطناعي يفكر..."):
                    cfg = GameConfig()
                    cfg.mcts_simulations = SessionManager.get('mcts_simulations')
                    cfg.mcts_time_limit = SessionManager.get('mcts_time')

                    eng = MCTSEngine(cfg)
                    best, analysis = eng.find_best_move(state)

                    analyzer = StrategyAnalyzer(state)
                    strategy = analyzer.analyze_move(best)

                    SessionManager.set('ai_recommendation', best)
                    SessionManager.set('ai_analysis', analysis)
                    SessionManager.set('ai_strategy', strategy)
                st.rerun()

        with col_rec:
            rec = SessionManager.get('ai_recommendation')
            analysis = SessionManager.get('ai_analysis')
            strategy = SessionManager.get('ai_strategy')

            if rec and analysis:
                if rec.is_pass:
                    rtxt = "دق 🚫"
                else:
                    d = "⬅️ يسار" if rec.direction == Direction.LEFT else "➡️ يمين"
                    rtxt = f"[{rec.tile.high}|{rec.tile.low}] {d}"

                st.markdown(f'''<div class="rec-card">
                <h3>🧠 توصية المساعد الذكي</h3>
                <h2>⭐ {rtxt}</h2>
                <p style="font-size:11px;color:#C8E6C9">
                {analysis.get('total_simulations',0)} محاكاة |
                {analysis.get('time_elapsed','')}</p>
                </div>''', unsafe_allow_html=True)

                # الحجر المُوصى
                if not rec.is_pass:
                    renderer.display_big_tile(rec.tile, "⭐ الحركة المُوصى بها")

                # الأسباب
                if strategy and strategy.get('reasons'):
                    with st.expander("📝 لماذا هذه الحركة؟", expanded=True):
                        for r in strategy['reasons']:
                            st.markdown(f"✅ {r}")

                # رسم بياني
                if analysis.get('moves_analysis'):
                    renderer.display_analysis(analysis['moves_analysis'])

        # ─── أزرار الحركات ───
        st.markdown("#### 👇 اختر حركتك:")

        if real:
            bcols = st.columns(min(len(real), 4))
            for i, move in enumerate(real):
                with bcols[i % len(bcols)]:
                    d = "⬅️" if move.direction == Direction.LEFT else "➡️"
                    is_rec = (
                        rec and not rec.is_pass and
                        rec.tile == move.tile and
                        rec.direction == move.direction
                    )
                    star = "⭐ " if is_rec else ""

                    if st.button(
                        f"{star}[{move.tile.high}|{move.tile.low}] {d}",
                        key=f"mv_{i}",
                        use_container_width=True,
                        type="primary" if is_rec else "secondary",
                    ):
                        state.apply_move(move)
                        h = SessionManager.get('move_history_display') or []
                        h.append(Formatter.move_to_text(move))
                        SessionManager.set('move_history_display', h)
                        SessionManager.set('ai_recommendation', None)
                        SessionManager.set('ai_analysis', None)
                        SessionManager.set('message',
                            f"✅ لعبت [{move.tile.high}|{move.tile.low}]")
                        SessionManager.set('message_type', 'success')

                        rules = DominoRules()
                        over, _ = rules.check_game_over(state)
                        if over:
                            state.is_game_over = True
                            SessionManager.set('game_phase', 'over')
                        st.rerun()

        if has_pass:
            if st.button("🚫 دق (Pass)", use_container_width=True):
                state.apply_move(Move(PlayerPosition.SOUTH, None, None))
                h = SessionManager.get('move_history_display') or []
                h.append("🟢 أنت: دق 🚫")
                SessionManager.set('move_history_display', h)
                SessionManager.set('message', '🚫 دقيت')
                SessionManager.set('message_type', 'warning')

                rules = DominoRules()
                over, _ = rules.check_game_over(state)
                if over:
                    state.is_game_over = True
                    SessionManager.set('game_phase', 'over')
                st.rerun()

    # ═══════════════════════════════════
    # دور الخصم / الشريك
    # ═══════════════════════════════════
    else:
        name = PLAYER_NAMES.get(current, "?")
        icon = PLAYER_ICONS.get(current, "⚪")

        st.markdown(f"### {icon} دور: {name}")
        st.caption("أدخل الحجر الذي لعبه أو اضغط دق")

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            sc1, sc2 = st.columns(2)
            with sc1:
                high = st.number_input("الرقم الأول", 0, 6, 0,
                    key=f"oh_{current.value}")
            with sc2:
                low = st.number_input("الرقم الثاني", 0, 6, 0,
                    key=f"ol_{current.value}")
        with c2:
            direction = st.radio("الاتجاه",
                ["⬅️ يسار", "➡️ يمين"],
                key=f"od_{current.value}",
                horizontal=True)
        with c3:
            st.write("")
            if st.button("✅ تأكيد", key=f"oc_{current.value}",
                         type="primary", use_container_width=True):
                tile = DominoTile(int(high), int(low))
                d = Direction.LEFT if "يسار" in direction else Direction.RIGHT
                move = Move(current, tile, d)

                state.players[current].tiles_count -= 1
                state.players[current].played_tiles.append(tile)
                state.apply_move(move)

                h = SessionManager.get('move_history_display') or []
                h.append(Formatter.move_to_text(move))
                SessionManager.set('move_history_display', h)

                rules = DominoRules()
                over, _ = rules.check_game_over(state)
                if over:
                    state.is_game_over = True
                    SessionManager.set('game_phase', 'over')
                st.rerun()

            if st.button("🚫 دق", key=f"op_{current.value}",
                         use_container_width=True):
                state.apply_move(Move(current, None, None))
                h = SessionManager.get('move_history_display') or []
                h.append(f"{icon} {name}: دق 🚫")
                SessionManager.set('move_history_display', h)

                rules = DominoRules()
                over, _ = rules.check_game_over(state)
                if over:
                    state.is_game_over = True
                    SessionManager.set('game_phase', 'over')
                st.rerun()

    # ═══ يدي ═══
    st.markdown("---")
    st.markdown("### 🃏 أحجارك")

    playable = get_playable_tiles(state.my_hand, state.board)
    hl = playable if current == PlayerPosition.SOUTH else []
    renderer.display_hand(state.my_hand, highlighted=hl, title="يدك")

    # ═══ الاحتمالات ═══
    if SessionManager.get('show_probabilities'):
        with st.expander("🎯 احتمالات أحجار الخصوم"):
            pe = ProbabilityEngine(state)
            probs = pe.calculate_tile_probabilities()
            tabs = st.tabs(["الخصم الأيمن", "الشريك", "الخصم الأيسر"])
            positions = [PlayerPosition.WEST, PlayerPosition.NORTH, PlayerPosition.EAST]
            for tab, pos in zip(tabs, positions):
                with tab:
                    items = sorted(
                        probs.get(pos, {}).items(),
                        key=lambda x: x[1], reverse=True
                    )
                    for tile, prob in items[:10]:
                        if prob < 0.01:
                            continue
                        tc1, tc2 = st.columns([1, 4])
                        with tc1:
                            st.write(f"**[{tile.high}|{tile.low}]**")
                        with tc2:
                            st.progress(min(prob, 1.0),
                                text=f"{prob:.0%}")

    # ═══ السجل ═══
    with st.expander("📜 سجل الحركات"):
        hist = SessionManager.get('move_history_display') or []
        if hist:
            for i, e in enumerate(reversed(hist[-20:]), 1):
                st.markdown(f"`{len(hist)-i+1}.` {e}")
        else:
            st.info("لم تُلعب أي حركة بعد")


# ═══════════════════════════════════════
# نهاية اللعبة
# ═══════════════════════════════════════

elif phase == 'over':
    state = SessionManager.get('game_state')
    if not state:
        st.error("❌ خطأ!")
        st.stop()

    is_win = state.winner in (PlayerPosition.SOUTH, PlayerPosition.NORTH)

    if is_win:
        st.balloons()
        st.markdown('''<div style="text-align:center;padding:50px;
        background:linear-gradient(135deg,#1B5E20,#4CAF50);
        border-radius:20px;color:white;margin:20px 0;">
        <h1 style="font-size:3em;">🏆</h1>
        <h2>مبروك! فريقك فاز!</h2></div>''', unsafe_allow_html=True)
    elif state.winner:
        st.markdown('''<div style="text-align:center;padding:50px;
        background:linear-gradient(135deg,#B71C1C,#E53935);
        border-radius:20px;color:white;margin:20px 0;">
        <h1 style="font-size:3em;">😔</h1>
        <h2>خسرت هذه الجولة</h2></div>''', unsafe_allow_html=True)
    else:
        st.markdown('''<div style="text-align:center;padding:50px;
        background:linear-gradient(135deg,#E65100,#FF9800);
        border-radius:20px;color:white;margin:20px 0;">
        <h1 style="font-size:3em;">🤝</h1>
        <h2>تعادل!</h2></div>''', unsafe_allow_html=True)

    # الطاولة النهائية
    st.markdown("### 🎯 الطاولة النهائية")
    renderer.display_board(state.board, width=900, height=180)

    # النقاط
    rules = DominoRules()
    score = rules.calculate_score(state)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("🟢 فريقك", f"{score.team_south_north} نقطة")
    with c2:
        st.metric("🔴 الخصوم", f"{score.team_west_east} نقطة")

    st.info(f"📝 {score.reason}")

    # أزرار
    st.markdown("---")
    ec1, ec2 = st.columns(2)
    with ec1:
        if st.button("🔄 لعبة جديدة", use_container_width=True, type="primary"):
            result = 'win' if is_win else 'loss' if state.winner else 'draw'
            PlayerStats.record_game(result=result, moves_count=len(state.move_history))
            SessionManager.reset_game()
            st.rerun()
    with ec2:
        report = ExportTools.generate_game_report(state)
        st.download_button("📄 تنزيل التقرير", data=report,
            file_name="domino_report.md", mime="text/markdown",
            use_container_width=True)
