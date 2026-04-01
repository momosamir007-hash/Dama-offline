import streamlit as st

st.set_page_config(
    page_title="🎮 اللعب",
    page_icon="🎮",
    layout="wide",
)

st.markdown("## 🎮 صفحة اللعب")
st.info("اللعبة الرئيسية في الصفحة الأولى (app)")

# لا نستخدم st.page_link
st.markdown(
    "[← الرجوع للعبة الرئيسية](/)",
    unsafe_allow_html=False,
)
