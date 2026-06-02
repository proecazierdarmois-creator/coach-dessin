import streamlit as st

from auth import show_login
from utils import ensure_profile
from dashboard import show_dashboard

st.set_page_config(
    page_title="Coach de dessin IA",
    page_icon="🎨",
    layout="wide",
)

if "email" not in st.session_state:
    st.session_state.email = None

if "profile" not in st.session_state:
    st.session_state.profile = None

if not st.session_state.email:
    show_login()

email = st.session_state.email
profile = ensure_profile(email)

if profile is None:
    st.error("Impossible de charger le profil.")
    st.stop()

st.session_state.profile = profile

show_dashboard(profile, email)