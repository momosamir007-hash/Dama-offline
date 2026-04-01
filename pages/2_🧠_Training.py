# pages/2_🧠_Training.py
"""
🧠 صفحة تدريب الذكاء الاصطناعي
تتيح للمستخدم:
  - تشغيل جلسات تدريب
  - مراقبة التقدم
  - تحميل/حفظ النماذج
  - اختبار النموذج المدرب
"""

import streamlit as st
import time
import os
import sys
import json
import random
from pathlib import Path

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, ROOT)

from game_engine.domino_board import DominoTile, Direction
from game_engine.game_state import (
    GameState, PlayerPosition, Move
)
from ai_brain.trainer import (
    DominoTrainer, TrainingConfig,
    FeatureExtractor, QTable
)
from ai_brain.mcts import MCTSEngine
from svg_renderer import DominoSVG, TileTheme
from streamlit_utils import (
    SessionManager, UIComponents,
    NotificationManager, Formatter,
)
from config import GameConfig


# ──────────────────────────────────────────────
# إعداد الصفحة
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="🧠 التدريب - الدومينو الذكي",
    page_icon="🧠",
    layout="wide",
)

SessionManager.init()

st.markdown("""
<div style="text-align: center; padding: 10px 0 20px 0;">
    <h1 style="
        background: linear-gradient(90deg, #FF6B6B, #FFE66D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2em;
    ">
        🧠 مختبر التدريب
    </h1>
    <p style="color: #888;">
        درّب الذكاء الاصطناعي ليصبح خبيراً في الدومينو
    </p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# الشريط الجانبي
# ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔧 إعدادات التدريب")

    num_episodes = st.number_input(
        "عدد الحلقات",
        min_value=100,
        max_value=100000,
        value=1000,
        step=100,
    )

    learning_rate = st.slider(
        "معدل التعلم",
        0.001, 0.1, 0.01, 0.001,
        format="%.3f",
    )

    discount = st.slider(
        "عامل الخصم (γ)",
        0.5, 0.99, 0.95, 0.01,
    )

    epsilon_start = st.slider(
        "استكشاف أولي (ε)",
        0.1, 1.0, 1.0, 0.05,
    )

    epsilon_end = st.slider(
        "استكشاف نهائي",
        0.01, 0.3, 0.05, 0.01,
    )

    eval_interval = st.number_input(
        "فترة التقييم",
        10, 1000, 100, 10,
    )

    st.markdown("---")

    # النماذج المحفوظة
    st.markdown("### 📦 النماذج المحفوظة")

    model_dir = Path("models/trained")
    model_dir.mkdir(parents=True, exist_ok=True)

    models = list(model_dir.glob("*.pkl"))
    if models:
        for model_path in models[:5]:
            size_kb = model_path.stat().st_size / 1024
            st.caption(
                f"📄 {model_path.name} "
                f"({size_kb:.0f} KB)"
            )
    else:
        st.caption("لا توجد نماذج محفوظة")


# ──────────────────────────────────────────────
# تبويبات المحتوى
# ──────────────────────────────────────────────

tab_train, tab_test, tab_models = st.tabs([
    "🏋️ التدريب",
    "🧪 الاختبار",
    "📦 النماذج",
])


# ═══════════════════════════════════════════════
# تبويب التدريب
# ═══════════════════════════════════════════════

with tab_train:
    st.markdown("### 🏋️ تدريب جديد")

    st.markdown("""
    <div style="
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    ">
        <strong>كيف يعمل التدريب؟</strong><br>
        <span style="color: #aaa;">
        1. يلعب الذكاء الاصطناعي آلاف المباريات ضد نفسه<br>
        2. يتعلم من كل فوز وخسارة (Q-Learning)<br>
        3. يستكشف استراتيجيات جديدة (ε-greedy)<br>
        4. يُقيَّم دورياً لمتابعة التقدم
        </span>
    </div>
    """, unsafe_allow_html=True)

    # عرض الإعدادات الحالية
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(UIComponents.metric_card(
            "الحلقات", Formatter.format_number(num_episodes),
            "🔄", "#2196F3"
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(UIComponents.metric_card(
            "معدل التعلم", f"{learning_rate:.3f}",
            "📈", "#4CAF50"
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(UIComponents.metric_card(
            "الخصم (γ)", f"{discount:.2f}",
            "⚡", "#FF9800"
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(UIComponents.metric_card(
            "استكشاف", f"{epsilon_start:.2f}→{epsilon_end:.2f}",
            "🔍", "#9C27B0"
        ), unsafe_allow_html=True)

    st.markdown("---")

    # زر بدء التدريب
    if st.button(
        "🚀 ابدأ التدريب",
        use_container_width=True,
        type="primary",
    ):
        # إعداد التدريب
        config = TrainingConfig(
            num_episodes=num_episodes,
            learning_rate=learning_rate,
            discount_factor=discount,
            epsilon_start=epsilon_start,
            epsilon_end=epsilon_end,
            eval_interval=eval_interval,
            save_interval=max(num_episodes // 5, 100),
        )

        trainer = DominoTrainer(config=config)

        # شريط التقدم
        progress_bar = st.progress(0)
        status_text = st.empty()

        # إحصائيات مباشرة
        stats_container = st.container()
        chart_placeholder = st.empty()

        win_rates = []
        epsilons = []

        # حلقة التدريب
        start_time = time.time()

        for episode in range(1, num_episodes + 1):
            trainer.stats.episode = episode

            # لعب مباراة
            experiences, result = trainer._play_one_game()
            trainer._learn_from_experiences(experiences)
            trainer._update_stats(result)

            # تناقص Epsilon
            trainer.epsilon = max(
                config.epsilon_end,
                trainer.epsilon * config.epsilon_decay
            )

            # تحديث الواجهة
            progress = episode / num_episodes
            progress_bar.progress(progress)

            if episode % eval_interval == 0:
                win_rate = trainer._evaluate()
                win_rates.append(win_rate)
                epsilons.append(trainer.epsilon)

                elapsed = time.time() - start_time
                speed = episode / elapsed

                status_text.markdown(f"""
                **الحلقة {episode:,}/{num_episodes:,}** |
                نسبة الفوز: **{win_rate:.1%}** |
                ε: {trainer.epsilon:.3f} |
                سرعة: {speed:.0f} لعبة/ث |
                حالات: {len(trainer.q_table.table):,}
                """)

                # رسم بياني مباشر
                if win_rates:
                    chart_placeholder.line_chart(
                        {"نسبة الفوز": win_rates},
                        use_container_width=True,
                    )

            if episode % config.save_interval == 0:
                trainer._save_checkpoint(f"ep{episode}")

        # حفظ نهائي
        trainer._save_checkpoint("final")
        progress_bar.progress(1.0)

        total_time = time.time() - start_time

        st.success(
            f"✅ انتهى التدريب في "
            f"{Formatter.format_duration(total_time)}"
        )

        # النتائج النهائية
        st.markdown("### 📊 النتائج النهائية")
        rc1, rc2, rc3, rc4 = st.columns(4)

        with rc1:
            st.metric("فوز", trainer.stats.total_wins)
        with rc2:
            st.metric("خسارة", trainer.stats.total_losses)
        with rc3:
            st.metric("تعادل", trainer.stats.total_draws)
        with rc4:
            st.metric(
                "أفضل نسبة فوز",
                f"{trainer.stats.best_win_rate:.1%}"
            )

        # رسم نهائي
        if win_rates:
            st.line_chart({
                "نسبة الفوز": win_rates,
                "الاستكشاف (ε)": epsilons,
            })


# ═══════════════════════════════════════════════
# تبويب الاختبار
# ═══════════════════════════════════════════════

with tab_test:
    st.markdown("### 🧪 اختبار النموذج المدرب")

    st.markdown("""
    شاهد الذكاء الاصطناعي المدرب وهو يلعب
    مباراة كاملة تلقائياً!
    """)

    test_games = st.slider(
        "عدد مباريات الاختبار",
        10, 500, 50, 10,
    )

    model_files = list(
        Path("models/trained").glob("*.pkl")
    )

    selected_model = None
    if model_files:
        model_names = [f.name for f in model_files]
        selected_name = st.selectbox(
            "اختر النموذج",
            model_names,
        )
        selected_model = str(
            Path("models/trained") / selected_name
        )
    else:
        st.warning(
            "لا توجد نماذج مدربة. "
            "ادرّب نموذجاً أولاً!"
        )

    if selected_model and st.button(
        "🧪 ابدأ الاختبار",
        type="primary",
        use_container_width=True,
    ):
        trainer = DominoTrainer()
        trainer.load_model(selected_model)
        trainer.epsilon = 0.0  # بدون استكشاف

        wins = 0
        losses = 0
        draws = 0

        test_progress = st.progress(0)
        test_status = st.empty()

        for i in range(1, test_games + 1):
            _, result = trainer._play_one_game()

            if result.startswith('win'):
                wins += 1
            elif result.startswith('loss'):
                losses += 1
            else:
                draws += 1

            test_progress.progress(i / test_games)

            if i % 10 == 0:
                wr = wins / i
                test_status.markdown(
                    f"**{i}/{test_games}** | "
                    f"فوز: {wins} | خسارة: {losses} | "
                    f"تعادل: {draws} | نسبة: {wr:.1%}"
                )

        test_progress.progress(1.0)

        # النتائج
        st.markdown("### 📊 نتائج الاختبار")

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            wr_pct = wins / test_games if test_games else 0
            ring_svg = UIComponents.progress_ring(
                wr_pct, "نسبة الفوز", color="#4CAF50"
            )
            st.markdown(ring_svg, unsafe_allow_html=True)
        with tc2:
            st.metric("فوز 🏆", wins)
            st.metric("خسارة 😔", losses)
        with tc3:
            st.metric("تعادل 🤝", draws)
            st.metric(
                "الإجمالي", test_games
            )


# ═══════════════════════════════════════════════
# تبويب النماذج
# ═══════════════════════════════════════════════

with tab_models:
    st.markdown("### 📦 إدارة النماذج")

    model_dir = Path("models/trained")
    model_dir.mkdir(parents=True, exist_ok=True)

    pkl_files = sorted(
        model_dir.glob("*.pkl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not pkl_files:
        st.info(
            "لا توجد نماذج مدربة بعد. "
            "اذهب لتبويب التدريب للبدء."
        )
    else:
        for f in pkl_files:
            stat = f.stat()
            size_kb = stat.st_size / 1024
            modified = time.strftime(
                '%Y-%m-%d %H:%M',
                time.localtime(stat.st_mtime)
            )

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(
                    f"**📄 {f.name}**  \n"
                    f"الحجم: {size_kb:.0f} KB | "
                    f"آخر تعديل: {modified}"
                )

            with col2:
                with open(f, 'rb') as fp:
                    st.download_button(
                        "📥 تنزيل",
                        data=fp.read(),
                        file_name=f.name,
                        mime="application/octet-stream",
                        key=f"dl_{f.name}",
                        use_container_width=True,
                    )

            with col3:
                if st.button(
                    "🗑️ حذف",
                    key=f"del_{f.name}",
                    use_container_width=True,
                ):
                    os.remove(f)
                    st.rerun()

            st.markdown("---")

    # رفع نموذج
    st.markdown("### 📤 رفع نموذج")

    uploaded = st.file_uploader(
        "اختر ملف نموذج (.pkl)",
        type=['pkl'],
    )

    if uploaded:
        save_path = model_dir / uploaded.name
        with open(save_path, 'wb') as f:
            f.write(uploaded.getbuffer())
        st.success(f"✅ تم رفع النموذج: {uploaded.name}")
        st.rerun()

    # إحصائيات التدريب
    st.markdown("---")
    st.markdown("### 📈 إحصائيات التدريب")

    log_dir = Path("logs")
    stats_files = list(log_dir.glob("training_stats_*.json"))

    if stats_files:
        latest = max(
            stats_files,
            key=lambda f: f.stat().st_mtime
        )

        with open(latest, 'r') as f:
            stats_data = json.load(f)

        sc1, sc2, sc3, sc4 = st.columns(4)

        with sc1:
            st.metric(
                "الحلقات",
                Formatter.format_number(
                    stats_data.get('episode', 0)
                )
            )
        with sc2:
            st.metric(
                "إجمالي الفوز",
                stats_data.get('total_wins', 0)
            )
        with sc3:
            st.metric(
                "نسبة الفوز",
                f"{stats_data.get('win_rate', 0):.1%}"
            )
        with sc4:
            st.metric(
                "حجم الجدول",
                Formatter.format_number(
                    stats_data.get('q_table_size', 0)
                )
            )
    else:
        st.info("لا توجد إحصائيات تدريب بعد")
