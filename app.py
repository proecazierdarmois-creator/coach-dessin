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
def get_leaderboard():
    profiles = supabase.table("profiles").select("email, xp").execute().data or []

    return sorted(
        profiles,
        key=lambda x: x.get("xp", 0),
        reverse=True
    )[:10]

def get_daily_challenge(level):
    if level < 2:
        return "Dessine un objet simple avec une ombre."
    elif level < 5:
        return "Dessine un visage avec 3 expressions différentes."
    elif level < 10:
        return "Dessine une scène avec arrière-plan et perspective."
    else:
        return "Crée une composition complète avec lumière, perspective et détails."
    
def get_coach_style(level):
    if level < 2:
        return "Utilise un langage très simple et très encourageant."
    elif level < 5:
        return "Donne des conseils concrets sur formes, proportions et couleurs."
    elif level < 10:
        return "Sois plus précis sur composition, volumes, ombres et perspective."
    else:
        return "Donne un retour avancé comme un professeur de dessin."

def get_badges(xp, analyses_count):
    badges = []

    if xp >= 50:
        badges.append("🎯 Premier pas")

    if xp >= 200:
        badges.append("🔥 Motivé")

    if xp >= 500:
        badges.append("🚀 Pro du dessin")

    if analyses_count >= 5:
        badges.append("📸 5 dessins")

    if analyses_count >= 20:
        badges.append("🏅 20 dessins")

    return badges

def get_level_info(xp):
    level = xp // 100
    xp_in_level = xp % 100

    if level < 2:
        rank = "🌱 Débutant"
    elif level < 5:
        rank = "✏️ Apprenti"
    elif level < 10:
        rank = "🎨 Artiste"
    else:
        rank = "👑 Maître"

    return level, xp_in_level, rank

def admin_get_xp_data():
    profiles = supabase.table("profiles").select("email, xp").execute().data or []

    # tri par XP
    profiles = sorted(profiles, key=lambda x: x.get("xp", 0), reverse=True)

    return profiles[:10]  # top 10

def admin_get_stats():
    profiles = supabase.table("profiles").select("*").execute().data or []
    analyses = supabase.table("analyses").select("*").execute().data or []

    total_users = len(profiles)
    total_analyses = len(analyses)

    avg_xp = int(sum([p.get("xp", 0) for p in profiles]) / total_users) if total_users > 0 else 0

    top_users = sorted(
        profiles,
        key=lambda p: p.get("xp", 0) or 0,
        reverse=True
    )[:5]

    return total_users, total_analyses, avg_xp, top_users

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

def save_analysis(email, image_url, analysis, is_challenge=False):
    result = supabase.table("analyses").insert({
        "email": email,
        "image_url": image_url,
        "note": int(str(analysis.get("note", 0)).split("/")[0]),
        "points_forts": analysis.get("points_forts", []),
        "ameliorations": analysis.get("ameliorations", []),
        "defi": analysis.get("defi", ""),
        "message_coach": analysis.get("message_coach", ""),
        "is_challenge": is_challenge,
    }).execute()
    return result.data[0] if result.data else None

def get_coach_style(level):
    if level < 2:
        return "Utilise un langage très simple, très encourageant, adapté à un débutant."
    elif level < 5:
        return "Donne des conseils concrets sur les formes, proportions et couleurs."
    elif level < 10:
        return "Sois plus précis sur composition, volumes, ombres et perspective."
    else:
        return "Donne un retour avancé comme un professeur de dessin."

