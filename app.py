import streamlit as st
import json
import uuid
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
def admin_get_user_analyses(email):
    result = (
        supabase.table("analyses")
        .select("*")
        .eq("email", email)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def admin_delete_analysis(analysis_id):
    supabase.table("analyses").delete().eq("id", analysis_id).execute()

def get_all_profiles():
    result = supabase.table("profiles").select("*").order("xp", desc=True).execute()
    return result.data or []


def admin_update_profile(email, xp):
    result = (
        supabase.table("profiles")
        .update({"xp": xp})
        .eq("email", email)
        .execute()
    )
    return result.data[0] if result.data else None

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
    try:
        result = supabase.table("analyses").insert({
            "email": email,
            "image_url": image_url,
            "note": int(str(analysis.get("note", 0)).split("/")[0]),
            "points_forts": analysis.get("points_forts", []),
            "ameliorations": analysis.get("ameliorations", []),
            "defi": analysis.get("defi", ""),
            "message_coach": analysis.get("message_coach", ""),
        }).execute()

        return result.data[0] if result.data else None

    except Exception as e:
        st.error("Erreur sauvegarde Supabase")
        st.code(str(e))
        raise

def analyze(image_bytes, mime, age, niveau):
    prompt = f"""
Analyse ce dessin d'une personne de {age} ans ({niveau}).
Réponds en JSON avec :
note, points_forts, ameliorations, defi, message_coach
"""

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        return json.loads(res.text)

    except Exception as e:
        st.error("Erreur Gemini")
        st.code(str(e))
        raise

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

# XP
xp = profile.get("xp", 0)
level = xp // 100
st.write(f"🏆 Niveau {level}")
st.progress((xp % 100) / 100)

if is_admin():
    st.write("---")

    with st.expander("🛠️ Admin", expanded=False):
        profiles = get_all_profiles()

        if not profiles:
            st.info("Aucun profil trouvé.")
        else:
            emails = [p["email"] for p in profiles]
            selected_email = st.selectbox("Choisir un compte", emails)

            selected_profile = next(
                (p for p in profiles if p["email"] == selected_email),
                None
            )

            if selected_profile:
                st.write(f"**Compte :** {selected_profile['email']}")

                new_xp = st.number_input(
                    "XP",
                    min_value=0,
                    max_value=100000,
                    value=selected_profile.get("xp") or 0,
                    step=10
                )

                if st.button("💾 Modifier XP"):
                    updated = admin_update_profile(selected_email, new_xp)

                    if updated:
                        st.success("XP mis à jour.")
                        if st.session_state.profile.get("email") == selected_email:
                            st.session_state.profile = updated
                            st.write("---")
st.write("### Analyses de cet utilisateur")

user_analyses = admin_get_user_analyses(selected_email)

if user_analyses:
    for a in user_analyses[:10]:
        with st.expander(f"Analyse {a.get('created_at', '')[:10]} — note {a.get('note', '—')}/10"):

            image_url = a.get("image_url")

            if image_url and str(image_url).startswith("http"):
                st.image(image_url, width=250)
            else:
                st.caption("Image non disponible")

if st.button("🗑️ Supprimer cette analyse", key=f"del_analysis_{a['id']}"):
                admin_delete_analysis(a["id"])
                st.success("Analyse supprimée.")
else:
    st.info("Aucune analyse pour ce compte.")

# ----------------------------
# ANALYSE
# ----------------------------
st.subheader("📸 Analyse")

file = st.file_uploader("Upload dessin", type=["png", "jpg", "jpeg"])

if file and st.button("Analyser"):
    with st.spinner("Analyse..."):
        data = analyze(file.getvalue(), file.type, 10, "Débutant")

        note = int(str(data.get("note", 0)).split("/")[0])
        xp_gain = note * 5

        xp = profile.get("xp", 0) + xp_gain

    file_bytes = file.getvalue()
    file_ext = file.name.split(".")[-1]
    file_name = f"{st.user.email}/{uuid.uuid4()}.{file_ext}"

    supabase.storage.from_("drawings").upload(
        file_name,
        file_bytes,
        {"content-type": file.type}
    )

    image_url = supabase.storage.from_("drawings").get_public_url(file_name)

    save_analysis(st.user.email, image_url, data)
    update_xp(st.user.email, xp)
    st.session_state.profile["xp"] = xp

    st.success("✅ Analyse faite !")
    st.balloons()

    st.metric("⭐ Note", f"{note}/10")
    st.metric("🔥 XP gagné", xp_gain)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**💪 Points forts :**")
        for p in data.get("points_forts", []):
            st.write(f"• {p}")

    with col2:
        st.write("**📈 À améliorer :**")
        for p in data.get("ameliorations", []):
            st.write(f"• {p}")

    st.write("**🎯 Défi :**")
    st.info(data.get("defi", ""))

    st.write("**💬 Coach :**")
    st.success(data.get("message_coach", ""))

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