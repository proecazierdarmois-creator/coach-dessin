import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client
import uuid
import streamlit as st

if not st.user.is_logged_in:
    st.title("Test Google login")
    st.button("Se connecter avec Google", on_click=st.login)
    st.stop()

st.write(f"Bonjour {st.user.name}")
if st.button("Se déconnecter"):
    st.logout()

# ------------------------
# SESSION STATE INIT
# ------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

def get_user_id(user):
    if user is None:
        return None
    if isinstance(user, dict):
        return user.get("id")
    return getattr(user, "id", None)


def get_user_email(user):
    if user is None:
        return None
    if isinstance(user, dict):
        return user.get("email")
    return getattr(user, "email", None)


def get_user_metadata(user):
    if user is None:
        return {}
    if isinstance(user, dict):
        return user.get("user_metadata", {}) or {}
    return getattr(user, "user_metadata", {}) or {}


def update_profile(user_id, age, genre, niveau_dessin):
    result = supabase.table("profiles").upsert({
        "id": user_id,
        "age": age,
        "genre": genre,
        "niveau_dessin": niveau_dessin,
    }).execute()
    return result


def get_level(xp):
    if xp < 50:
        return "Débutant 🟢"
    elif xp < 150:
        return "Intermédiaire 🔵"
    else:
        return "Avancé 🔴"


def get_profile(user_id=None, email=None):
    query = supabase.table("profiles").select("*")
    if user_id is not None:
        query = query.eq("id", user_id)
    elif email:
        query = query.eq("email", email)
    else:
        return None

    result = query.execute()
    if result.data:
        return result.data[0]
    return None


def get_profile_by_email(email):
    return get_profile(email=email)


def ensure_profile(email, name=None, picture=None):
    profile = get_profile(email=email)
    if profile:
        return profile

    result = supabase.table("profiles").insert({
        "email": email,
        "name": name,
        "avatar_url": picture or DEFAULT_AVATAR,
        "xp": 0,
    }).execute()
    if result.data:
        return result.data[0]
    return None

# ------------------------
# CONFIG
# ------------------------
DEFAULT_AVATAR = "https://via.placeholder.com/150?text=Avatar"


# ------------------------
# UPLOAD AVATAR
# ------------------------
def upload_avatar(user_id, file_name, file_bytes, mime_type):
    storage_path = f"{user_id}/{file_name}"

    try:
        supabase.storage.from_("avatars").upload(
            storage_path,
            file_bytes,
            {"content-type": mime_type}
        )
    except Exception:
        supabase.storage.from_("avatars").update(
            storage_path,
            file_bytes,
            {"content-type": mime_type}
        )

    public_url = supabase.storage.from_("avatars").get_public_url(storage_path)
    return public_url


# ------------------------
# UPDATE DB
# ------------------------
def update_avatar(user_id, avatar_url):
    supabase.table("profiles").update({
        "avatar_url": avatar_url
    }).eq("id", user_id).execute()


# ------------------------
# GET AVATAR
# ------------------------
def get_avatar(profile):
    if profile and profile.get("avatar_url"):
        return profile.get("avatar_url")
    return DEFAULT_AVATAR


def upload_image(user_id, uploaded):
    file_bytes = uploaded.getvalue()
    mime_type = uploaded.type or "image/jpeg"

    # 🔥 nom unique
    unique_name = f"{uuid.uuid4()}_{uploaded.name}"
    file_name = f"{user_id}/{unique_name}"

    supabase.storage.from_("drawings").upload(
        file_name,
        file_bytes,
        {"content-type": mime_type}
    )

    public_url = supabase.storage.from_("drawings").get_public_url(file_name)
    return public_url

def save_profile(user):
    metadata = get_user_metadata(user)
    user_id = get_user_id(user)
    email = get_user_email(user)

    supabase.table("profiles").upsert({
        "id": user_id,
        "email": email,
        "age": metadata.get("age"),
        "genre": metadata.get("genre"),
        "niveau_dessin": metadata.get("niveau_dessin"),
    }).execute()


def update_xp(user_id, xp):
    supabase.table("profiles").update({"xp": xp}).eq("id", user_id).execute()


