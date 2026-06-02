import streamlit as st
import time

import supabase

from utils import (
    supabase,
    get_analyses,
    is_admin,
    get_all_profiles,
    admin_update_xp,
    admin_delete_analysis,
    update_streak,
    get_leaderboard,
    get_badges,
)

from analysis import (
    analyze_drawing,
    save_analysis,
    upload_image,
    update_xp,
)


def show_dashboard(profile, email):

    # ----------------------------
    # LANGUE
    # ----------------------------
    if "lang" not in st.session_state:
        st.session_state.lang = "Français"

    languages = ["Français", "English", "Español"]

    lang = st.selectbox(
        "🌍 Langue",
        languages,
        index=languages.index(st.session_state.lang)
    )

    st.session_state.lang = lang

    translations = {
        "Français": {
            "welcome": "Bienvenue",
            "logout": "🚪 Déconnexion",
            "leaderboard": "🏆 Voir le classement",
            "badges": "🏅 Badges",
            "gallery": "🖼️ Galerie de tes dessins",
            "analysis": "📸 Analyse",
        },

        "English": {
            "welcome": "Welcome",
            "logout": "🚪 Logout",
            "leaderboard": "🏆 Leaderboard",
            "badges": "🏅 Badges",
            "gallery": "🖼️ Your drawings gallery",
            "analysis": "📸 Analysis",
        },

        "Español": {
            "welcome": "Bienvenido",
            "logout": "🚪 Cerrar sesión",
            "leaderboard": "🏆 Clasificación",
            "badges": "🏅 Insignias",
            "gallery": "🖼️ Galería de dibujos",
            "analysis": "📸 Análisis",
        }
    }

    t = translations[lang]

    # ----------------------------
    # STREAK
    # ----------------------------
    profile = update_streak(email) or profile

    # ----------------------------
    # PAGE
    # ----------------------------
    if "page" not in st.session_state:
        st.session_state.page = "home"

    # ----------------------------
    # LEADERBOARD PAGE
    # ----------------------------
    if st.session_state.page == "leaderboard":

        st.title("🏆 Classement général")

        leaderboard = get_leaderboard()

        if not leaderboard:
            st.info("Aucun utilisateur dans le classement.")
        else:
            medals = ["🥇", "🥈", "🥉"]

            for i, user in enumerate(leaderboard):

                rank = medals[i] if i < 3 else f"{i + 1}."

                line = (
                    f"{rank} "
                    f"{user.get('email')} — "
                    f"{user.get('xp', 0)} XP — "
                    f"🔥 {user.get('streak', 0)} jour(s)"
                )

                if user.get("email") == email:
                    st.success(line + " (toi)")
                else:
                    st.write(line)

        if st.button("⬅️ Retour au dashboard"):
            st.session_state.page = "home"
            st.rerun()

        st.stop()

    # ----------------------------
    # MAIN DASHBOARD
    # ----------------------------
    st.title("🎨 Coach de dessin IA")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.write(f"{t['welcome']} {st.user.name} 👋")
        st.caption(f"Connecté : {email}")

    if st.button(t["logout"]):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.email = None
    st.session_state.profile = None
    st.rerun()

    st.write("---")

    # ----------------------------
    # STATS
    # ----------------------------
    xp = profile.get("xp", 0)
    level = xp // 100
    xp_in_level = xp % 100
    streak = profile.get("streak", 0) or 0

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("⭐ XP", xp)

    with c2:
        st.metric("🏆 Niveau", level)

    with c3:
        st.metric("🔥 Streak", f"{streak} jour(s)")

    st.progress(xp_in_level / 100)
    st.caption(f"{xp_in_level}/100 XP vers le niveau suivant")

    # ----------------------------
    # BADGES
    # ----------------------------
    badges = get_badges(email, xp, streak)

    with st.expander(t["badges"], expanded=True):

        if badges:
            for badge in badges:
                st.write(badge)
        else:
            st.info("Aucun badge pour le moment.")

    # ----------------------------
    # LEADERBOARD BUTTON
    # ----------------------------
    if st.button(t["leaderboard"]):
        st.session_state.page = "leaderboard"
        st.rerun()

    st.write("---")

    # ----------------------------
    # ANALYSIS
    # ----------------------------
    st.subheader(t["analysis"])

    uploaded_file = st.file_uploader(
        "Upload dessin",
        type=["png", "jpg", "jpeg"]
    )

    if "last_analysis_time" not in st.session_state:
        st.session_state.last_analysis_time = 0

    now = time.time()

    if uploaded_file and st.button("Analyser"):

        if now - st.session_state.last_analysis_time < 5:
            st.warning("⏳ Attends quelques secondes avant une nouvelle analyse")
            st.stop()

        st.session_state.last_analysis_time = now

        with st.spinner("Analyse en cours..."):

            analysis = analyze_drawing(
                uploaded_file.getvalue(),
                uploaded_file.type,
                profile.get("age") or 10,
                profile.get("niveau_dessin") or "Débutant",
                profile.get("xp", 0) // 100
            )

            if analysis is None:
                st.stop()

            image_url = upload_image(email, uploaded_file)

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

            if analysis.get("defi"):
                st.info(analysis.get("defi"))

            if analysis.get("message_coach"):
                st.success(analysis.get("message_coach"))

    st.write("---")

    # ----------------------------
    # GALLERY
    # ----------------------------
    with st.expander(t["gallery"], expanded=True):

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

    # ----------------------------
    # ADMIN
    # ----------------------------
    st.write("---")

    if is_admin(email):

        with st.expander("🛠️ Admin", expanded=False):

            profiles = get_all_profiles()

            if not profiles:
                st.info("Aucun profil trouvé.")
            else:

                emails = [
                    p.get("email")
                    for p in profiles
                    if p.get("email")
                ]

                selected_email = st.selectbox(
                    "Utilisateur",
                    emails
                )

                selected_profile = next(
                    (
                        p for p in profiles
                        if p.get("email") == selected_email
                    ),
                    None
                )

                if selected_profile:

                    new_xp = st.number_input(
                        "XP",
                        min_value=0,
                        max_value=100000,
                        value=selected_profile.get("xp") or 0,
                        step=10,
                    )

                    if st.button("💾 Modifier XP"):
                        admin_update_xp(selected_email, new_xp)
                        st.success("XP mis à jour.")
                        st.rerun()

                    st.write("### Analyses utilisateur")

                    analyses = get_analyses(selected_email)

                    for a in analyses[:10]:

                        with st.expander(
                            f"Analyse "
                            f"{a.get('created_at', '')[:10]} "
                            f"— {a.get('note', '—')}/10"
                        ):

                            image_url = a.get("image_url")

                            if image_url and str(image_url).startswith("http"):
                                st.image(image_url, width=250)

                            if st.button(
                                "🗑️ Supprimer cette analyse",
                                key=f"delete_analysis_{a['id']}"
                            ):
                                admin_delete_analysis(a["id"])
                                st.success("Analyse supprimée.")
                                st.rerun()