import streamlit as st

def show_dashboard(profile, email):
    st.title("🎨 Coach de dessin IA")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.write(f"Bienvenue {st.user.name} 👋")
        st.caption(f"Connecté : {email}")

    with col2:
        if st.button("🚪 Déconnexion"):
            st.logout()
            st.rerun()

    st.write("---")

    xp = profile.get("xp", 0)
    level = xp // 100
    xp_in_level = xp % 100

    c1, c2 = st.columns(2)

    with c1:
        st.metric("⭐ XP", xp)

    with c2:
        st.metric("🏆 Niveau", level)

    st.progress(xp_in_level / 100)
    st.caption(f"{xp_in_level}/100 XP vers le niveau suivant")