def save_analysis(user_id, theme, style, coach, note, defi, message_coach, image_url=None):
    supabase.table("analyses").insert({
        "user_id": user_id,
        "theme": theme,
        "style": style,
        "coach": coach,
        "note": note,
        "defi": defi,
        "message_coach": message_coach,
        "image_url": image_url,
    }).execute()


def get_analyses(user_id):
    result = (
        supabase.table("analyses")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []

load_dotenv()

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# Config
# ----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if not GEMINI_API_KEY:
    st.error("Clé Gemini manquante dans Streamlit Secrets")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

if "access_token" in st.session_state and "refresh_token" in st.session_state:
    try:
        session_response = supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

        if "user" not in st.session_state or st.session_state.user is None:
            st.session_state.user = session_response.user
    except Exception:
        st.session_state.user = None

# Cas 2 : session déjà connue
elif st.session_state.access_token and st.session_state.refresh_token:
    try:
        session = supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )
        st.session_state.user = session.user
    except Exception:
        st.session_state.user = None

client = genai.Client()

# ----------------------------
# Session state
# ----------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "xp" not in st.session_state:
    st.session_state.xp = 0

if "badges" not in st.session_state:
    st.session_state.badges = []

if "historique" not in st.session_state:
    st.session_state.historique = []

# ----------------------------
# Helpers
# ----------------------------
def calcul_niveau(xp: int) -> int:
    return 1 + xp // 30

def verifier_badges(note: int, style: str):
    nouveaux = []

    if note >= 8 and "⭐ Premier 8+" not in st.session_state.badges:
        nouveaux.append("⭐ Premier 8+")

    if note == 10 and "👑 Chef-d'œuvre" not in st.session_state.badges:
        nouveaux.append("👑 Chef-d'œuvre")

    badge_style = f"🎨 Style {style}"
    if badge_style not in st.session_state.badges:
        nouveaux.append(badge_style)

    if len(st.session_state.historique) >= 4 and "🔥 5 dessins analysés" not in st.session_state.badges:
        nouveaux.append("🔥 5 dessins analysés")

    st.session_state.badges.extend(nouveaux)
    return nouveaux

personnalites = {
    "Sensei Manga": """
Tu es Sensei Manga, un coach énergique et gentil.
Tu adores les poses dynamiques, les émotions et les regards expressifs.
Tu parles comme un mentor cool d'anime.
""",
    "Coach Cartoon": """
Tu es Coach Cartoon, drôle, positif et encourageant.
Tu aimes les expressions exagérées, les formes simples et les dessins fun.
""",
    "Maître Croquis": """
Tu es Maître Croquis, calme, rassurant et précis.
Tu aides à améliorer les bases du dessin : formes, proportions, ombres.
"""
}

