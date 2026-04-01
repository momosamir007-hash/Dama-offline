# pages/3_📊_Analytics.py
"""
📊 صفحة التحليلات والإحصائيات
تعرض:
  - إحصائيات اللاعب الشاملة
  - رسوم بيانية تفاعلية
  - تحليل الأنماط
  - أفضل الاستراتيجيات
"""

import streamlit as st
import os
import sys
import json
from datetime import datetime, timedelta
from collections import Counter

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, ROOT)

from game_engine.domino_board import DominoTile
from svg_renderer import DominoSVG, TileTheme
from streamlit_utils import (
    SessionManager, UIComponents, PlayerStats,
    Formatter, NotificationManager,
)


# ──────────────────────────────────────────────
# إعداد الصفحة
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="📊 التحليلات - الدومينو الذكي",
    page_icon="📊",
    layout="wide",
)

SessionManager.init()

st.markdown("""
<div style="text-align: center; padding: 10px 0 20px 0;">
    <h1 style="
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2em;
    ">
        📊 لوحة التحليلات
    </h1>
    <p style="color: #888;">
        تابع أداءك واكتشف نقاط قوتك وضعفك
    </p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# تحميل الإحصائيات
# ──────────────────────────────────────────────

stats = PlayerStats.get_stats()
total_games = stats.get('total_games', 0)


# ──────────────────────────────────────────────
# البطاقات الرئيسية
# ──────────────────────────────────────────────

st.markdown("### 📋 نظرة عامة")

if total_games == 0:
    st.info(
        "🎮 لم تلعب أي مباراة بعد! "
        "اذهب لصفحة اللعب وابدأ مباراتك الأولى."
    )
    st.stop()

wins = stats.get('wins', 0)
losses = stats.get('losses', 0)
draws = stats.get('draws', 0)
win_rate = wins / total_games if total_games else 0

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(UIComponents.metric_card(
        "مباريات",
        total_games,
        "🎮", "#2196F3",
    ), unsafe_allow_html=True)

with c2:
    st.markdown(UIComponents.metric_card(
        "فوز",
        wins,
        "🏆", "#4CAF50",
    ), unsafe_allow_html=True)

with c3:
    st.markdown(UIComponents.metric_card(
        "خسارة",
        losses,
        "😔", "#F44336",
    ), unsafe_allow_html=True)

with c4:
    st.markdown(UIComponents.metric_card(
        "تعادل",
        draws,
        "🤝", "#FF9800",
    ), unsafe_allow_html=True)

with c5:
    ring = UIComponents.progress_ring(
        win_rate, "نسبة الفوز",
        color="#4CAF50" if win_rate >= 0.5 else "#F44336"
    )
    st.markdown(ring, unsafe_allow_html=True)


st.markdown("---")


# ──────────────────────────────────────────────
# تبويبات التحليل
# ──────────────────────────────────────────────

tab_overview, tab_tiles, tab_history, tab_streaks = st.tabs([
    "📈 الأداء",
    "🎲 الأحجار",
    "📜 السجل",
    "🔥 السلاسل",
])


# ═══════════════════════════════════════════════
# تبويب الأداء
# ═══════════════════════════════════════════════

with tab_overview:
    st.markdown("### 📈 تحليل الأداء")

    # رسم بياني - نتائج آخر المباريات
    history = stats.get('game_history', [])

    if history:
        st.markdown("#### آخر المباريات")

        # تحويل لقيم رقمية
        results_numeric = []
        labels = []
        cumulative_wr = []
        running_wins = 0

        for i, game in enumerate(history[-50:], 1):
            if game['result'] == 'win':
                results_numeric.append(1)
                running_wins += 1
            elif game['result'] == 'loss':
                results_numeric.append(-1)
            else:
                results_numeric.append(0)

            labels.append(f"مباراة {i}")
            cumulative_wr.append(running_wins / i)

        # رسم نسبة الفوز التراكمية
        st.line_chart(
            {"نسبة الفوز التراكمية": cumulative_wr},
            use_container_width=True,
        )

        # رسم النتائج
        st.bar_chart(
            {"النتيجة": results_numeric},
            use_container_width=True,
        )

    # إحصائيات إضافية
    st.markdown("#### 📊 إحصائيات عامة")

    total_moves = stats.get('total_moves', 0)
    avg_moves = (
        total_moves / total_games if total_games else 0
    )
    total_points_won = stats.get('total_points_won', 0)
    total_points_lost = stats.get('total_points_lost', 0)

    sc1, sc2, sc3, sc4 = st.columns(4)

    with sc1:
        st.metric(
            "إجمالي الحركات",
            Formatter.format_number(total_moves)
        )
    with sc2:
        st.metric(
            "متوسط الحركات/مباراة",
            f"{avg_moves:.1f}"
        )
    with sc3:
        st.metric(
            "نقاط مكتسبة",
            Formatter.format_number(total_points_won)
        )
    with sc4:
        st.metric(
            "نقاط مفقودة",
            Formatter.format_number(total_points_lost)
        )

    # توزيع النتائج
    st.markdown("#### 🥧 توزيع النتائج")

    dist_data = {
        "الفئة": ["فوز 🏆", "خسارة 😔", "تعادل 🤝"],
        "العدد": [wins, losses, draws],
    }

    # نعرض كـ أعمدة بدل pie chart لأن streamlit
    # ما يدعم pie مباشرة
    st.bar_chart(
        data={"العدد": [wins, losses, draws]},
        use_container_width=True,
    )

    # مدة اللعب
    durations = stats.get('game_durations', [])
    if durations:
        avg_duration = sum(durations) / len(durations)
        st.markdown(
            f"⏱️ متوسط مدة المباراة: "
            f"**{Formatter.format_duration(avg_duration)}**"
        )


# ═══════════════════════════════════════════════
# تبويب الأحجار
# ═══════════════════════════════════════════════

with tab_tiles:
    st.markdown("### 🎲 تحليل الأحجار")

    tiles_played = stats.get('tiles_played', {})

    if not tiles_played:
        st.info("لا توجد بيانات أحجار بعد")
    else:
        renderer = DominoSVG(theme=TileTheme.MODERN)

        # الأحجار الأكثر لعباً
        st.markdown("#### 🔝 الأحجار الأكثر لعباً")

        sorted_tiles = sorted(
            tiles_played.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # عرض أعلى 10
        top_tiles_data = {}
        for tile_key, count in sorted_tiles[:10]:
            parts = tile_key.split('-')
            h, l = int(parts[0]), int(parts[1])
            label = f"[{h}|{l}]"
            top_tiles_data[label] = count

        st.bar_chart(
            top_tiles_data,
            use_container_width=True,
        )

        # الحجر المفضل
        if sorted_tiles:
            fav_key = sorted_tiles[0][0]
            fav_count = sorted_tiles[0][1]
            parts = fav_key.split('-')
            fav_tile = DominoTile(int(parts[0]), int(parts[1]))

            st.markdown("#### ⭐ حجرك المفضل")

            fc1, fc2 = st.columns([1, 2])

            with fc1:
                fav_svg = renderer.render_single_tile_large(
                    fav_tile,
                    label=f"لعبته {fav_count} مرة"
                )
                st.markdown(fav_svg, unsafe_allow_html=True)

            with fc2:
                st.markdown(f"""
                - **الحجر:** [{fav_tile.high}|{fav_tile.low}]
                - **المجموع:** {fav_tile.total} نقطة
                - **مرات اللعب:** {fav_count}
                - **النوع:** {'دبل' if fav_tile.is_double else 'عادي'}
                """)

        # تحليل الأرقام المفضلة
        st.markdown("#### 🔢 الأرقام المفضلة")

        number_counts = Counter()
        for tile_key, count in tiles_played.items():
            parts = tile_key.split('-')
            h, l = int(parts[0]), int(parts[1])
            number_counts[h] += count
            if h != l:
                number_counts[l] += count

        num_data = {
            f"الرقم {i}": number_counts.get(i, 0)
            for i in range(7)
        }
        st.bar_chart(num_data, use_container_width=True)

        # الدبل vs العادي
        st.markdown("#### 🎯 دبل vs عادي")

        doubles_count = 0
        normal_count = 0
        for tile_key, count in tiles_played.items():
            parts = tile_key.split('-')
            if parts[0] == parts[1]:
                doubles_count += count
            else:
                normal_count += count

        dc1, dc2 = st.columns(2)
        with dc1:
            st.metric("دبل 🔴", doubles_count)
        with dc2:
            st.metric("عادي ⚪", normal_count)

        if doubles_count + normal_count > 0:
            double_pct = (
                doubles_count /
                (doubles_count + normal_count)
            )
            st.progress(
                double_pct,
                text=f"نسبة الدبل: {double_pct:.0%}"
            )


# ═══════════════════════════════════════════════
# تبويب السجل
# ═══════════════════════════════════════════════

with tab_history:
    st.markdown("### 📜 سجل المباريات")

    history = stats.get('game_history', [])

    if not history:
        st.info("لا توجد مباريات مسجلة")
    else:
        # فلترة
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            result_filter = st.multiselect(
                "فلترة حسب النتيجة",
                ["win", "loss", "draw"],
                default=["win", "loss", "draw"],
                format_func=lambda x: {
                    'win': '🏆 فوز',
                    'loss': '😔 خسارة',
                    'draw': '🤝 تعادل'
                }.get(x, x)
            )

        with filter_col2:
            sort_order = st.radio(
                "الترتيب",
                ["الأحدث أولاً", "الأقدم أولاً"],
                horizontal=True,
            )

        # فلترة وترتيب
        filtered = [
            g for g in history
            if g['result'] in result_filter
        ]

        if sort_order == "الأحدث أولاً":
            filtered = list(reversed(filtered))

        st.caption(
            f"عرض {len(filtered)} من {len(history)} مباراة"
        )

        # عرض المباريات
        for i, game in enumerate(filtered[:50]):
            result_icon = {
                'win': '🏆',
                'loss': '😔',
                'draw': '🤝'
            }.get(game['result'], '❓')

            result_text = {
                'win': 'فوز',
                'loss': 'خسارة',
                'draw': 'تعادل'
            }.get(game['result'], '؟')

            result_color = {
                'win': '#4CAF50',
                'loss': '#F44336',
                'draw': '#FF9800'
            }.get(game['result'], '#999')

            date_str = game.get('date', '')
            try:
                dt = datetime.fromisoformat(date_str)
                date_display = dt.strftime('%Y/%m/%d %H:%M')
            except (ValueError, TypeError):
                date_display = date_str

            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.03);
                border-left: 4px solid {result_color};
                border-radius: 0 8px 8px 0;
                padding: 12px 16px;
                margin: 6px 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <div>
                    <span style="font-size: 20px;">
                        {result_icon}
                    </span>
                    <strong style="color: {result_color};">
                        {result_text}
                    </strong>
                    <span style="color: #888; margin-right: 10px;">
                        | {game.get('moves', 0)} حركة
                    </span>
                </div>
                <div style="color: #666; font-size: 12px;">
                    {date_display}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# تبويب السلاسل
# ═══════════════════════════════════════════════

with tab_streaks:
    st.markdown("### 🔥 سلاسل الفوز")

    best_streak = stats.get('best_streak', 0)
    current_streak = stats.get('current_streak', 0)

    sc1, sc2 = st.columns(2)

    with sc1:
        st.markdown(UIComponents.metric_card(
            "أفضل سلسلة فوز",
            f"{best_streak} 🔥",
            "🏅", "#FFD700",
        ), unsafe_allow_html=True)

    with sc2:
        streak_color = (
            "#4CAF50" if current_streak > 0
            else "#999"
        )
        st.markdown(UIComponents.metric_card(
            "السلسلة الحالية",
            f"{current_streak}",
            "⚡", streak_color,
        ), unsafe_allow_html=True)

    # تحليل السلاسل من السجل
    history = stats.get('game_history', [])

    if history:
        st.markdown("#### 📊 تحليل السلاسل")

        streaks = []
        current = 0
        streak_type = None

        for game in history:
            if game['result'] == 'win':
                if streak_type == 'win':
                    current += 1
                else:
                    if current > 0 and streak_type:
                        streaks.append(
                            (streak_type, current)
                        )
                    current = 1
                    streak_type = 'win'
            else:
                if streak_type and streak_type != 'win':
                    current += 1
                else:
                    if current > 0 and streak_type:
                        streaks.append(
                            (streak_type, current)
                        )
                    current = 1
                    streak_type = 'other'

        if current > 0 and streak_type:
            streaks.append((streak_type, current))

        # عرض السلاسل
        win_streaks = [
            s[1] for s in streaks if s[0] == 'win'
        ]

        if win_streaks:
            st.bar_chart(
                {"طول السلسلة": win_streaks},
                use_container_width=True,
            )

            avg_streak = (
                sum(win_streaks) / len(win_streaks)
            )
            st.markdown(
                f"متوسط سلسلة الفوز: "
                f"**{avg_streak:.1f}** مباراة"
            )

    # الإنجازات
    st.markdown("---")
    st.markdown("### 🏅 الإنجازات")

    achievements = [
        ("🎮 مبتدئ", "العب أول مباراة", total_games >= 1),
        ("🏆 فائز", "اربح أول مباراة", wins >= 1),
        ("🔟 خبير", "العب 10 مباريات", total_games >= 10),
        ("💯 محترف", "العب 100 مباراة", total_games >= 100),
        ("🔥 سلسلة 3", "اربح 3 مباريات متتالية", best_streak >= 3),
        ("🔥 سلسلة 5", "اربح 5 مباريات متتالية", best_streak >= 5),
        ("🔥 سلسلة 10", "اربح 10 مباريات متتالية", best_streak >= 10),
        ("⚖️ متوازن", "نسبة فوز 50%+", win_rate >= 0.5),
        ("👑 بطل", "نسبة فوز 70%+", win_rate >= 0.7),
    ]

    ach_cols = st.columns(3)
    for i, (icon_name, desc, unlocked) in enumerate(achievements):
        with ach_cols[i % 3]:
            opacity = "1.0" if unlocked else "0.3"
            check = "✅" if unlocked else "🔒"

            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 16px;
                margin: 8px 0;
                text-align: center;
                opacity: {opacity};
                border: 1px solid {'#4CAF50' if unlocked else '#333'};
            ">
                <div style="font-size: 28px;">
                    {icon_name}
                </div>
                <div style="font-size: 12px; color: #aaa;
                            margin-top: 4px;">
                    {desc}
                </div>
                <div style="margin-top: 4px;">
                    {check}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# الشريط الجانبي
# ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 ملخص سريع")

    st.metric("إجمالي المباريات", total_games)
    st.metric(
        "نسبة الفوز",
        Formatter.format_percentage(win_rate)
    )
    st.metric("أفضل سلسلة", best_streak)

    fav = PlayerStats.get_favorite_tile()
    if fav:
        st.metric("الحجر المفضل", f"[{fav}]")

    st.markdown("---")

    if st.button(
        "🗑️ مسح الإحصائيات",
        use_container_width=True,
    ):
        if st.checkbox("متأكد؟"):
            PlayerStats.reset()
            NotificationManager.show_toast(
                "تم مسح الإحصائيات", "warning"
            )
            st.rerun()

    st.markdown("---")

    # تصدير
    if total_games > 0:
        stats_json = json.dumps(
            stats, ensure_ascii=False, indent=2
        )
        st.download_button(
            "📥 تصدير الإحصائيات",
            data=stats_json,
            file_name="domino_stats.json",
            mime="application/json",
            use_container_width=True,
        )
