"""
📊 صفحة التحليلات
"""
import streamlit as st
import sys
import os

# إصلاح المسار
ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from streamlit_utils import PlayerStats, Formatter

st.set_page_config(
    page_title="📊 التحليلات",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<h1 style="text-align:center;
background:linear-gradient(90deg,#667eea,#764ba2);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
font-size:2em;">
📊 لوحة التحليلات
</h1>
""", unsafe_allow_html=True)

stats = PlayerStats.get_stats()
total = stats.get('total_games', 0)

if total == 0:
    st.info("🎮 العب مباراتك الأولى لترى الإحصائيات!")
    st.markdown("[← ابدأ اللعب](/)")
    st.stop()

wins = stats.get('wins', 0)
losses = stats.get('losses', 0)
draws = stats.get('draws', 0)
wr = wins / total if total > 0 else 0

# ─── البطاقات ───
c1, c2, c3, c4 = st.columns(4)
c1.metric("🎮 مباريات", total)
c2.metric("🏆 فوز", wins)
c3.metric("😔 خسارة", losses)
c4.metric("📈 نسبة الفوز", f"{wr:.0%}")

st.markdown("---")

# ─── الرسم البياني ───
history = stats.get('game_history', [])

if history:
    st.markdown("### 📈 تطور الأداء")

    running_wins = 0
    cumulative = []
    for i, g in enumerate(history[-50:], 1):
        if g['result'] == 'win':
            running_wins += 1
        cumulative.append(running_wins / i)

    st.line_chart({"نسبة الفوز التراكمية": cumulative})

    st.markdown("### 📜 آخر المباريات")

    for g in reversed(history[-15:]):
        icon = {
            'win': '🏆',
            'loss': '😔',
            'draw': '🤝',
        }.get(g['result'], '❓')

        date = g.get('date', '')[:16]
        moves = g.get('moves', 0)

        st.markdown(f"- {icon} {date} | {moves} حركة")

st.markdown("---")

# ─── السلاسل ───
best_streak = stats.get('best_streak', 0)
current_streak = stats.get('current_streak', 0)

s1, s2 = st.columns(2)
s1.metric("🔥 أفضل سلسلة فوز", best_streak)
s2.metric("⚡ السلسلة الحالية", current_streak)

st.markdown("---")

# ─── إحصائيات إضافية ───
total_moves = stats.get('total_moves', 0)
avg_moves = total_moves / total if total > 0 else 0

m1, m2 = st.columns(2)
m1.metric("🎯 إجمالي الحركات", total_moves)
m2.metric("📊 متوسط الحركات/مباراة", f"{avg_moves:.1f}")

# ─── الشريط الجانبي ───
with st.sidebar:
    st.markdown("## 📊 الإحصائيات")
    st.metric("المباريات", total)
    st.metric("نسبة الفوز", f"{wr:.0%}")

    st.markdown("---")

    if st.button(
        "🗑️ مسح الإحصائيات",
        use_container_width=True,
    ):
        PlayerStats.reset()
        st.rerun()

st.markdown("---")
st.markdown("[← الرجوع للعبة الرئيسية](/)")
