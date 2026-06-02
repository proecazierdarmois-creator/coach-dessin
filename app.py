import streamlit as st

st.write("Query params:")
st.write(st.query_params)

st.write("User:")
st.write(st.user)

if not st.user.is_logged_in:
    st.button(
        "🔵 Continuer avec Google",
        on_click=st.login
    )
    st.stop()

st.success("Connecté")
st.write(st.user)