def analyse_dessin(image_bytes, mime_type, style, coach, theme, age=11, niveau_dessin="Débutant"):
    system_prompt = personnalites[coach]

    prompt = f"""
Tu es un professeur de dessin.

Tu analyses le dessin d'un utilisateur avec :
- âge : {age}
- niveau : {niveau_dessin}

Adapte ton langage :
- enfant débutant → très simple, encourageant
- niveau avancé → plus technique

Style : {style}
Sujet : {theme if theme else "non précisé"}

Réponds en JSON :
{{
  "note": 1 à 10,
  "points_forts": ["...", "..."],
  "ameliorations": ["...", "..."],
  "defi": "...",
  "message_coach": "..."
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )

    return json.loads(response.text)

def sign_up(email: str, password: str, genre: str, age: int, niveau_dessin: str):
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {
                "genre": genre,
                "age": age,
                "niveau_dessin": niveau_dessin,
            }
        }
    })

def sign_in(email: str, password: str):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

def sign_out():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None

# ----------------------------
# Auth UI
# ----------------------------
if (not st.user.is_logged_in) and (st.session_state.user is None):
    st.title("🎨 Coach de dessin IA")
    st.subheader("Connexion / Inscription")

    st.markdown("### 🔐 Connexion rapide")
    st.button("🔵 Se connecter avec Google", on_click=st.login)

    st.divider()

    # 👇 👉 ICI TU METS TON BLOC
    mode = st.radio("Choisis une action", ["Connexion", "Inscription"], horizontal=True)

    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        if mode == "Inscription":
            genre = st.selectbox(
                "Genre",
                ["Je préfère ne pas dire", "Fille", "Garçon", "Non-binaire", "Autre"]
            )

            age = st.number_input(
                "Âge",
                min_value=4,
                max_value=100,
                value=11,
                step=1
            )

            niveau_dessin = st.selectbox(
                "Niveau en dessin",
                ["Débutant", "Intermédiaire", "Avancé"]
            )

        submitted = st.form_submit_button("Valider")

    # ----------------------------
    # Traitement
    # ----------------------------
    if submitted:
        try:
            if mode == "Connexion":
                result = sign_in(email, password)
                if result and result.user:
                    st.session_state.user = result.user
                    st.session_state.access_token = result.session.access_token
                    st.session_state.refresh_token = result.session.refresh_token
                    save_profile(result.user)
                    st.success("Connexion réussie.")
                    st.rerun()
                else:
                    st.error("Connexion impossible.")

            else:  # Inscription
                result = sign_up(email, password, genre, int(age), niveau_dessin)
                st.success("Compte créé.")

                user = getattr(result, "user", None)
                session = getattr(result, "session", None)

                if session and user:
                    st.session_state.user = user
                    st.session_state.access_token = session.access_token
                    st.session_state.refresh_token = session.refresh_token
                    save_profile(user)
                    st.rerun()

        except Exception as e:
            st.error("Erreur d'authentification")
            st.code(str(e))

    st.stop()

# ----------------------------
# Sync utilisateur Google → session + Supabase
# ----------------------------
if st.user.is_logged_in and st.session_state.user is None:
    user_email = st.user.email
    user_name = getattr(st.user, "name", user_email)
    user_picture = getattr(st.user, "picture", None)

    profile = get_profile_by_email(user_email)
    if not profile:
        profile = ensure_profile(user_email, user_name, user_picture)

    st.session_state.user = {
        "id": profile.get("id") if profile else None,
        "email": user_email,
        "name": user_name,
        "picture": user_picture
    }

    st.rerun()  # 🔥 important pour rafraîchir l'app

# ----------------------------
# App protégée
# ----------------------------
user = st.session_state.user
profile = get_profile(user_id=get_user_id(user), email=get_user_email(user))
st.write("USER ID:", get_user_id(user))

st.write("PROFILE ID:", profile.get("id") if profile else None)
xp = profile.get("xp", 0) if profile else 0
niveau_label = get_level(xp)

if profile:
    avatar_url = profile.get("avatar_url")
else:
    avatar_url = None

st.divider()
st.subheader("👤 Mon profil")

current_age = profile.get("age") if profile else 11
if current_age is None:
    current_age = 11

current_genre = profile.get("genre", "Je préfère ne pas dire") if profile else "Je préfère ne pas dire"
current_niveau = profile.get("niveau_dessin", "Débutant") if profile else "Débutant"

with st.form("profile_form"):
    new_age = st.number_input("Âge", min_value=4, max_value=100, value=int(current_age), step=1)

    genres = ["Je préfère ne pas dire", "Fille", "Garçon", "Non-binaire", "Autre"]
    genre_index = genres.index(current_genre) if current_genre in genres else 0
    new_genre = st.selectbox("Genre", genres, index=genre_index)

    niveaux = ["Débutant", "Intermédiaire", "Avancé"]
    niveau_index = niveaux.index(current_niveau) if current_niveau in niveaux else 0
    new_niveau = st.selectbox("Niveau en dessin", niveaux, index=niveau_index)

    save_profile_button = st.form_submit_button("Enregistrer mon profil")

if save_profile_button:
    try:
        result = update_profile(get_user_id(user), int(new_age), new_genre, new_niveau)
        st.write(result)
        st.success("Profil mis à jour")
        st.rerun()
    except Exception as e:
        st.error("Erreur lors de la mise à jour du profil")
        st.code(str(e))

metadata = get_user_metadata(user)

age = metadata.get("age", 11)
niveau_dessin = metadata.get("niveau_dessin", "Débutant")

profile = get_profile(user_id=get_user_id(user), email=get_user_email(user))

genre = profile.get("genre", "Non renseigné") if profile else "Non renseigné"
age = profile.get("age", "Non renseigné") if profile else "Non renseigné"
niveau_dessin = profile.get("niveau_dessin", "Non renseigné") if profile else "Non renseigné"

avatar_url = get_avatar(profile)

col1, col2 = st.columns([1, 3])

with col1:
    st.image(avatar_url, width=100)

with col2:
    st.markdown(f"### 👤 {get_user_email(user)}")
    st.write(f"🎯 XP : **{xp}**")
    st.write(f"🏆 Niveau : **{niveau_label}**")
st.write(f"Genre : **{genre}**")
st.write(f"Âge : **{age}**")

st.title("🎨 Coach de dessin IA")
st.write(f"Connecté : **{get_user_email(user)}**")

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("Se déconnecter"):
        sign_out()
        st.rerun()

coach = st.selectbox(
    "🧑‍🏫 Choisis ton professeur",
    ["Sensei Manga", "Coach Cartoon", "Maître Croquis"]
)

style = st.selectbox(
    "🎨 Choisis un style",
    ["Cartoon", "Réaliste", "Manga", "Fantasy"]
)

theme = st.text_input("✏️ Sujet du dessin (optionnel)", placeholder="Ex : dragon, chat, ninja, château...")
uploaded = st.file_uploader("Choisis une image", type=["png", "jpg", "jpeg"])

niveau = calcul_niveau(st.session_state.xp)

st.subheader("🏆 Progression")
st.write(f"**XP :** {st.session_state.xp}")
st.write(f"**Niveau :** {niveau}")

if st.session_state.badges:
    st.write("**Badges :** " + " | ".join(st.session_state.badges))
else:
    st.write("**Badges :** aucun pour l’instant")

if uploaded:
    st.image(uploaded, caption="Ton dessin", use_container_width=True)
    image_url = upload_image(get_user_id(user), uploaded)
    
    if st.button("Analyser mon dessin"):
        image_bytes = uploaded.read()
        mime_type = uploaded.type or "image/jpeg"

        with st.spinner("Analyse en cours..."):
            try:
                fb = analyse_dessin(image_bytes, mime_type, style, coach, theme, age=age, niveau_dessin=niveau_dessin)

                note = int(fb["note"])
                gain_xp = note * 5
                st.session_state.xp += gain_xp
                niveau = calcul_niveau(st.session_state.xp)

                st.session_state.historique.insert(0, {
                    "theme": theme if theme else "Sans titre",
                    "style": style,
                    "coach": coach,
                    "note": note
                })

                nouveaux_badges = verifier_badges(note, style)

                st.subheader(f"⭐ Note : {note}/10")
                st.success(f"Tu gagnes {gain_xp} XP !")

                st.subheader("💪 Points forts")
                for x in fb["points_forts"]:
                    st.write("•", x)

                st.subheader("🔧 À améliorer")
                for x in fb["ameliorations"]:
                    st.write("•", x)

                st.subheader("🎯 Défi")
                st.write(fb["defi"])

                st.subheader(f"🧑‍🏫 Message de {coach}")
                st.info(fb["message_coach"])

                st.subheader("🏅 Récompenses")
                st.write(f"**Niveau actuel :** {niveau}")
                if nouveaux_badges:
                    st.write("**Nouveaux badges :** " + " | ".join(nouveaux_badges))
                else:
                    st.write("Pas de nouveau badge cette fois.")

            except Exception as e:
                st.error("Erreur pendant l'analyse Gemini.")
                st.code(str(e))

st.divider()
st.subheader("📚 Historique")

historique = get_analyses(get_user_id(user))

if historique:
    for item in historique:
        st.write(f"🎯 {item['theme']} — Note : {item['note']}/10")

        if item.get("image_url"):
            st.image(item["image_url"], width=200)
else:
    st.write("Pas encore de dessins.")