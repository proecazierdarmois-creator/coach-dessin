import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase import create_client, Client
import os

st.write("Gemini OK:", os.getenv("GEMINI_API_KEY") is not None)

load_dotenv()

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# Config
# ----------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("SUPABASE_URL ou SUPABASE_ANON_KEY manque dans .env")
    st.stop()

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY manque dans .env")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
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

def analyse_dessin(image_bytes, mime_type, style, coach, theme):
    system_prompt = personnalites[coach]

    prompt = f"""
{system_prompt}

Tu analyses le dessin d'un enfant de 11 ans.

Style visé : {style}
Sujet annoncé : {theme if theme else "non précisé"}

Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{{
  "note": <nombre entier entre 1 et 10>,
  "points_forts": ["point fort 1", "point fort 2"],
  "ameliorations": ["amélioration 1", "amélioration 2"],
  "defi": "un défi court, fun et concret",
  "message_coach": "un petit message motivant du coach"
}}

Règles :
- ton encourageant
- adapté à un enfant de 11 ans
- conseils concrets
- phrases courtes
- pas de critique dure
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

def sign_up(email: str, password: str):
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
    })

def sign_in(email: str, password: str):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user = None

# ----------------------------
# Auth UI
# ----------------------------
if st.session_state.user is None:
    st.title("🎨 Coach de dessin IA")
    st.subheader("Connexion / Inscription")

    mode = st.radio("Choisis une action", ["Connexion", "Inscription"], horizontal=True)

    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Valider")

    if submitted:
        try:
            if mode == "Inscription":
                result = sign_up(email, password)
                st.success("Compte créé. Vérifie ton email si une confirmation est demandée.")
                # Certains projets connectent immédiatement, d'autres demandent confirmation email
                user = getattr(result, "user", None)
                session = getattr(result, "session", None)
                if session and user:
                    st.session_state.user = user
                    st.rerun()
            else:
                result = sign_in(email, password)
                if result and result.user:
                    st.session_state.user = result.user
                    st.success("Connexion réussie.")
                    st.rerun()
                else:
                    st.error("Connexion impossible.")
        except Exception as e:
            st.error("Erreur d'authentification")
            st.code(str(e))

    st.stop()

# ----------------------------
# App protégée
# ----------------------------
user = st.session_state.user

st.title("🎨 Coach de dessin IA")
st.write(f"Connecté : **{user.email}**")

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

    if st.button("Analyser mon dessin"):
        image_bytes = uploaded.read()
        mime_type = uploaded.type or "image/jpeg"

        with st.spinner("Analyse en cours..."):
            try:
                fb = analyse_dessin(image_bytes, mime_type, style, coach, theme)

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

if st.session_state.historique:
    for item in st.session_state.historique:
        st.write(
            f"• {item['theme']} — style : {item['style']} — coach : {item['coach']} — note : {item['note']}/10"
        )
else:
    st.write("Pas encore d’analyse.")