import streamlit as st
import json
from supabase import create_client, Client
from google import genai
from google.genai import types

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# CONFIGURATION
# ----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
DEFAULT_AVATAR = "https://via.placeholder.com/150?text=Avatar"
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "profile" not in st.session_state:
    st.session_state.profile = None

# ----------------------------
# FONCTIONS PROFIL
# ----------------------------
def get_profile_by_email(email):
    """Récupère le profil Supabase par email"""
    result = supabase.table("profiles").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    return None


def ensure_profile(email, name, picture):
    profile = get_profile_by_email(email)

    if profile:
        if picture and not profile.get("avatar_url"):
            supabase.table("profiles").update({
                "avatar_url": picture
            }).eq("email", email).execute()
            profile["avatar_url"] = picture
        return profile

    new_profile = {
        "email": email,
        "avatar_url": picture or DEFAULT_AVATAR,
        "xp": 0,
        "genre": None,
        "age": None,
        "niveau_dessin": None,
    }

    result = supabase.table("profiles").insert(new_profile).execute()

    if result.data:
        return result.data[0]

    return None

def update_profile(email, age, genre, niveau_dessin):
    """Met à jour le profil dans Supabase"""
    update_data = {
        "age": age if age else None,
        "genre": genre if genre else None,
        "niveau_dessin": niveau_dessin if niveau_dessin else None,
    }

    result = supabase.table("profiles").update(update_data).eq("email", email).execute()

    if result.data:
        st.session_state.profile = result.data[0]
        return True

    return False


def save_analysis(email, image_url, analysis):
    """Sauvegarde l'analyse dans Supabase"""
    result = supabase.table("analyses").insert({
        "email": email,
        "image_url": image_url,
        "note": analysis.get("note"),
        "points_forts": analysis.get("points_forts"),
        "ameliorations": analysis.get("ameliorations"),
        "defi": analysis.get("defi"),
        "message_coach": analysis.get("message_coach"),
    }).execute()

    return result.data[0] if result.data else None


