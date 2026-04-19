import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# CONFIGURATION
# ----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
DEFAULT_AVATAR = "https://via.placeholder.com/150?text=Avatar"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📊 XP", profile.get("xp", 0))

    with col2:
        age = profile.get("age")
        st.metric("🎂 Âge", age if age else "—")

    with col3:
        niveau = profile.get("niveau_dessin")
        st.metric("📚 Niveau", niveau if niveau else "—")

    st.write("")
    st.write("---")
    st.write("🚀 Prêt à démarrer ? Sélectionne une option ci-dessous")
else:
    st.warning("Profil non chargé.")

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