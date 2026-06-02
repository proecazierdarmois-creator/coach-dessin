import streamlit as st

st.write("USER:")
st.write(st.user)

if not st.user.is_logged_in:
    st.button(
        "🔵 Continuer avec Google",
        on_click=lambda: st.login("google")
    )
    st.stop()

st.success("✅ Connecté")
st.write("Email :", st.user.email)

if st.button("Déconnexion"):
    st.logout()
    st.rerun()