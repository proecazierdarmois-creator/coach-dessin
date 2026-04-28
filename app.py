import streamlit as st
import json
import uuid
from supabase import create_client
from google import genai
from google.genai import types
from datetime import date, timedelta

st.set_page_config(page_title="Coach de dessin IA", page_icon="🎨")

# ----------------------------
# CONFIG
# ----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

ADMIN_EMAILS = {"pro.ecazierdarmois@gmail.com"}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
if "code" in st.query_params:
    try:
        code = st.query_params["code"]
        supabase.auth.exchange_code_for_session({"auth_code": code})
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error("Erreur retour OAuth")
        st.code(str(e))
        st.stop()
client = genai.Client(api_key=GEMINI_API_KEY)
session = supabase.auth.get_session()

# ----------------------------
# SESSION
# ----------------------------
if "profile" not in st.session_state:
    st.session_state.profile = None

# ----------------------------
# UTILS
# ----------------------------
def update_profile(email, age, genre, niveau_dessin):
    result = (
        supabase.table("profiles")
        .update({
            "age": age if age else None,
            "genre": genre if genre else None,
            "niveau_dessin": niveau_dessin if niveau_dessin else None,
        })
        .eq("email", email)
        .execute()
    )

    if result.data:
        st.session_state.profile = result.data[0]
        return True

    return False

def get_current_email():
    if st.user.is_logged_in and hasattr(st.user, "email"):
        return st.user.email

    try:
        session = supabase.auth.get_session()
        if session and session.user:
            return session.user.email
    except:
        pass

    if st.session_state.profile:
        return st.session_state.profile.get("email")

    return None

def is_parent():
    profile = st.session_state.profile
    return profile and profile.get("role") == "parent"


def get_children_for_parent(parent_email):
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("parent_email", parent_email)
        .execute()
    )
    return result.data or []


def parent_link_child(child_email, parent_email):
    result = (
        supabase.table("profiles")
        .update({"parent_email": parent_email, "role": "child"})
        .eq("email", child_email)
        .execute()
    )
    return result.data[0] if result.data else None


def set_parent_role(email):
    result = (
        supabase.table("profiles")
        .update({"role": "parent"})
        .eq("email", email)
        .execute()
    )
    if result.data:
        st.session_state.profile = result.data[0]
        return True
    return False

def update_streak(email):
    """Met à jour la streak quotidienne de l'utilisateur"""
    today = date.today()

    profile = get_profile_by_email(email)
    if not profile:
        return 0

    last_active = profile.get("last_active_date")
    streak = profile.get("streak", 0) or 0

    if last_active:
        last_active = date.fromisoformat(str(last_active))

    # Déjà actif aujourd’hui → pas de changement
    if last_active == today:
        return streak

    # Jour consécutif → +1
    if last_active == today - timedelta(days=1):
        streak += 1
    else:
        # reset
        streak = 1

    result = (
        supabase.table("profiles")
        .update({
            "streak": streak,
            "last_active_date": str(today),
        })
        .eq("email", email)
        .execute()
    )

    if result.data:
        st.session_state.profile = result.data[0]

    return streak

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
        return current_email in ADMIN_EMAILS
    if st.session_state.profile:
        return st.session_state.profile.get("email") in ADMIN_EMAILS
    return False

def get_profile_by_email(email):
    result = supabase.table("profiles").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    return None

def ensure_profile(email):
    profile = get_profile_by_email(email)
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
# APP
# ----------------------------

current_email = get_current_email()

st.write("st.user:", st.user)
st.write("current_email:", current_email)

# ----------------------------
# LOGIN
# ----------------------------
current_email = get_current_email()

if not current_email:

    st.title("Connexion")

# 🔵 GOOGLE (TOUJOURS EN PREMIER)
st.subheader("Connexion rapide")
st.button("🔵 Continuer avec Google", on_click=lambda: st.login("google"))

st.divider()

# EMAIL / PASSWORD
mode = st.radio("Choisis une action", ["Connexion", "Inscription"], horizontal=True)

with st.form("email_auth_form"):
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")

    if mode == "Inscription":
        age = st.number_input("Âge", min_value=5, max_value=100, value=10)
        genre = st.selectbox("Genre", ["—", "Fille", "Garçon", "Autre"])
        niveau = st.selectbox("Niveau dessin", ["Débutant", "Intermédiaire", "Avancé"])

    submitted = st.form_submit_button("Valider")

if submitted:
    try:
        if mode == "Connexion":
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if result and result.user:
                st.session_state.profile = ensure_profile(result.user.email)
                st.success("✅ Connexion réussie")
                st.rerun()

        else:
            result = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if result and result.user:
                st.session_state.profile = ensure_profile(email)

                update_profile(
                    email,
                    age,
                    genre if genre != "—" else None,
                    niveau
                )

                st.success("✅ Compte créé")
                st.rerun()

    except Exception as e:
        st.error("Erreur d'authentification")
        st.code(str(e))

st.stop()

if st.user.is_logged_in and hasattr(st.user, "email"):
    current_email = st.user.email

    if st.session_state.profile is None:
        st.session_state.profile = ensure_profile(current_email)
        st.rerun()
