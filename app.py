import streamlit as st

st.write("is_logged_in =", st.user.is_logged_in)
st.write("st.user =", st.user)

if not st.user.is_logged_in:
    st.button(
        "🔵 Continuer avec Google",
        on_click=lambda: st.login("google")
    )
    st.stop()

st.success("Connecté !")
st.write(st.user.email)