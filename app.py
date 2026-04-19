import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# CONFIGURATION
# ----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "profile" not in st.session_state:
    st.session_state.profile = None

# ----------------------------
# LOGIN GOOGLE
# ----------------------------
if not st.user.is_logged_in:
    st.title("🎨 Coach de dessin IA")
    st.write("Connecte-toi avec Google pour commencer")
    st.button("Se connecter avec Google", on_click=st.login)
    st.stop()

# L'utilisateur est connecté
st.title("🎨 Coach de dessin IA")

col1, col2 = st.columns([3, 1])

with col1:
    st.write(f"Bienvenue {st.user.name} 👋")

with col2:
    if st.button("Déconnexion"):
        st.logout()
        st.stop()

st.write("---")
st.write("✅ Vous êtes connecté")