# ----------------------------
# LOAD PROFILE
# ----------------------------
if st.session_state.profile is None:
    if st.user.is_logged_in and hasattr(st.user, "email"):
       current_email = get_current_email()

current_email = get_current_email()

if current_email and st.session_state.profile is None:
    st.session_state.profile = ensure_profile(current_email)

if not current_email:
    st.warning("Connecte-toi pour continuer.")
    st.stop()

profile = st.session_state.profile
streak = update_streak(current_email)
profile = st.session_state.profile

# ----------------------------
# DASHBOARD
# ----------------------------
profile = st.session_state.profile

st.title("🎨 Coach de dessin IA")
if st.button("🚪 Déconnexion"):
    if st.user.is_logged_in:
        st.logout()

    try:
        supabase.auth.sign_out()
    except:
        pass

    st.session_state.profile = None
    st.rerun()
current_email = get_current_email()
if not current_email:
    st.warning("Connecte-toi pour continuer.")
    st.stop()

st.write(f"Bienvenue {st.user.name} 👋")

if st.button("Déconnexion"):
    st.logout()
    st.session_state.profile = None

xp = profile.get("xp", 0)
streak = profile.get("streak", 0)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("⭐ XP", xp)

with col2:
    st.metric("🏆 Niveau", xp // 100)

with col3:
    st.metric("🔥 Streak", f"{streak} jour(s)")

if streak >= 3:
    st.success("🔥 Tu es en série ! Continue comme ça !")

#Mode parent
with st.expander("👨‍👩‍👧 Mode parent", expanded=False):
    if not is_parent():
        st.write("Active le mode parent pour suivre un enfant.")
        if st.button("Activer le mode parent"):
            if set_parent_role(current_email):
                st.success("Mode parent activé.")
                st.rerun()
    else:
        st.success("Mode parent actif")

        child_email = st.text_input("Email de l'enfant à suivre")

        if st.button("Associer cet enfant"):
            linked = parent_link_child(child_email, current_email)
            if linked:
                st.success("Enfant associé.")
                st.rerun()
            else:
                st.error("Aucun profil enfant trouvé avec cet email.")

        children = get_children_for_parent(current_email)

        st.write("### Enfants associés")

        if children:
            for child in children:
                with st.expander(f"{child.get('email')} — {child.get('xp',0)} XP"):
                    st.write(f"🔥 Streak : {child.get('streak', 0)} jour(s)")
                    st.write(f"🎨 Niveau dessin : {child.get('niveau_dessin') or '—'}")

                    child_analyses = get_analyses(child.get("email"))

                    st.write(f"📚 Analyses : {len(child_analyses)}")

                    for a in child_analyses[:5]:
                        st.write(f"⭐ Note : {a.get('note', '—')}/10")
                        if a.get("image_url") and str(a.get("image_url")).startswith("http"):
                            st.image(a.get("image_url"), width=200)
        else:
            st.info("Aucun enfant associé pour le moment.")

# XP
xp = profile.get("xp", 0)

#Badges
analyses = get_analyses(current_email)
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

    current_email = current_email  # 👈 ICI

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
        try:
            xp = profile.get("xp", 0)
            level = xp // 100
            file_bytes = file.getvalue()

            data = analyze(
                file_bytes,
                file.type,
                profile.get("age") or 10,
                profile.get("niveau_dessin") or "Débutant",
                level
            )

            raw_note = data.get("note", 0)
            try:
                if isinstance(raw_note, int):
                    note = raw_note
                else:
                    note = int(str(raw_note).split("/")[0].strip())
            except Exception:
                note = 0

            xp_gain = note * 5

            if is_challenge:
                xp_gain += 25

            new_xp = xp + xp_gain

            xp_gain = note * 5

            if is_challenge:
                xp_gain += 25

                streak = profile.get("streak", 0)

            if streak >= 3:
                xp_gain += 10

            if streak >= 7:
                xp_gain += 20

            import uuid
            file_ext = file.name.split(".")[-1]
            file_name = f"{current_email}/{uuid.uuid4()}.{file_ext}"

            supabase.storage.from_("drawings").upload(
                file_name,
                file_bytes,
                {"content-type": file.type}
            )

            image_url = supabase.storage.from_("drawings").get_public_url(file_name)

            save_analysis(current_email, image_url, data, is_challenge)

            update_xp(current_email, new_xp)
            st.session_state.profile["xp"] = new_xp
            profile["xp"] = new_xp

            st.toast("✅ Analyse faite !")
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

        except Exception as e:
            st.error("Erreur pendant l'analyse")
            st.code(str(e))

# ----------------------------
# GALERIE
# ----------------------------
with st.expander("🖼️ Galerie de tes dessins", expanded=False):
    analyses = get_analyses(current_email)

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
    analyses = get_analyses(current_email)
    for a in analyses:
        st.write(a.get("note"))

# ----------------------------
# ADMIN
# ----------------------------
if is_admin():
    st.write("---")
    with st.expander("🛠️ Admin"):
        st.write("Mode admin actif")