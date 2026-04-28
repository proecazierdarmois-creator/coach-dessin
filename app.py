import streamlit as st
from auth import show_login
from utils import ensure_profile
from dashboard import show_dashboard

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# LOGIN
if not st.user.is_logged_in:
    show_login()

# CONNECTÉ
email = st.user.email
profile = ensure_profile(email)

show_dashboard(profile, email)