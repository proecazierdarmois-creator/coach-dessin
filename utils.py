from supabase import create_client
import streamlit as st
from datetime import date, timedelta

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)
def update_streak(email):
    today = date.today()

    profile = get_profile(email)
    if not profile:
        return 0

    streak = profile.get("streak", 0) or 0
    last_active = profile.get("last_active_date")

    if last_active:
        last_active = date.fromisoformat(str(last_active))

    if last_active == today:
        return streak

    if last_active == today - timedelta(days=1):
        streak += 1
    else:
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

    return result.data[0] if result.data else profile

def is_admin(email):
    admin_emails = [
        "pro.ecazierdarmois@gmail.com",
        "eliel2024@outlook.fr"
    ]
    return email in admin_emails


def get_all_profiles():
    result = (
        supabase.table("profiles")
        .select("*")
        .neq("email", "test@example.com")
        .order("xp", desc=True)
        .execute()
    )
    return result.data or []


def admin_update_xp(email, new_xp):
    result = (
        supabase.table("profiles")
        .update({"xp": new_xp})
        .eq("email", email)
        .execute()
    )
    return result.data[0] if result.data else None


def admin_delete_analysis(analysis_id):
    supabase.table("analyses").delete().eq("id", analysis_id).execute()

def get_profile(email):
    result = supabase.table("profiles").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None

def ensure_profile(email):
    # 👉 ignore les faux emails
    if not email or email == "test@example.com":
        return None

    profile = get_profile(email)
    if profile:
        return profile

    result = supabase.table("profiles").insert({
        "email": email,
        "xp": 0,
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