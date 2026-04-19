import streamlit as st
import json
from supabase import create_client
from google import genai
from google.genai import types

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# CONFIG
# ----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

ADMIN_EMAILS = {"pro.ecazierdarmois@gmail.com"}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

# ----------------------------
# SESSION
# ----------------------------
if "profile" not in st.session_state:
    st.session_state.profile = None

# ----------------------------
# UTILS
# ----------------------------
def is_admin():
    if st.user.is_logged_in:
        return st.user.email in ADMIN_EMAILS
    if st.session_state.profile:
        return st.session_state.profile.get("email") in ADMIN_EMAILS
    return False

def get_profile(email):
    res = supabase.table("profiles").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None

def ensure_profile(email):
    profile = get_profile(email)
    if profile:
        return profile
    res = supabase.table("profiles").insert({"email": email, "xp": 0}).execute()
    return res.data[0]

def update_xp(email, xp):
    supabase.table("profiles").update({"xp": xp}).eq("email", email).execute()

def get_analyses(email):
    res = supabase.table("analyses").select("*").eq("email", email).execute()
    return res.data or []

def save_analysis(email, image_url, analysis):
    supabase.table("analyses").insert({
        "email": email,
        "image_url": image_url,
        "note": analysis.get("note"),
        "points_forts": analysis.get("points_forts"),
        "ameliorations": analysis.get("ameliorations"),
        "defi": analysis.get("defi"),
        "message_coach": analysis.get("message_coach"),
    }).execute()

def analyze(image_bytes, mime, age, niveau):
    prompt = f"""
Analyse ce dessin d'une personne de {age} ans ({niveau}).
Réponds en JSON avec :
note, points_forts, ameliorations, defi, message_coach
"""
    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime)
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(res.text)

# ----------------------------
# LOGIN
# ----------------------------
if not st.user.is_logged_in:
    st.title("🎨 Coach de dessin IA")
    st.button("🔵 Se connecter avec Google", on_click=st.login)
    st.stop()

# ----------------------------
# LOAD PROFILE
# ----------------------------
if st.session_state.profile is None:
    st.session_state.profile = ensure_profile(st.user.email)

profile = st.session_state.profile

# ----------------------------
# DASHBOARD
# ----------------------------
st.title("🎨 Coach de dessin IA")
st.write(f"Bienvenue {st.user.name} 👋")

if st.button("Déconnexion"):
    st.logout()
    st.session_state.profile = None
    st.rerun()

# XP
xp = profile.get("xp", 0)
level = xp // 100
st.write(f"🏆 Niveau {level}")
st.progress((xp % 100) / 100)

# ----------------------------
# ANALYSE
# ----------------------------
st.subheader("📸 Analyse")

file = st.file_uploader("Upload dessin", type=["png", "jpg", "jpeg"])

if file and st.button("Analyser"):
    with st.spinner("Analyse..."):
        data = analyze(file.getvalue(), file.type, 10, "Débutant")

        save_analysis(st.user.email, "temp_url", data)

        xp += data.get("note", 0) * 5
        update_xp(st.user.email, xp)

        st.session_state.profile["xp"] = xp

        st.success("Analyse faite !")
        st.balloons()

        st.json(data)

# ----------------------------
# HISTORIQUE
# ----------------------------
with st.expander("📚 Historique"):
    analyses = get_analyses(st.user.email)
    for a in analyses:
        st.write(a.get("note"))

# ----------------------------
# ADMIN
# ----------------------------
if is_admin():
    st.write("---")
    with st.expander("🛠️ Admin"):
        st.write("Mode admin actif")