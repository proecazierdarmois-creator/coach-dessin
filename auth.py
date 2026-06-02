import streamlit as st

def show_login():
    st.title("Connexion")
    st.button("🔵 Continuer avec Google", on_click=lambda: st.login("google"))
    st.stop()