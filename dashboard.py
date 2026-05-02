import streamlit as st
from analysis import analyze_drawing, save_analysis, upload_image, update_xp
import time
from utils import get_analyses

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

    st.write("---")
    st.subheader("📸 Analyse")

    uploaded_file = st.file_uploader("Upload dessin", type=["png", "jpg", "jpeg"])
    analyse_button = st.button("Analyser")

    if uploaded_file and analyse_button:
        if "last_analysis_time" not in st.session_state:
            st.session_state.last_analysis_time = 0

        now = time.time()
        if now - st.session_state.last_analysis_time < 5:
            st.warning("⏳ Attends quelques secondes avant une nouvelle analyse")
            return

        st.session_state.last_analysis_time = now

        with st.spinner("Analyse en cours..."):
            image_url = upload_image(email, uploaded_file)
            if not image_url:
                st.error("Impossible de téléverser l'image.")
                return

            analysis = analyze_drawing(
                uploaded_file.getvalue(),
                uploaded_file.type,
                profile.get("age") or 10,
                profile.get("niveau_dessin") or "Débutant",
                level,
            )

            if analysis is None:
                st.stop()

            saved = save_analysis(email, image_url, analysis)
            note = saved.get("note", 0) if saved else 0
            profile, xp_gain = update_xp(email, profile, note)

            st.success("✅ Analyse terminée !")
            st.metric("⭐ Note", f"{note}/10")
            st.metric("🔥 XP gagné", xp_gain)

            col1, col2 = st.columns(2)

            with col1:
                st.write("**💪 Points forts**")
                for p in analysis.get("points_forts", []):
                    st.write(f"• {p}")

            with col2:
                st.write("**📈 À améliorer**")
                for p in analysis.get("ameliorations", []):
                    st.write(f"• {p}")

            st.info(analysis.get("defi", ""))
            st.success(analysis.get("message_coach", ""))

        
    st.write("---")

    with st.expander("🖼️ Galerie de tes dessins", expanded=True):
        analyses = get_analyses(email)

        if not analyses:
            st.info("Aucun dessin pour le moment.")
        else:
            cols = st.columns(3)

            for i, a in enumerate(analyses[:12]):
                with cols[i % 3]:
                    image_url = a.get("image_url")

                    if image_url and str(image_url).startswith("http"):
                        st.image(image_url, use_container_width=True)
                    else:
                        st.caption("Image non disponible")

                    st.markdown(f"⭐ **{a.get('note', '—')}/10**")

                    with st.expander("Détails"):
                        if a.get("points_forts"):
                            st.write("**💪 Points forts**")
                            for p in a.get("points_forts"):
                                st.write(f"• {p}")

                        if a.get("ameliorations"):
                            st.write("**📈 À améliorer**")
                            for p in a.get("ameliorations"):
                                st.write(f"• {p}")

                        if a.get("defi"):
                            st.info(a.get("defi"))

                        if a.get("message_coach"):
                            st.success(a.get("message_coach"))
