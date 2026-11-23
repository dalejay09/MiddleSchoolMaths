import streamlit as st

# 1. Page Config MUST be the first Streamlit command
st.set_page_config(page_title="Middle School Maths", page_icon="📐", layout="centered")

# 2. Import active maths modules
import area_perimeter_module as area_perimeter

# 3. Tab-reset handler
def handle_nav_change():
    st.session_state.ap_generating = True
    st.session_state.ap_pdf_bytes = None

# 4. Clean Horizontal Tab Navigation
st.markdown("""
    <style>
    div[role="radiogroup"] {
        justify-content: center;
        gap: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

selected_app = st.radio(
    "Navigation",
    ["Area & Perimeter", "Fractions & Decimals", "Algebra", "Angles & Geometry", "Statistics"],
    horizontal=True,
    label_visibility="collapsed",
    on_change=handle_nav_change
)

st.markdown("<hr style='margin: 0.2em 0px 1.5em 0px; border-color: #444;'>", unsafe_allow_html=True)

# 5. Route to the active module
if selected_app == "Area & Perimeter":
    area_perimeter.run_app()
elif selected_app == "Fractions & Decimals":
    st.info("🍰 Fractions & Decimals module is under construction.")
elif selected_app == "Algebra":
    st.info("✖️ Algebra module is under construction.")
elif selected_app == "Angles & Geometry":
    st.info("📐 Angles & Geometry module is under construction.")
elif selected_app == "Statistics":
    st.info("📊 Statistics module is under construction.")