import streamlit as st
from utils import supabase, ensure_profile


def show_login():
    st.title("🎨 Coach de dessin IA")
    st.subheader("Connexion / Inscription")

    mode = st.radio(
        "Choisis une action",
        ["Connexion", "Inscription"],
        horizontal=True,
    )

    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        submitted = st.form_submit_button("Valider")

    if submitted:
        try:
            if mode == "Connexion":
                result = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password,
                })
            else:
                result = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                })

            if result and result.user:
                st.session_state.email = result.user.email
                st.session_state.profile = ensure_profile(result.user.email)
                st.success("✅ Connexion réussie")
                st.rerun()
            else:
                st.error("Connexion impossible")

        except Exception as e:
            st.error("Erreur d'authentification")
            st.code(str(e))

    st.stop()