import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streamlit_utils import PlayerStats, Formatter

st.set_page_config(page_title="📊 التحليلات", page_icon="📊", layout="wide")

st.markdown("""
<h1 style="text-align:center;
background:linear-gradient(90deg,#667eea,#764ba2);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
font-size:2em;">📊 لوحة التحليلات</h1>
""", unsafe_allow_html=True)

stats = PlayerStats.get_stats()
total = stats.get('total_games', 0)

if total == 0:
    st.info("🎮 العب مباراتك الأولى لترى الإحصائيات!")
    st.page_link("app.py", label="← ابدأ اللعب", icon="🎲")
    st.stop()

wins = stats.get('wins', 0)
losses = stats.get('losses', 0)
draws = stats.get('draws', 0)
wr = wins / total

c1, c2, c3, c4 = st.columns(4)
c1.metric("🎮 مباريات", total)
c2.metric("🏆 فوز", wins)
c3.metric("😔 خسارة", losses)
c4.metric("📈 نسبة الفوز", f"{wr:.0%}")

st.markdown("---")

history = stats.get('game_history', [])
if history:
    st.markdown("### 📈 تطور الأداء")
    rw = 0
    cum = []
    for i, g in enumerate(history[-50:], 1):
        if g['result'] == 'win': rw += 1
        cum.append(rw / i)
    st.line_chart({"نسبة الفوز": cum})

    st.markdown("### 📜 آخر المباريات")
    for g in reversed(history[-10:]):
        ic = {'win': '🏆', 'loss': '😔', 'draw': '🤝'}.get(g['result'], '❓')
        st.markdown(f"- {ic} {g.get('date', '')[:16]} | {g.get('moves', 0)} حركة")

st.markdown("---")
st.metric("🔥 أفضل سلسلة فوز", stats.get('best_streak', 0))

if st.sidebar.button("🗑️ مسح الإحصائيات"):
    PlayerStats.reset()
    st.rerun()