def analyze(image_bytes, mime, age, niveau, level):
    coach_style = get_coach_style(level)

    prompt = f"""
Tu es un coach de dessin IA bienveillant.

Profil :
- âge : {age}
- niveau déclaré : {niveau}
- niveau XP : {level}

Style de coaching :
{coach_style}

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
    st.button("🔵 Se connecter avec Google", on_click=lambda: st.login("google"))
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

#Badges
analyses = get_analyses(st.user.email)
badges = get_badges(xp, len(analyses))

st.write("### 🏅 Tes badges")

if badges:
    for b in badges:
        st.write(b)
else:
    st.caption("Aucun badge débloqué pour le moment")

level, xp_in_level, rank = get_level_info(xp)

st.write(f"🏆 Niveau {level}")
st.progress(xp_in_level / 100)
st.subheader(rank)
st.caption(f"{xp_in_level}/100 XP vers le niveau suivant")

with st.expander("🎯 Défi du jour", expanded=True):
    st.info(get_daily_challenge(level))

with st.expander("🏆 Classement global", expanded=True):

    leaderboard = get_leaderboard()
    medals = ["🥇", "🥈", "🥉"]

    current_email = st.user.email  # 👈 ICI

    for i, user in enumerate(leaderboard):
        medal = medals[i] if i < 3 else f"{i+1}."

        if user.get("email") == current_email:
            st.success(f"{medal} {user.get('email')} — {user.get('xp',0)} XP (toi)")
        else:
            st.write(f"{medal} {user.get('email')} — {user.get('xp',0)} XP")

    for i, user in enumerate(leaderboard):
        medal = medals[i] if i < 3 else f"{i+1}."

        st.write(f"{medal} {user.get('email')} — {user.get('xp',0)} XP")

if is_admin():
    st.write("---")

    st.write("")
st.write("### 📈 Graphique XP")

xp_data = admin_get_xp_data()

if xp_data:
    names = [p["email"] for p in xp_data]
    values = [p.get("xp", 0) for p in xp_data]

    st.bar_chart({
        "XP": values
    })
else:
    st.info("Pas de données XP")
    
# ----------------------------
# ADMIN 2
# ----------------------------
if is_admin():
    st.write("---")

    with st.expander("🛠️ Admin", expanded=False):

        profiles = get_all_profiles()  # 👈 IMPORTANT

        if not profiles:
            st.info("Aucun profil trouvé.")
        else:
            emails = [str(p.get("email", "")) for p in profiles if p.get("email")]

            search = st.text_input("🔍 Rechercher un utilisateur")

            filtered_emails = [e for e in emails if search.lower() in e.lower()] if search else emails

            if not filtered_emails:
                st.warning("Aucun utilisateur trouvé")
            else:
                selected_email = st.selectbox("Choisir un compte", filtered_emails)

                selected_profile = next(
                    (p for p in profiles if p.get("email") == selected_email),
                    None
                )

                if selected_profile:
                    st.write(f"Compte : {selected_email}")

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
                st.rerun()
else:
    st.info("Aucune analyse pour ce compte.")

st.write("")
st.write("### 🏆 Top utilisateurs")
total_users, total_analyses, avg_xp, top_users = admin_get_stats()
for i, user in enumerate(top_users):
    st.write(f"{i+1}. {user.get('email')} — {user.get('xp',0)} XP")

st.write("---")
st.write("### 📊 Statistiques")

total_users, total_analyses, avg_xp, top_users = admin_get_stats()

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("👥 Utilisateurs", total_users)

with c2:
    st.metric("🖼️ Analyses", total_analyses)

with c3:
    st.metric("📊 XP moyen", avg_xp)

# ----------------------------
# ANALYSE
# ----------------------------
st.subheader("📸 Analyse")

file = st.file_uploader("Upload dessin", type=["png", "jpg", "jpeg"])

is_challenge = st.checkbox("🎯 Ce dessin répond au défi du jour")
if file and st.button("Analyser"):
    with st.spinner("Analyse..."):

        xp = profile.get("xp", 0)
        level = xp // 100

        # 👉 APPEL ICI
        data = analyze(
            file.getvalue(),
            file.type,
            profile.get("age") or 10,
            profile.get("niveau_dessin") or "Débutant",
            level
        )

        # 👉 récupération note
        raw_note = data.get("note", 0)

try:
    if isinstance(raw_note, int):
        note = raw_note
    else:
        note = int(str(raw_note).split("/")[0].strip())
except:
        note = 0
        xp_gain = note * 5
        xp += xp_gain

        # 👉 upload image
        import uuid
        file_bytes = file.getvalue()
        file_ext = file.name.split(".")[-1]
        file_name = f"{st.user.email}/{uuid.uuid4()}.{file_ext}"

        supabase.storage.from_("drawings").upload(
            file_name,
            file_bytes,
            {"content-type": file.type}
        )

        image_url = supabase.storage.from_("drawings").get_public_url(file_name)

        # 👉 sauvegarde
        try:
            save_analysis(st.user.email, image_url, data)
        except Exception as e:
            st.error("Erreur sauvegarde Supabase")
            st.code(str(e))
            st.stop()

        # 👉 update XP
        update_xp(st.user.email, xp)
        st.session_state.profile["xp"] = xp

        # 👉 affichage
        st.toast("✅ Analyse faite !")
        st.balloons()

        with st.expander("🖼️ Galerie de tes dessins", expanded=False):
                analyses = get_analyses(st.user.email)

if analyses:
        cols = st.columns(3)

        for i, a in enumerate(analyses[:12]):
            with cols[i % 3]:
                image_url = a.get("image_url")

                if image_url and str(image_url).startswith("http"):
                    st.image(image_url, use_container_width=True)
                else:
                    st.caption("Image non disponible")

                note = a.get("note", "—")
                st.markdown(f"⭐ **{note}/10**")
                st.metric("🔥 XP gagné", xp_gain)

                if a.get("is_challenge"):
                    st.caption("🎯 Défi validé")

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
        else:
            st.info("Aucun dessin pour le moment.")

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