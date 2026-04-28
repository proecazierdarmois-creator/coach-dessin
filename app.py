import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_profile(email):
    result = supabase.table("profiles").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None

def ensure_profile(email):
    profile = get_profile(email)
    if profile:
        return profile

    result = supabase.table("profiles").insert({
        "email": email,
        "xp": 0,
    }).execute()

    return result.data[0] if result.data else None

if not st.user.is_logged_in:
    st.title("Connexion")
    st.button("🔵 Se connecter avec Google", on_click=lambda: st.login("google"))
    st.stop()

email = st.user.email
profile = ensure_profile(email)

st.title("🎨 Coach de dessin IA")
st.write(f"Connecté : {email}")

if profile:
    st.write("Profil chargé ✅")
    st.write(profile)
else:
    st.error("Profil non chargé")

if st.button("🚪 Déconnexion"):
    st.logout()
    st.rerun()