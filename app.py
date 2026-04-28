import streamlit as st

# ----------------------------
# LOGIN GOOGLE SIMPLE
# ----------------------------

if not st.user.is_logged_in:
    st.title("Connexion")

    st.button("🔵 Se connecter avec Google", on_click=lambda: st.login("google"))

    st.stop()

# ----------------------------
# UTILISATEUR CONNECTÉ
# ----------------------------

st.title("🎨 Coach de dessin IA")

st.write("Connecté avec :")
st.write(st.user)

# bouton logout
if st.button("🚪 Déconnexion"):
    st.logout()
    st.rerun()