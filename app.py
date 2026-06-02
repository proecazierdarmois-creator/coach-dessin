import streamlit as st

from auth import show_login
from utils import ensure_profile
from dashboard import show_dashboard

import streamlit as st

st.write("Secrets détectés :")
st.write(list(st.secrets.keys()))
st.stop()

st.set_page_config(
    page_title="Coach de dessin IA",
    page_icon="🎨",
    layout="wide",
)

# ----------------------------
# LOGIN
# ----------------------------
if not st.user.is_logged_in:
    show_login()

# ----------------------------
# UTILISATEUR CONNECTÉ
# ----------------------------
email = st.user.email

profile = ensure_profile(email)

if profile is None:
    st.error("Impossible de charger le profil.")
    st.stop()

# ----------------------------
# DASHBOARD
# ----------------------------
show_dashboard(profile, email)