import streamlit as st

st.write("Query params:")
st.write(st.query_params)

st.write("User:")
st.write(st.user)

if not st.user.is_logged_in:
    st.button(
        "🔵 Continuer avec Google",
        on_click=lambda: st.login("google")
    )
    st.stop()

st.success("Connecté")