import streamlit as st


def show_login():
    st.title("🎨 Coach de dessin IA")

    st.write("Connecte-toi pour accéder à tes dessins, badges et progression.")

    st.button(
        "🔵 Continuer avec Google",
        on_click=lambda: st.login("google"),
        use_container_width=True,
    )

    st.stop()