"""
📷 صفحة الكاميرا - تصوير الطاولة والأحجار
تدعم:
  - تصوير أحجار اليد
  - تصوير الطاولة
  - إدخال يدوي بعد المعاينة
"""
import streamlit as st
import sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game_engine.domino_board import DominoTile
from streamlit_utils import SessionManager, generate_all_tiles

st.set_page_config(
    page_title="📷 الكاميرا - الدومينو الذكي",
    page_icon="📷",
    layout="wide",
)

SessionManager.init()

st.markdown("""
<h1 style="text-align:center;
background:linear-gradient(90deg,#FF6B6B,#FFE66D);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
font-size:2em;">
📷 كاميرا الدومينو
</h1>
<p style="text-align:center;color:#888;">
صوّر أحجارك أو الطاولة وسيساعدك الذكاء الاصطناعي
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════
# تصوير أحجار اليد
# ═══════════════════════════════════

st.markdown("### 🃏 تصوير أحجار يدك")
st.caption(
    "صوّر أحجارك ثم أدخلها يدوياً بالأسفل "
    "(الاكتشاف التلقائي قريباً!)"
)

tab_camera, tab_upload, tab_manual = st.tabs([
    "📷 الكاميرا",
    "📁 رفع صورة",
    "✏️ إدخال يدوي",
])


# ─── الكاميرا ───
with tab_camera:
    st.markdown("#### 📷 التقط صورة لأحجارك")

    camera_photo = st.camera_input(
        "وجّه الكاميرا نحو أحجارك",
        key="hand_camera",
    )

    if camera_photo:
        st.image(camera_photo, caption="📸 الصورة الملتقطة", use_container_width=True)

        st.success("✅ تم التقاط الصورة!")
        st.info(
            "🔜 الاكتشاف التلقائي قيد التطوير.\n"
            "الآن أدخل الأحجار يدوياً في تبويب 'إدخال يدوي'"
        )

        # حفظ الصورة في الحالة
        SessionManager.set('captured_hand_photo', camera_photo)


# ─── رفع صورة ───
with tab_upload:
    st.markdown("#### 📁 ارفع صورة لأحجارك")

    uploaded = st.file_uploader(
        "اختر صورة",
        type=['jpg', 'jpeg', 'png', 'webp'],
        key="hand_upload",
    )

    if uploaded:
        st.image(uploaded, caption="📸 الصورة المرفوعة", use_container_width=True)

        st.success("✅ تم رفع الصورة!")
        st.info(
            "🔜 الاكتشاف التلقائي قيد التطوير.\n"
            "الآن أدخل الأحجار يدوياً في تبويب 'إدخال يدوي'"
        )


# ─── إدخال يدوي ───
with tab_manual:
    st.markdown("#### ✏️ أدخل أحجارك يدوياً")
    st.caption("اختر 7 أحجار من القائمة")

    # عرض الصورة إذا التقطتها
    photo = SessionManager.get('captured_hand_photo')
    if photo:
        col_img, col_input = st.columns([1, 2])
        with col_img:
            st.image(photo, caption="📸 صورتك", use_container_width=True)
    else:
        col_input = st.container()

    with col_input if not photo else col_input:
        # إدخال سريع
        st.markdown("**أدخل الأحجار بصيغة: `6-4 5-5 3-1`**")

        text_input = st.text_input(
            "الأحجار (مفصولة بمسافات)",
            placeholder="6-4 5-5 3-1 2-0 4-3 6-6 1-0",
            key="manual_tiles_text",
        )

        if text_input:
            tiles = []
            parts = text_input.strip().split()
            errors = []

            for part in parts:
                try:
                    nums = part.split('-')
                    if len(nums) == 2:
                        a, b = int(nums[0]), int(nums[1])
                        if 0 <= a <= 6 and 0 <= b <= 6:
                            tiles.append(DominoTile(a, b))
                        else:
                            errors.append(f"❌ رقم خارج النطاق: {part}")
                    else:
                        errors.append(f"❌ صيغة خاطئة: {part}")
                except ValueError:
                    errors.append(f"❌ إدخال غير صحيح: {part}")

            if errors:
                for e in errors:
                    st.error(e)

            if tiles:
                st.success(f"✅ تم التعرف على {len(tiles)} حجر: {tiles}")

                # عرض الأحجار
                from svg_renderer import DominoSVG
                renderer = DominoSVG()
                renderer.display_hand(tiles, title="الأحجار المُدخلة")

                if len(tiles) == 7:
                    if st.button(
                        "🎮 استخدم هذه الأحجار وابدأ اللعب!",
                        type="primary",
                        use_container_width=True,
                    ):
                        SessionManager.set('my_hand_input', tiles)
                        SessionManager.set('game_phase', 'setup')
                        st.success("✅ تم! اذهب للصفحة الرئيسية واضغط 'ابدأ اللعب'")
                        st.page_link("app.py", label="← الرجوع للعبة", icon="🎲")
                else:
                    st.warning(f"⚠️ أدخلت {len(tiles)} حجر. تحتاج 7 بالضبط.")


st.markdown("---")


# ═══════════════════════════════════
# تصوير الطاولة
# ═══════════════════════════════════

st.markdown("### 🎯 تصوير الطاولة")
st.caption("صوّر الطاولة لمعرفة الأحجار الملعوبة")

table_tab1, table_tab2 = st.tabs(["📷 كاميرا", "📁 رفع صورة"])

with table_tab1:
    table_photo = st.camera_input(
        "وجّه الكاميرا نحو الطاولة",
        key="table_camera",
    )

    if table_photo:
        st.image(table_photo, caption="📸 صورة الطاولة", use_container_width=True)
        st.info("💡 انظر للأحجار على الطاولة وأدخلها في اللعبة يدوياً")

with table_tab2:
    table_upload = st.file_uploader(
        "ارفع صورة الطاولة",
        type=['jpg', 'jpeg', 'png', 'webp'],
        key="table_upload",
    )

    if table_upload:
        st.image(table_upload, caption="📸 صورة الطاولة", use_container_width=True)
        st.info("💡 انظر للأحجار على الطاولة وأدخلها في اللعبة يدوياً")


st.markdown("---")


# ═══════════════════════════════════
# نصائح التصوير
# ═══════════════════════════════════

st.markdown("### 💡 نصائح للتصوير الأفضل")

tips_cols = st.columns(3)

with tips_cols[0]:
    st.markdown("""
    #### 💡 الإضاءة
    - استخدم إضاءة جيدة
    - تجنب الظلال القوية
    - الضوء الطبيعي الأفضل
    """)

with tips_cols[1]:
    st.markdown("""
    #### 📐 الزاوية
    - صوّر من الأعلى مباشرة
    - اجعل الأحجار واضحة
    - لا تقطع أي حجر
    """)

with tips_cols[2]:
    st.markdown("""
    #### 🎯 الوضوح
    - ثبّت الكاميرا
    - قرّب بما يكفي
    - تأكد من وضوح النقاط
    """)


# ═══════════════════════════════════
# الرجوع للعبة
# ═══════════════════════════════════

st.markdown("---")
st.page_link("app.py", label="← الرجوع للعبة الرئيسية", icon="🎲")