def get_analyses(email):
    result = (
        supabase.table("analyses")
        .select("*")
        .eq("email", email)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def update_xp(email, xp_gained):
    """Met à jour l'XP du profil"""
    current_xp = st.session_state.profile.get("xp", 0)
    new_xp = current_xp + xp_gained

    result = (
        supabase.table("profiles")
        .update({"xp": new_xp})
        .eq("email", email)
        .execute()
    )

    if result.data:
        st.session_state.profile = result.data[0]

    return new_xp

def analyze_drawing(image_bytes, mime_type, age, niveau_dessin):
    """Analyse un dessin avec Gemini et renvoie un JSON"""
    user_prompt = f"""
Tu es un coach de dessin IA bienveillant et encourageant.

Analyse ce dessin d'une personne de {age} ans, niveau {niveau_dessin}.

Réponds uniquement en JSON avec cette structure :
{{
  "note": 1-10,
  "points_forts": ["...", "..."],
  "ameliorations": ["...", "..."],
  "defi": "...",
  "message_coach": "..."
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            user_prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )

    return json.loads(response.text)

# ----------------------------
# LOGIN GOOGLE
# ----------------------------
if not st.user.is_logged_in:
    st.title("🎨 Coach de dessin IA")
    st.write("Connecte-toi avec Google pour commencer")
    st.button("Se connecter avec Google", on_click=st.login)
    st.stop()

# L'utilisateur est connecté
st.title("🎨 Coach de dessin IA")

col1, col2 = st.columns([3, 1])

with col1:
    st.write(f"Bienvenue {st.user.name} 👋")

with col2:
    if st.button("Déconnexion"):
        st.logout()
        st.stop()

# Charger/créer le profil
if st.session_state.profile is None:
    st.session_state.profile = ensure_profile(
        st.user.email,
        st.user.name,
        st.user.picture
    )

st.write("---")

# ----------------------------
# ÉCRAN PRINCIPAL
# ----------------------------
profile = st.session_state.profile

if profile:
    col1, col2 = st.columns([1, 3])

    with col1:
        avatar_url = profile.get("avatar_url") or DEFAULT_AVATAR
        st.image(avatar_url, width=80)

    with col2:
        st.subheader(f"{st.user.name}")
        st.caption(f"📧 {st.user.email}")

    st.write("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 XP", profile.get("xp", 0))

    with col2:
        xp = profile.get("xp", 0)
        level = xp // 100
        xp_in_level = xp % 100

        st.write(f"🏆 Niveau {level}")
        st.progress(xp_in_level / 100)
        st.caption(f"{xp_in_level}/100 XP vers le niveau suivant")

        if level < 2:
            rank = "🌱 Débutant"
        elif level < 5:
            rank = "✏️ Apprenti"
        elif level < 10:
            rank = "🎨 Artiste"
        else:
            rank = "👑 Maître"

        st.subheader(rank)

    with col3:
        age = profile.get("age")
        st.metric("🎂 Âge", age if age else "—")

    with col4:
        niveau = profile.get("niveau_dessin")
        st.metric("📚 Niveau", niveau if niveau else "—")

    st.write("")
    st.write("---")
    st.write("🚀 Prêt à démarrer ? Sélectionne une option ci-dessous")

    # ----------------------------
    # MON PROFIL
    # ----------------------------
    with st.expander("⚙️ Mon profil", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            age = st.number_input(
                "🎂 Quel est ton âge ?",
                min_value=5,
                max_value=100,
                value=profile.get("age") or 10,
                step=1
            )

        with col2:
            options_genre = ["—", "Homme", "Femme", "Autre"]
            genre_actuel = profile.get("genre") or "—"
            if genre_actuel not in options_genre:
                genre_actuel = "—"

            genre = st.selectbox(
                "⚧ Genre",
                options_genre,
                index=options_genre.index(genre_actuel)
            )

        with col3:
            options_niveau = ["—", "Débutant", "Intermédiaire", "Avancé"]
            niveau_actuel = profile.get("niveau_dessin") or "—"
            if niveau_actuel not in options_niveau:
                niveau_actuel = "—"

            niveau = st.selectbox(
                "📚 Niveau de dessin",
                options_niveau,
                index=options_niveau.index(niveau_actuel)
            )

        if st.button("💾 Sauvegarder le profil"):
            success = update_profile(
                st.user.email,
                age,
                genre if genre != "—" else None,
                niveau if niveau != "—" else None
            )

            if success:
                st.success("✅ Profil mis à jour !")
                st.rerun()
            else:
                st.error("❌ Erreur lors de la mise à jour")

    st.write("")
    st.subheader("📸 Analyser ton dessin")

    uploaded_file = st.file_uploader(
        "Choisis une image à analyser",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        st.image(uploaded_file, width=300)

        if st.button("🚀 Lancer l'analyse"):
            with st.spinner("🤖 Analyse en cours..."):
                try:
                    # Upload l'image
                    import uuid
                    file_bytes = uploaded_file.getvalue()
                    file_ext = uploaded_file.name.split(".")[-1]
                    file_name = f"drawings/{profile.get('id')}/{uuid.uuid4()}.{file_ext}"
                    
                    supabase.storage.from_("drawings").upload(
                        file_name,
                        file_bytes,
                        {"content-type": uploaded_file.type}
                    )
                    image_url = supabase.storage.from_("drawings").get_public_url(file_name)
                    
                    # Analyse avec Gemini
                    analysis = analyze_drawing(
                        file_bytes,
                        uploaded_file.type,
                        profile.get("age") or 10,
                        profile.get("niveau_dessin") or "Débutant"
                    )

                    # Sauvegarde l'analyse
                    save_analysis(st.user.email, image_url, analysis)
                    
                    # Met à jour l'XP
                    xp_gained = min(analysis.get("note", 0) * 5, 100)
                    update_xp(st.user.email, xp_gained)

                    st.success("✅ Analyse complète !")

                    note = analysis.get("note", 0)
                    st.metric("⭐ Note", f"{note}/10")
                    st.metric("🔥 XP gagné", xp_gained)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**💪 Points forts :**")
                        for point in analysis.get("points_forts", []):
                            st.write(f"• {point}")

                    with col2:
                        st.write("**📈 À améliorer :**")
                        for point in analysis.get("ameliorations", []):
                            st.write(f"• {point}")

                    st.write("**🎯 Défi du jour :**")
                    st.info(analysis.get("defi", ""))

                    st.write("**💬 Message du coach :**")
                    st.success(analysis.get("message_coach", ""))

                except Exception as e:
                    st.error(f"❌ Erreur : {str(e)}")

    # ----------------------------
    # HISTORIQUE DES ANALYSES
    # ----------------------------
    st.write("")
    st.subheader("📚 Historique de tes analyses")

    analyses = get_analyses(st.user.email)

    if analyses:
        for i, analysis in enumerate(analyses[:5]):  # Afficher les 5 dernières
            with st.expander(f"📅 Analyse #{len(analyses)-i} - Note: {analysis.get('note')}/10", expanded=(i==0)):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if analysis.get("image_url"):
                        st.image(analysis.get("image_url"), width=200)
                
                with col2:
                    st.write(f"**⭐ Note:** {analysis.get('note')}/10")
                    
                    if analysis.get("points_forts"):
                        st.write("**💪 Points forts:**")
                        for point in analysis.get("points_forts"):
                            st.write(f"• {point}")
                    
                    if analysis.get("ameliorations"):
                        st.write("**📈 À améliorer:**")
                        for point in analysis.get("ameliorations"):
                            st.write(f"• {point}")
                    
                    if analysis.get("defi"):
                        st.write(f"**🎯 Défi:** {analysis.get('defi')}")
                    
                    if analysis.get("message_coach"):
                        st.write(f"**💬 Coach:** {analysis.get('message_coach')}")
    else:
        st.info("Aucune analyse pour le moment. Upload un dessin pour commencer !")

else:
    st.warning("⚠️ Profil non chargé. Actualise la page.")