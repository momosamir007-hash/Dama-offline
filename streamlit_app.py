# streamlit_app.py
"""
🎲 المساعد الذكي للدومينو - Streamlit Edition
التطبيق الرئيسي مع واجهة SVG
"""

import streamlit as st
import time
import random
from typing import List, Dict, Optional

# إعداد المسار
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_engine.domino_board import DominoTile, Board, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, PlayerInfo, Move
)
from game_engine.rules import DominoRules, GameMode
from ai_brain.mcts import MCTSEngine
from ai_brain.strategy import StrategyAnalyzer
from ai_brain.probability import ProbabilityEngine
from svg_renderer import DominoSVG, TileTheme
from config import GameConfig


# ──────────────────────────────────────────────
# إعداد الصفحة
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="المساعد الذكي للدومينو",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CSS مخصص
# ──────────────────────────────────────────────

st.markdown("""
<style>
    /* تنسيق عام */
    .main { direction: rtl; }

    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }

    /* بطاقات */
    .game-card {
        background: rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
    }

    /* عنوان رئيسي */
    .main-title {
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }

    /* بطاقة التوصية */
    .recommendation-card {
        background: linear-gradient(135deg, #1B5E20, #2E7D32);
        border-radius: 16px;
        padding: 24px;
        color: white;
        text-align: center;
        margin: 15px 0;
        box-shadow: 0 8px 32px rgba(46,125,50,0.3);
    }

    .recommendation-card h3 {
        color: #A5D6A7;
        margin-bottom: 10px;
    }

    /* أزرار الحركات */
    .move-btn {
        background: linear-gradient(135deg, #1565C0, #1976D2);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s;
    }

    /* إخفاء عناصر Streamlit الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* تحسين الأزرار */
    .stButton > button {
        border-radius: 12px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# تهيئة الحالة (Session State)
# ──────────────────────────────────────────────

def init_session_state():
    """تهيئة حالة الجلسة"""
    defaults = {
        'game_state': None,
        'game_started': False,
        'game_phase': 'setup',  # setup, playing, over
        'my_hand_input': [],
        'move_history_display': [],
        'ai_recommendation': None,
        'ai_analysis': None,
        'theme': TileTheme.MODERN,
        'show_probabilities': False,
        'mcts_simulations': 1000,
        'mcts_time': 3.0,
        'message': '',
        'message_type': 'info',
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ──────────────────────────────────────────────
# مكونات الواجهة
# ──────────────────────────────────────────────

def show_header():
    """العنوان الرئيسي"""
    st.markdown(
        '<div class="main-title">'
        '🎲 المساعد الذكي للدومينو 🎲'
        '</div>',
        unsafe_allow_html=True
    )


def show_sidebar():
    """الشريط الجانبي"""
    with st.sidebar:
        st.markdown("## ⚙️ الإعدادات")

        # السمة
        theme_names = {
            "حديث 🎨": TileTheme.MODERN,
            "كلاسيكي ♟️": TileTheme.CLASSIC,
            "داكن 🌙": TileTheme.DARK,
            "خشبي 🪵": TileTheme.WOODEN,
        }

        selected_theme = st.selectbox(
            "سمة الأحجار",
            list(theme_names.keys()),
            index=0
        )
        st.session_state.theme = theme_names[selected_theme]

        st.markdown("---")

        # إعدادات الذكاء الاصطناعي
        st.markdown("### 🧠 إعدادات الذكاء")

        st.session_state.mcts_simulations = st.slider(
            "عدد المحاكاات",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="أكثر = أدق لكن أبطأ"
        )

        st.session_state.mcts_time = st.slider(
            "وقت التحليل (ثوانٍ)",
            min_value=1.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
        )

        st.session_state.show_probabilities = st.checkbox(
            "عرض الاحتمالات",
            value=False
        )

        st.markdown("---")

        # معلومات
        st.markdown("### 📖 القواعد")
        with st.expander("قواعد اللعب"):
            st.markdown("""
            - 🎯 4 لاعبين في فريقين
            - 🃏 كل لاعب 7 أحجار
            - 👑 صاحب أعلى دبل يبدأ
            - 🔄 اللعب بالدور
            - 🚫 لو ما عندك حجر = دق
            - 🏆 أول من يخلّص أحجاره يفوز
            """)

        st.markdown("---")

        if st.button("🔄 لعبة جديدة", use_container_width=True):
            reset_game()


def reset_game():
    """إعادة تعيين اللعبة"""
    st.session_state.game_state = None
    st.session_state.game_started = False
    st.session_state.game_phase = 'setup'
    st.session_state.my_hand_input = []
    st.session_state.move_history_display = []
    st.session_state.ai_recommendation = None
    st.session_state.ai_analysis = None
    st.session_state.message = ''


# ──────────────────────────────────────────────
# مرحلة الإعداد
# ──────────────────────────────────────────────

def show_setup_phase():
    """مرحلة إدخال الأحجار"""
    st.markdown("### 📝 أدخل أحجارك السبعة")

    renderer = DominoSVG(theme=st.session_state.theme)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("اختر أحجارك من القائمة:")

        # شبكة اختيار الأحجار
        selected_tiles = []

        # عرض كل الأحجار الممكنة كأزرار
        all_possible = []
        for i in range(7):
            for j in range(i, 7):
                all_possible.append(DominoTile(j, i))

        # عرض في صفوف
        cols_per_row = 7
        for row_start in range(0, len(all_possible), cols_per_row):
            row_tiles = all_possible[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)

            for idx, tile in enumerate(row_tiles):
                with cols[idx]:
                    tile_key = f"{tile.high}-{tile.low}"
                    is_selected = tile in st.session_state.my_hand_input

                    label = f"{'✅' if is_selected else ''} [{tile.high}|{tile.low}]"

                    if st.button(
                        label,
                        key=f"tile_{tile_key}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                    ):
                        if is_selected:
                            st.session_state.my_hand_input.remove(tile)
                        elif len(st.session_state.my_hand_input) < 7:
                            st.session_state.my_hand_input.append(tile)
                        st.rerun()

    with col2:
        st.markdown("#### أحجارك المختارة:")

        if st.session_state.my_hand_input:
            hand_svg = renderer.render_hand(
                st.session_state.my_hand_input,
                title="أحجارك",
            )
            st.markdown(hand_svg, unsafe_allow_html=True)

            st.info(
                f"اخترت {len(st.session_state.my_hand_input)}/7 أحجار"
            )
        else:
            st.warning("لم تختر أي حجر بعد")

    # زر البدء
    st.markdown("---")

    col_a, col_b, col_c = st.columns([1, 2, 1])

    with col_b:
        if len(st.session_state.my_hand_input) == 7:
            if st.button(
                "🎮 ابدأ اللعب!",
                use_container_width=True,
                type="primary",
            ):
                start_game()
                st.rerun()
        elif len(st.session_state.my_hand_input) > 0:
            remaining = 7 - len(st.session_state.my_hand_input)
            st.warning(
                f"تحتاج {remaining} أحجار أخرى"
            )


def start_game():
    """بدء اللعبة"""
    state = GameState()
    state.initialize_players()
    state.set_my_hand(
        st.session_state.my_hand_input.copy()
    )

    st.session_state.game_state = state
    st.session_state.game_started = True
    st.session_state.game_phase = 'playing'
    st.session_state.message = '🎮 اللعبة بدأت! حظاً سعيداً'
    st.session_state.message_type = 'success'


# ──────────────────────────────────────────────
# مرحلة اللعب
# ──────────────────────────────────────────────

def show_playing_phase():
    """مرحلة اللعب الرئيسية"""
    state = st.session_state.game_state
    renderer = DominoSVG(theme=st.session_state.theme)

    # رسالة
    if st.session_state.message:
        msg_func = {
            'success': st.success,
            'error': st.error,
            'warning': st.warning,
            'info': st.info,
        }
        msg_func.get(
            st.session_state.message_type, st.info
        )(st.session_state.message)

    # ─── الطاولة ───
    st.markdown("### 🎯 الطاولة")
    board_svg = renderer.render_board(state.board)
    st.markdown(board_svg, unsafe_allow_html=True)

    # ─── خريطة اللاعبين ───
    with st.expander("👥 خريطة اللاعبين", expanded=True):
        players_svg = renderer.render_players_map(state)
        st.markdown(players_svg, unsafe_allow_html=True)

    st.markdown("---")

    # ─── التحكم ───
    current = state.current_turn

    if current == PlayerPosition.SOUTH:
        show_my_turn(state, renderer)
    else:
        show_opponent_turn(state, renderer)

    # ─── يدي ───
    st.markdown("---")
    st.markdown("### 🃏 يدك")

    valid_moves = state.get_valid_moves(PlayerPosition.SOUTH)
    playable_indices = []
    for i, tile in enumerate(state.my_hand):
        if any(
            m.tile == tile and not m.is_pass
            for m in valid_moves
        ):
            playable_indices.append(i)

    hand_svg = renderer.render_hand(
        state.my_hand,
        highlighted_indices=(
            playable_indices
            if current == PlayerPosition.SOUTH else []
        ),
        title="يدك",
    )
    st.markdown(hand_svg, unsafe_allow_html=True)

    # ─── الاحتمالات ───
    if st.session_state.show_probabilities:
        show_probabilities(state)

    # ─── سجل الحركات ───
    with st.expander("📜 سجل الحركات"):
        show_move_history()


def show_my_turn(state: GameState, renderer: DominoSVG):
    """دوري"""
    st.markdown(
        "### 🎯 دورك!",
    )

    valid_moves = state.get_valid_moves(PlayerPosition.SOUTH)

    # ─── زر التحليل الذكي ───
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "🧠 تحليل ذكي",
            use_container_width=True,
            type="primary",
        ):
            with st.spinner("جاري التحليل..."):
                run_ai_analysis(state)
            st.rerun()

    with col2:
        # عرض التوصية إن وجدت
        if st.session_state.ai_recommendation:
            show_ai_recommendation(renderer)

    # ─── أزرار الحركات ───
    st.markdown("#### اختر حركتك:")

    has_pass = any(m.is_pass for m in valid_moves)
    real_moves = [m for m in valid_moves if not m.is_pass]

    if real_moves:
        cols = st.columns(min(len(real_moves), 4))

        for i, move in enumerate(real_moves):
            col_idx = i % len(cols)
            with cols[col_idx]:
                dir_name = (
                    "⬅️ يسار"
                    if move.direction == Direction.LEFT
                    else "➡️ يمين"
                )

                # هل هذه هي التوصية؟
                is_recommended = False
                rec = st.session_state.ai_recommendation
                if rec and rec.tile == move.tile and rec.direction == move.direction:
                    is_recommended = True

                btn_label = (
                    f"{'⭐ ' if is_recommended else ''}"
                    f"[{move.tile.high}|{move.tile.low}] "
                    f"{dir_name}"
                )

                if st.button(
                    btn_label,
                    key=f"move_{i}",
                    use_container_width=True,
                    type="primary" if is_recommended else "secondary",
                ):
                    apply_my_move(move)
                    st.rerun()

    if has_pass:
        if st.button(
            "🚫 دق (Pass)",
            use_container_width=True,
        ):
            pass_move = Move(
                PlayerPosition.SOUTH, None, None
            )
            apply_my_move(pass_move)
            st.rerun()


def show_opponent_turn(state: GameState, renderer: DominoSVG):
    """دور الخصم / الشريك"""
    name_map = {
        PlayerPosition.WEST: "الخصم الأيمن (غرب)",
        PlayerPosition.NORTH: "شريكك (شمال)",
        PlayerPosition.EAST: "الخصم الأيسر (شرق)",
    }

    current = state.current_turn
    name = name_map.get(current, str(current))

    st.markdown(f"### 🎯 دور: {name}")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("**ماذا لعب؟**")

        sub_col1, sub_col2 = st.columns(2)

        with sub_col1:
            high = st.number_input(
                "الرقم الأول",
                min_value=0, max_value=6,
                value=0,
                key=f"opp_high_{current.value}"
            )

        with sub_col2:
            low = st.number_input(
                "الرقم الثاني",
                min_value=0, max_value=6,
                value=0,
                key=f"opp_low_{current.value}"
            )

    with col2:
        direction = st.radio(
            "الاتجاه",
            ["⬅️ يسار", "➡️ يمين"],
            key=f"opp_dir_{current.value}",
            horizontal=True,
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            "✅ تأكيد",
            key=f"confirm_opp_{current.value}",
            type="primary",
            use_container_width=True,
        ):
            tile = DominoTile(int(high), int(low))
            dir_val = (
                Direction.LEFT
                if "يسار" in direction
                else Direction.RIGHT
            )
            move = Move(current, tile, dir_val)
            apply_opponent_move(move)
            st.rerun()

        if st.button(
            "🚫 دق",
            key=f"pass_opp_{current.value}",
            use_container_width=True,
        ):
            move = Move(current, None, None)
            apply_opponent_move(move)
            st.rerun()


# ──────────────────────────────────────────────
# تطبيق الحركات
# ──────────────────────────────────────────────

def apply_my_move(move: Move):
    """تطبيق حركتي"""
    state = st.session_state.game_state

    success = state.apply_move(move)

    if success:
        if move.is_pass:
            log = "أنت: دق 🚫"
        else:
            dir_name = (
                "يسار" if move.direction == Direction.LEFT
                else "يمين"
            )
            log = f"أنت: [{move.tile.high}|{move.tile.low}] ← {dir_name}"

        st.session_state.move_history_display.append(log)
        st.session_state.ai_recommendation = None
        st.session_state.ai_analysis = None
        st.session_state.message = f"✅ {log}"
        st.session_state.message_type = 'success'

        check_game_over()
    else:
        st.session_state.message = "❌ حركة غير صحيحة!"
        st.session_state.message_type = 'error'


def apply_opponent_move(move: Move):
    """تطبيق حركة الخصم"""
    state = st.session_state.game_state
    current = state.current_turn

    name_map = {
        PlayerPosition.WEST: "الخصم الأيمن",
        PlayerPosition.NORTH: "الشريك",
        PlayerPosition.EAST: "الخصم الأيسر",
    }
    name = name_map.get(current, str(current))

    if not move.is_pass and move.tile:
        state.players[current].tiles_count -= 1
        state.players[current].played_tiles.append(move.tile)

    success = state.apply_move(move)

    if success:
        if move.is_pass:
            log = f"{name}: دق 🚫"
        else:
            dir_name = (
                "يسار" if move.direction == Direction.LEFT
                else "يمين"
            )
            log = f"{name}: [{move.tile.high}|{move.tile.low}] ← {dir_name}"

        st.session_state.move_history_display.append(log)
        st.session_state.message = f"✅ {log}"
        st.session_state.message_type = 'info'

        check_game_over()
    else:
        st.session_state.message = "❌ حركة غير صحيحة!"
        st.session_state.message_type = 'error'


def check_game_over():
    """التحقق من نهاية اللعبة"""
    state = st.session_state.game_state
    rules = DominoRules()

    is_over, reason = rules.check_game_over(state)

    if is_over:
        state.is_game_over = True
        st.session_state.game_phase = 'over'

        if state.winner in (
            PlayerPosition.SOUTH,
            PlayerPosition.NORTH
        ):
            st.session_state.message = f"🏆 مبروك! فريقك فاز! {reason}"
            st.session_state.message_type = 'success'
        elif state.winner:
            st.session_state.message = f"😔 خسرت. {reason}"
            st.session_state.message_type = 'error'
        else:
            st.session_state.message = f"🤝 تعادل. {reason}"
            st.session_state.message_type = 'warning'


# ──────────────────────────────────────────────
# الذكاء الاصطناعي
# ──────────────────────────────────────────────

def run_ai_analysis(state: GameState):
    """تشغيل التحليل الذكي"""
    config = GameConfig()
    config.mcts_simulations = st.session_state.mcts_simulations
    config.mcts_time_limit = st.session_state.mcts_time

    engine = MCTSEngine(config)
    best_move, analysis = engine.find_best_move(state)

    st.session_state.ai_recommendation = best_move
    st.session_state.ai_analysis = analysis

    # تحليل استراتيجي
    analyzer = StrategyAnalyzer(state)
    strategy = analyzer.analyze_move(best_move)
    st.session_state.ai_strategy = strategy


def show_ai_recommendation(renderer: DominoSVG):
    """عرض توصية الذكاء الاصطناعي"""
    rec = st.session_state.ai_recommendation
    analysis = st.session_state.ai_analysis
    strategy = getattr(st.session_state, 'ai_strategy', {})

    if not rec:
        return

    # بطاقة التوصية
    if rec.is_pass:
        rec_text = "دق (Pass) 🚫"
    else:
        dir_name = (
            "⬅️ يسار"
            if rec.direction == Direction.LEFT
            else "➡️ يمين"
        )
        rec_text = f"[{rec.tile.high}|{rec.tile.low}] {dir_name}"

    st.markdown(f"""
    <div class="recommendation-card">
        <h3>🧠 توصية المساعد الذكي</h3>
        <h2>⭐ {rec_text}</h2>
        <p>محاكاات: {analysis.get('total_simulations', 0)} |
           وقت: {analysis.get('time_elapsed', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    # الحجر المُوصى به
    if not rec.is_pass:
        tile_svg = renderer.render_single_tile_large(
            rec.tile,
            label="⭐ الحركة المُوصى بها"
        )
        st.markdown(tile_svg, unsafe_allow_html=True)

    # الأسباب
    reasons = strategy.get('reasons', [])
    if reasons:
        with st.expander("📝 لماذا هذه الحركة؟", expanded=True):
            for reason in reasons:
                st.markdown(f"- {reason}")

    # تحليل بياني
    if analysis and 'moves_analysis' in analysis:
        analysis_svg = renderer.render_move_analysis(
            analysis['moves_analysis']
        )
        st.markdown(analysis_svg, unsafe_allow_html=True)


def show_probabilities(state: GameState):
    """عرض احتمالات أحجار الخصوم"""
    with st.expander("🎯 احتمالات أحجار الخصوم"):
        engine = ProbabilityEngine(state)
        probs = engine.calculate_tile_probabilities()

        name_map = {
            PlayerPosition.WEST: "الخصم الأيمن",
            PlayerPosition.NORTH: "الشريك",
            PlayerPosition.EAST: "الخصم الأيسر",
        }

        tabs = st.tabs(list(name_map.values()))

        for tab, pos in zip(tabs, name_map.keys()):
            with tab:
                if pos in probs:
                    sorted_tiles = sorted(
                        probs[pos].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    for tile, prob in sorted_tiles[:10]:
                        if prob < 0.01:
                            continue

                        col1, col2 = st.columns([1, 3])

                        with col1:
                            st.markdown(
                                f"**[{tile.high}|{tile.low}]**"
                            )

                        with col2:
                            st.progress(
                                min(prob, 1.0),
                                text=f"{prob:.0%}"
                            )


def show_move_history():
    """عرض سجل الحركات"""
    history = st.session_state.move_history_display

    if not history:
        st.info("لم تُلعب أي حركة بعد")
        return

    for i, entry in enumerate(reversed(history[-15:]), 1):
        st.markdown(f"`{len(history) - i + 1}.` {entry}")


# ──────────────────────────────────────────────
# مرحلة نهاية اللعبة
# ──────────────────────────────────────────────

def show_game_over():
    """شاشة نهاية اللعبة"""
    state = st.session_state.game_state

    is_win = state.winner in (
        PlayerPosition.SOUTH,
        PlayerPosition.NORTH
    )

    if is_win:
        st.balloons()
        st.markdown("""
        <div style="text-align:center; padding:40px;
                    background: linear-gradient(135deg, #1B5E20, #388E3C);
                    border-radius: 20px; color: white;
                    margin: 20px 0;">
            <h1>🏆 مبروك! فريقك فاز! 🏆</h1>
        </div>
        """, unsafe_allow_html=True)
    elif state.winner:
        st.markdown("""
        <div style="text-align:center; padding:40px;
                    background: linear-gradient(135deg, #B71C1C, #E53935);
                    border-radius: 20px; color: white;
                    margin: 20px 0;">
            <h1>😔 خسرت هذه الجولة</h1>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:40px;
                    background: linear-gradient(135deg, #E65100, #FF9800);
                    border-radius: 20px; color: white;
                    margin: 20px 0;">
            <h1>🤝 تعادل!</h1>
        </div>
        """, unsafe_allow_html=True)

    # النقاط
    rules = DominoRules()
    score = rules.calculate_score(state)

    st.markdown("### 📊 النقاط النهائية")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "فريقك (أنت + شريكك)",
            f"{score.team_south_north} نقطة",
            delta=(
                "فائز! 🏆"
                if score.winner_team == "south_north"
                else None
            )
        )

    with col2:
        st.metric(
            "فريق الخصوم",
            f"{score.team_west_east} نقطة",
            delta=(
                "فائز"
                if score.winner_team == "west_east"
                else None
            )
        )

    st.info(score.reason)

    # زر إعادة اللعب
    if st.button(
        "🔄 لعبة جديدة",
        use_container_width=True,
        type="primary",
    ):
        reset_game()
        st.rerun()


# ──────────────────────────────────────────────
# التطبيق الرئيسي
# ──────────────────────────────────────────────

def main():
    """نقطة البداية"""
    show_header()
    show_sidebar()

    phase = st.session_state.game_phase

    if phase == 'setup':
        show_setup_phase()
    elif phase == 'playing':
        show_playing_phase()
    elif phase == 'over':
        show_game_over()


if __name__ == "__main__":
    main()
