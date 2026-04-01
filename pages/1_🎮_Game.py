# pages/1_🎮_Game.py
"""
🎮 صفحة اللعب الرئيسية
تعمل بشكل مستقل عن streamlit_app.py
مع كل ميزات اللعب والتحليل الذكي
"""

import streamlit as st
import time
import os
import sys

# إعداد المسار
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game_engine.domino_board import (
    DominoTile, Board, Direction
)
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)
from game_engine.rules import DominoRules, GameMode
from ai_brain.mcts import MCTSEngine
from ai_brain.strategy import StrategyAnalyzer
from ai_brain.probability import ProbabilityEngine
from svg_renderer import DominoSVG, TileTheme
from streamlit_utils import (
    SessionManager, UIComponents, GameSaveManager,
    PlayerStats, Formatter, ExportTools,
    NotificationManager, StyleManager,
    generate_all_tiles, get_playable_tiles,
    PLAYER_NAMES, PLAYER_ICONS,
)
from config import GameConfig


# ──────────────────────────────────────────────
# إعداد الصفحة
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="🎮 اللعب - الدومينو الذكي",
    page_icon="🎮",
    layout="wide",
)

SessionManager.init()
StyleManager.load_css("assets/style.css")


# ──────────────────────────────────────────────
# العنوان
# ──────────────────────────────────────────────

