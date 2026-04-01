"""
📷 صفحة الكاميرا
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

from game_engine.domino_board import DominoTile
from streamlit_utils import SessionManager

st.set_page_config(
    page_title="📷 الكاميرا",
    page_icon="📷",
    layout="wide",
)

SessionManager.init()

st.markdown("""
<h1 style="text-align:center;
background:linear-gradient(90deg,#FF6B6B,#FFE66D);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
font-size:2em;">
📷 كاميرا الدومينو
</h1>
<p style="text-align:center;color:#888;">
صوّر أحجارك أو الطاولة
</p>
""", unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════
# تصوير أحجار اليد
# ═══════════════════════════════

st.markdown("### 🃏 تصوير أحجار يدك")

tab_camera, tab_upload, tab_manual = st.tabs([
    "📷 الكاميرا",
    "📁 رفع صورة",
    "✏️ إدخال يدوي",
])

with tab_camera:
    st.markdown("#### 📷 التقط صورة لأحجارك")

    camera_photo = st.camera_input(
        "وجّه الكاميرا نحو أحجارك",
        key="hand_camera",
    )

    if camera_photo:
        st.image(
            camera_photo,
            caption="📸 الصورة الملتقطة",
            use_container_width=True,
        )
        st.success("✅ تم التقاط الصورة!")
        st.info(
            "🔜 الاكتشاف التلقائي قيد التطوير.\n"
            "أدخل الأحجار يدوياً في تبويب 'إدخال يدوي'"
        )
        SessionManager.set('captured_hand_photo', camera_photo)


with tab_upload:
    st.markdown("#### 📁 ارفع صورة لأحجارك")

    uploaded = st.file_uploader(
        "اختر صورة",
        type=['jpg', 'jpeg', 'png', 'webp'],
        key="hand_upload",
    )

    if uploaded:
        st.image(
            uploaded,
            caption="📸 الصورة المرفوعة",
            use_container_width=True,
        )
        st.success("✅ تم رفع الصورة!")
        st.info(
            "🔜 الاكتشاف التلقائي قيد التطوير.\n"
            "أدخل الأحجار يدوياً في تبويب 'إدخال يدوي'"
        )


with tab_manual:
    st.markdown("#### ✏️ أدخل أحجارك يدوياً")
    st.caption("الصيغة: `6-4 5-5 3-1 2-0 4-3 6-6 1-0`")

    # عرض الصورة لو التقطها
    photo = SessionManager.get('captured_hand_photo')
    if photo:
        st.image(
            photo,
            caption="📸 صورتك (للمرجع)",
            width=300,
        )

    text_input = st.text_input(
        "الأحجار (مفصولة بمسافات)",
        placeholder="6-4 5-5 3-1 2-0 4-3 6-6 1-0",
        key="manual_tiles_text",
    )

    if text_input:
        tiles = []
        errors = []

        parts = text_input.strip().split()
        for part in parts:
            try:
                nums = part.replace('|', '-').split('-')
                if len(nums) == 2:
                    a, b = int(nums[0]), int(nums[1])
                    if 0 <= a <= 6 and 0 <= b <= 6:
                        tiles.append(DominoTile(a, b))
                    else:
                        errors.append(f"❌ خارج النطاق: {part}")
                else:
                    errors.append(f"❌ صيغة خاطئة: {part}")
            except ValueError:
                errors.append(f"❌ غير صحيح: {part}")

        for e in errors:
            st.error(e)

        if tiles:
            # عرض الأحجار كنص
            tiles_str = " ".join(
                f"[{t.high}|{t.low}]" for t in tiles
            )
            st.success(
                f"✅ {len(tiles)} حجر: {tiles_str}"
            )

            total = sum(t.total for t in tiles)
            st.caption(f"مجموع النقاط: {total}")

            if len(tiles) == 7:
                if st.button(
                    "🎮 استخدم هذه الأحجار!",
                    type="primary",
                    use_container_width=True,
                ):
                    SessionManager.set(
                        'my_hand_input', tiles
                    )
                    SessionManager.set(
                        'game_phase', 'setup'
                    )
                    st.success(
                        "✅ تم! اذهب للصفحة الرئيسية "
                        "واضغط 'ابدأ اللعب'"
                    )
            elif len(tiles) > 7:
                st.error(
                    f"❌ أدخلت {len(tiles)} حجر! "
                    f"المطلوب 7 فقط"
                )
            else:
                st.warning(
                    f"⚠️ {len(tiles)}/7 - "
                    f"تحتاج {7-len(tiles)} أحجار أخرى"
                )


st.markdown("---")


# ═══════════════════════════════
# تصوير الطاولة
# ═══════════════════════════════

st.markdown("### 🎯 تصوير الطاولة")

table_tab1, table_tab2 = st.tabs([
    "📷 كاميرا",
    "📁 رفع صورة",
])

with table_tab1:
    table_photo = st.camera_input(
        "صوّر الطاولة",
        key="table_camera",
    )
    if table_photo:
        st.image(
            table_photo,
            caption="📸 صورة الطاولة",
            use_container_width=True,
        )
        st.info("💡 انظر للأحجار وأدخلها في اللعبة")

with table_tab2:
    table_upload = st.file_uploader(
        "ارفع صورة الطاولة",
        type=['jpg', 'jpeg', 'png', 'webp'],
        key="table_upload",
    )
    if table_upload:
        st.image(
            table_upload,
            caption="📸 الطاولة",
            use_container_width=True,
        )


st.markdown("---")

# نصائح
st.markdown("### 💡 نصائح التصوير")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    **💡 الإضاءة**
    - إضاءة جيدة
    - بدون ظلال
    """)
with c2:
    st.markdown("""
    **📐 الزاوية**
    - من الأعلى مباشرة
    - الأحجار واضحة
    """)
with c3:
    st.markdown("""
    **🎯 الوضوح**
    - ثبّت الكاميرا
    - قرّب بما يكفي
    """)

st.markdown("---")
st.markdown("[← الرجوع للعبة الرئيسية](/)")