st.markdown("""
<div style="text-align: center; padding: 10px 0 20px 0;">
    <h1 style="
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2em;
    ">
        🎮 ساحة اللعب
    </h1>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# الشريط الجانبي
# ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ إعدادات اللعبة")

    # السمة
    theme_map = {
        "حديث 🎨": TileTheme.MODERN,
        "كلاسيكي ♟️": TileTheme.CLASSIC,
        "داكن 🌙": TileTheme.DARK,
        "خشبي 🪵": TileTheme.WOODEN,
    }
    theme_choice = st.selectbox(
        "سمة الأحجار",
        list(theme_map.keys()),
        index=0,
    )
    SessionManager.set('theme', theme_map[theme_choice])

    st.markdown("---")

    # إعدادات AI
    st.markdown("### 🧠 الذكاء الاصطناعي")

    SessionManager.set('mcts_simulations', st.slider(
        "عدد المحاكاات",
        100, 10000, 1000, 100,
        help="أكثر = أدق لكن أبطأ"
    ))

    SessionManager.set('mcts_time', st.slider(
        "وقت التحليل (ثوانٍ)",
        1.0, 10.0, 3.0, 0.5,
    ))

    SessionManager.set('show_probabilities', st.checkbox(
        "📊 عرض الاحتمالات", False
    ))

    st.markdown("---")

    # حفظ/تحميل
    st.markdown("### 💾 حفظ / تحميل")

    if SessionManager.get('game_started'):
        save_name = st.text_input(
            "اسم الحفظ",
            placeholder="اختياري..."
        )
        if st.button("💾 حفظ اللعبة", use_container_width=True):
            state = SessionManager.get('game_state')
            if state:
                path = GameSaveManager.save_game(
                    state, save_name
                )
                NotificationManager.show_toast(
                    f"تم الحفظ: {path}", "success"
                )

    # قائمة الحفظ
    saves = GameSaveManager.list_saves()
    if saves:
        with st.expander(f"📂 ألعاب محفوظة ({len(saves)})"):
            for save in saves[:5]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    status = (
                        "✅ منتهية"
                        if save['is_over']
                        else "▶️ جارية"
                    )
                    st.caption(
                        f"{save['filename']} | "
                        f"{save['moves']} حركة | "
                        f"{status}"
                    )
                with col2:
                    if st.button(
                        "📂",
                        key=f"load_{save['filename']}",
                    ):
                        loaded = GameSaveManager.load_game(
                            save['filepath']
                        )
                        if loaded:
                            SessionManager.set(
                                'game_state', loaded
                            )
                            SessionManager.set(
                                'game_started', True
                            )
                            SessionManager.set(
                                'game_phase', 'playing'
                            )
                            NotificationManager.show_toast(
                                "تم التحميل!", "success"
                            )
                            st.rerun()

    st.markdown("---")

    if st.button(
        "🔄 لعبة جديدة",
        use_container_width=True,
        type="primary"
    ):
        SessionManager.reset_game()
        st.rerun()


# ──────────────────────────────────────────────
# المحتوى الرئيسي
# ──────────────────────────────────────────────

renderer = DominoSVG(theme=SessionManager.get('theme'))
phase = SessionManager.get('game_phase')


# ═══════════════════════════════════════════════
# مرحلة الإعداد
# ═══════════════════════════════════════════════

if phase == 'setup':
    st.markdown("### 📝 اختر أحجارك السبعة")

    # عرض الأحجار المختارة حالياً
    my_hand = SessionManager.get('my_hand_input') or []

    if my_hand:
        hand_svg = renderer.render_hand(
            my_hand, title="أحجارك المختارة"
        )
        st.markdown(hand_svg, unsafe_allow_html=True)
        st.info(f"✅ اخترت {len(my_hand)}/7 أحجار")
    else:
        st.warning("اضغط على الأحجار لاختيارها")

    st.markdown("---")

    # شبكة كل الأحجار
    all_tiles = generate_all_tiles()

    # الأحجار المختارة
    cols_count = 7
    for row in range(0, len(all_tiles), cols_count):
        row_tiles = all_tiles[row:row + cols_count]
        cols = st.columns(cols_count)

        for i, tile in enumerate(row_tiles):
            with cols[i]:
                is_sel = tile in my_hand

                btn_label = (
                    f"{'✅' if is_sel else '  '} "
                    f"[{tile.high}|{tile.low}]"
                )

                if st.button(
                    btn_label,
                    key=f"pick_{tile.high}_{tile.low}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary",
                ):
                    current = SessionManager.get(
                        'my_hand_input'
                    ) or []
                    if is_sel:
                        current.remove(tile)
                    elif len(current) < 7:
                        current.append(tile)
                    SessionManager.set('my_hand_input', current)
                    st.rerun()

    # زر البدء
    st.markdown("---")

    _, center, _ = st.columns([1, 2, 1])
    with center:
        if len(my_hand) == 7:
            if st.button(
                "🎮 ابدأ اللعب!",
                use_container_width=True,
                type="primary",
            ):
                state = GameState()
                state.initialize_players()
                state.set_my_hand(my_hand.copy())

                SessionManager.set('game_state', state)
                SessionManager.set('game_started', True)
                SessionManager.set('game_phase', 'playing')
                SessionManager.set(
                    'game_id',
                    SessionManager.generate_game_id()
                )
                NotificationManager.show_toast(
                    "🎮 اللعبة بدأت!", "success"
                )
                st.rerun()

        elif len(my_hand) > 0:
            st.warning(
                f"تحتاج {7 - len(my_hand)} أحجار أخرى"
            )


# ═══════════════════════════════════════════════
# مرحلة اللعب
# ═══════════════════════════════════════════════

elif phase == 'playing':
    state = SessionManager.get('game_state')

    if not state:
        st.error("حالة اللعبة غير موجودة!")
        st.stop()

    # ─── الرسالة ───
    msg = SessionManager.get('message')
    if msg:
        msg_type = SessionManager.get('message_type')
        NotificationManager.show_banner(msg, msg_type)

    # ─── الطاولة ───
    st.markdown("### 🎯 الطاولة")
    board_svg = renderer.render_board(state.board, width=900)
    st.markdown(board_svg, unsafe_allow_html=True)

    # ─── اللاعبون ───
    with st.expander("👥 خريطة اللاعبين", expanded=False):
        map_svg = renderer.render_players_map(state, width=750)
        st.markdown(map_svg, unsafe_allow_html=True)

    st.markdown("---")

    # ─── التحكم حسب الدور ───
    current_turn = state.current_turn

    if current_turn == PlayerPosition.SOUTH:
        # ═══════ دوري ═══════
        st.markdown("### 🎯 دورك!")

        valid_moves = state.get_valid_moves(
            PlayerPosition.SOUTH
        )
        real_moves = [m for m in valid_moves if not m.is_pass]
        has_pass = any(m.is_pass for m in valid_moves)

        # زر التحليل والتوصية
        ai_col, rec_col = st.columns([1, 2])

        with ai_col:
            if st.button(
                "🧠 تحليل ذكي",
                use_container_width=True,
                type="primary",
            ):
                with st.spinner("⏳ جاري التحليل الذكي..."):
                    config = GameConfig()
                    config.mcts_simulations = SessionManager.get(
                        'mcts_simulations'
                    )
                    config.mcts_time_limit = SessionManager.get(
                        'mcts_time'
                    )

                    engine = MCTSEngine(config)
                    best, analysis = engine.find_best_move(state)

                    analyzer = StrategyAnalyzer(state)
                    strategy = analyzer.analyze_move(best)

                    SessionManager.set('ai_recommendation', best)
                    SessionManager.set('ai_analysis', analysis)
                    SessionManager.set('ai_strategy', strategy)

                st.rerun()

        with rec_col:
            rec = SessionManager.get('ai_recommendation')
            analysis = SessionManager.get('ai_analysis')
            strategy = SessionManager.get('ai_strategy')

            if rec and analysis:
                if rec.is_pass:
                    rec_txt = "دق 🚫"
                else:
                    d = (
                        "⬅️ يسار"
                        if rec.direction == Direction.LEFT
                        else "➡️ يمين"
                    )
                    rec_txt = f"[{rec.tile.high}|{rec.tile.low}] {d}"

                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #1B5E20, #2E7D32);
                    border-radius: 14px;
                    padding: 18px;
                    color: white;
                    text-align: center;
                ">
                    <div style="font-size: 13px; color: #A5D6A7;">
                        🧠 توصية المساعد الذكي
                    </div>
                    <div style="font-size: 22px; font-weight: bold;
                                margin: 8px 0;">
                        ⭐ {rec_txt}
                    </div>
                    <div style="font-size: 11px; color: #C8E6C9;">
                        {analysis.get('total_simulations', 0)} محاكاة |
                        {analysis.get('time_elapsed', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # الأسباب
                if strategy and strategy.get('reasons'):
                    with st.expander("📝 لماذا هذه الحركة؟"):
                        for reason in strategy['reasons']:
                            st.markdown(f"- {reason}")

                # الرسم البياني
                if analysis.get('moves_analysis'):
                    chart_svg = renderer.render_move_analysis(
                        analysis['moves_analysis']
                    )
                    st.markdown(chart_svg, unsafe_allow_html=True)

        # ─── أزرار الحركات ───
        st.markdown("#### اختر حركتك:")

        if real_moves:
            btn_cols = st.columns(min(len(real_moves), 4))

            for i, move in enumerate(real_moves):
                with btn_cols[i % len(btn_cols)]:
                    d = (
                        "⬅️ يسار"
                        if move.direction == Direction.LEFT
                        else "➡️ يمين"
                    )

                    is_rec = False
                    if rec and not rec.is_pass:
                        is_rec = (
                            rec.tile == move.tile and
                            rec.direction == move.direction
                        )

                    prefix = "⭐ " if is_rec else ""

                    if st.button(
                        f"{prefix}[{move.tile.high}|{move.tile.low}] {d}",
                        key=f"play_{i}",
                        use_container_width=True,
                        type="primary" if is_rec else "secondary",
                    ):
                        state.apply_move(move)
                        history = SessionManager.get(
                            'move_history_display'
                        ) or []
                        history.append(
                            Formatter.move_to_text(move)
                        )
                        SessionManager.set(
                            'move_history_display', history
                        )
                        SessionManager.set(
                            'ai_recommendation', None
                        )
                        SessionManager.set('ai_analysis', None)
                        SessionManager.set(
                            'message',
                            f"✅ لعبت [{move.tile.high}|{move.tile.low}]"
                        )
                        SessionManager.set(
                            'message_type', 'success'
                        )

                        # فحص النهاية
                        rules = DominoRules()
                        over, reason = rules.check_game_over(state)
                        if over:
                            state.is_game_over = True
                            SessionManager.set(
                                'game_phase', 'over'
                            )
                        st.rerun()

        if has_pass:
            if st.button(
                "🚫 دق (Pass)",
                use_container_width=True,
            ):
                pass_move = Move(
                    PlayerPosition.SOUTH, None, None
                )
                state.apply_move(pass_move)
                history = SessionManager.get(
                    'move_history_display'
                ) or []
                history.append("🟢 أنت: دق 🚫")
                SessionManager.set(
                    'move_history_display', history
                )
                SessionManager.set(
                    'message', "🚫 دقيت"
                )
                SessionManager.set('message_type', 'warning')

                rules = DominoRules()
                over, reason = rules.check_game_over(state)
                if over:
                    state.is_game_over = True
                    SessionManager.set('game_phase', 'over')
                st.rerun()

    else:
        # ═══════ دور الخصم/الشريك ═══════
        name = PLAYER_NAMES.get(current_turn, "?")
        icon = PLAYER_ICONS.get(current_turn, "⚪")

        st.markdown(f"### {icon} دور: {name}")

        c1, c2, c3 = st.columns([2, 1, 1])

        with c1:
            sc1, sc2 = st.columns(2)
            with sc1:
                high = st.number_input(
                    "الرقم الأول", 0, 6, 0,
                    key=f"oh_{current_turn.value}"
                )
            with sc2:
                low = st.number_input(
                    "الرقم الثاني", 0, 6, 0,
                    key=f"ol_{current_turn.value}"
                )

        with c2:
            direction = st.radio(
                "الاتجاه",
                ["⬅️ يسار", "➡️ يمين"],
                key=f"od_{current_turn.value}",
                horizontal=True,
            )

        with c3:
            st.write("")  # فراغ
            if st.button(
                "✅ تأكيد",
                key=f"oc_{current_turn.value}",
                type="primary",
                use_container_width=True,
            ):
                tile = DominoTile(int(high), int(low))
                d = (
                    Direction.LEFT
                    if "يسار" in direction
                    else Direction.RIGHT
                )
                move = Move(current_turn, tile, d)

                state.players[current_turn].tiles_count -= 1
                state.players[current_turn].played_tiles.append(
                    tile
                )
                state.apply_move(move)

                history = SessionManager.get(
                    'move_history_display'
                ) or []
                history.append(Formatter.move_to_text(move))
                SessionManager.set(
                    'move_history_display', history
                )

                rules = DominoRules()
                over, reason = rules.check_game_over(state)
                if over:
                    state.is_game_over = True
                    SessionManager.set('game_phase', 'over')
                st.rerun()

            if st.button(
                "🚫 دق",
                key=f"op_{current_turn.value}",
                use_container_width=True,
            ):
                move = Move(current_turn, None, None)
                state.apply_move(move)

                history = SessionManager.get(
                    'move_history_display'
                ) or []
                history.append(
                    f"{icon} {name}: دق 🚫"
                )
                SessionManager.set(
                    'move_history_display', history
                )

                rules = DominoRules()
                over, reason = rules.check_game_over(state)
                if over:
                    state.is_game_over = True
                    SessionManager.set('game_phase', 'over')
                st.rerun()

    # ─── يدي ───
    st.markdown("---")
    st.markdown("### 🃏 يدك")

    playable = get_playable_tiles(state.my_hand, state.board)
    highlight = (
        playable
        if current_turn == PlayerPosition.SOUTH
        else []
    )

    hand_svg = renderer.render_hand(
        state.my_hand,
        highlighted_indices=highlight,
        title="يدك"
    )
    st.markdown(hand_svg, unsafe_allow_html=True)

    # ─── الاحتمالات ───
    if SessionManager.get('show_probabilities'):
        with st.expander("🎯 احتمالات أحجار الخصوم"):
            prob_engine = ProbabilityEngine(state)
            probs = prob_engine.calculate_tile_probabilities()

            tabs = st.tabs([
                "الخصم الأيمن", "الشريك", "الخصم الأيسر"
            ])
            positions = [
                PlayerPosition.WEST,
                PlayerPosition.NORTH,
                PlayerPosition.EAST,
            ]

            for tab, pos in zip(tabs, positions):
                with tab:
                    sorted_t = sorted(
                        probs.get(pos, {}).items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    for tile, prob in sorted_t[:10]:
                        if prob < 0.01:
                            continue
                        c1, c2 = st.columns([1, 4])
                        with c1:
                            st.write(f"[{tile.high}|{tile.low}]")
                        with c2:
                            st.progress(
                                min(prob, 1.0),
                                text=f"{prob:.0%}"
                            )

    # ─── سجل الحركات ───
    with st.expander("📜 سجل الحركات"):
        history = SessionManager.get(
            'move_history_display'
        ) or []
        if history:
            for i, entry in enumerate(
                reversed(history[-20:]), 1
            ):
                st.markdown(
                    f"`{len(history) - i + 1}.` {entry}"
                )
        else:
            st.info("لم تُلعب أي حركة بعد")


# ═══════════════════════════════════════════════
# مرحلة نهاية اللعبة
# ═══════════════════════════════════════════════

elif phase == 'over':
    state = SessionManager.get('game_state')

    if not state:
        st.error("حالة اللعبة غير موجودة!")
        st.stop()

    is_win = state.winner in (
        PlayerPosition.SOUTH,
        PlayerPosition.NORTH
    )

    if is_win:
        st.balloons()
        st.markdown("""
        <div style="text-align:center; padding:50px;
                    background: linear-gradient(135deg, #1B5E20, #4CAF50);
                    border-radius: 20px; color: white;
                    margin: 20px 0;
                    box-shadow: 0 10px 40px rgba(76,175,80,0.3);">
            <h1 style="font-size: 3em;">🏆</h1>
            <h2>مبروك! فريقك فاز!</h2>
        </div>
        """, unsafe_allow_html=True)
    elif state.winner:
        st.markdown("""
        <div style="text-align:center; padding:50px;
                    background: linear-gradient(135deg, #B71C1C, #E53935);
                    border-radius: 20px; color: white;
                    margin: 20px 0;">
            <h1 style="font-size: 3em;">😔</h1>
            <h2>خسرت هذه الجولة</h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:50px;
                    background: linear-gradient(135deg, #E65100, #FF9800);
                    border-radius: 20px; color: white;
                    margin: 20px 0;">
            <h1 style="font-size: 3em;">🤝</h1>
            <h2>تعادل!</h2>
        </div>
        """, unsafe_allow_html=True)

    # النقاط
    rules = DominoRules()
    score = rules.calculate_score(state)

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "فريقك",
            f"{score.team_south_north} نقطة",
        )
    with c2:
        st.metric(
            "الخصوم",
            f"{score.team_west_east} نقطة",
        )

    st.info(score.reason)

    # تصدير
    st.markdown("---")
    ec1, ec2, ec3 = st.columns(3)

    with ec1:
        if st.button(
            "🔄 لعبة جديدة",
            use_container_width=True,
            type="primary",
        ):
            # تسجيل الإحصائيات
            result = (
                'win' if is_win
                else 'loss' if state.winner
                else 'draw'
            )
            PlayerStats.record_game(
                result=result,
                moves_count=len(state.move_history),
            )
            SessionManager.reset_game()
            st.rerun()

    with ec2:
        report = ExportTools.generate_game_report(state)
        st.download_button(
            "📄 تنزيل التقرير",
            data=report,
            file_name="domino_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with ec3:
        json_data = GameSaveManager.export_game_json(state)
        st.download_button(
            "💾 تنزيل اللعبة",
            data=json_data,
            file_name="domino_game.json",
            mime="application/json",
            use_container_width=True,
        )
