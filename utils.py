from datetime import date, timedelta
from typing import Any

import streamlit as st
from supabase import create_client


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
)


# ----------------------------
# PROFILS
# ----------------------------
def get_profile(email: str) -> dict[str, Any] | None:
    result = supabase.table("profiles").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None


def ensure_profile(email: str) -> dict[str, Any] | None:
    if not email or email == "test@example.com":
        return None

    profile = get_profile(email)
    if profile:
        return profile

    result = supabase.table("profiles").insert({
        "email": email,
        "xp": 0,
        "streak": 0,
    }).execute()

    return result.data[0] if result.data else None


# ----------------------------
# ANALYSES
# ----------------------------
def get_analyses(email: str) -> list[dict[str, Any]]:
    result = (
        supabase.table("analyses")
        .select("*")
        .eq("email", email)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ----------------------------
# STREAK
# ----------------------------
def update_streak(email: str) -> dict[str, Any] | None:
    today = date.today()

    profile = get_profile(email)
    if not profile:
        return None

    streak = profile.get("streak", 0) or 0
    last_active = profile.get("last_active_date")

    if last_active:
        last_active = date.fromisoformat(str(last_active))

    if last_active == today:
        return profile

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


# ----------------------------
# BADGES
# ----------------------------
def get_badges(email: str, xp: int, streak: int) -> list[str]:
    analyses = get_analyses(email)
    count = len(analyses)

    badges = []

    if count >= 1:
        badges.append("🎨 Premier dessin")

    if count >= 5:
        badges.append("🖼️ 5 dessins analysés")

    if count >= 10:
        badges.append("🏅 10 dessins analysés")

    if xp >= 100:
        badges.append("⭐ 100 XP")

    if xp >= 500:
        badges.append("🚀 500 XP")

    if streak >= 3:
        badges.append("🔥 Streak 3 jours")

    if streak >= 7:
        badges.append("🔥🔥 Streak 7 jours")

    if any((a.get("note") or 0) >= 8 for a in analyses):
        badges.append("🌟 Note de 8 ou plus")

    return badges


# ----------------------------
# LEADERBOARD
# ----------------------------
def get_leaderboard(limit: int = 20) -> list[dict[str, Any]]:
    result = (
        supabase.table("profiles")
        .select("email, xp, streak")
        .neq("email", "test@example.com")
        .order("xp", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []


# ----------------------------
# ADMIN
# ----------------------------
def is_admin(email: str) -> bool:
    admin_emails = [
        "pro.ecazierdarmois@gmail.com",
        "eliel2024@outlook.fr",
    ]
    return email in admin_emails


def get_all_profiles() -> list[dict[str, Any]]:
    result = (
        supabase.table("profiles")
        .select("*")
        .neq("email", "test@example.com")
        .order("xp", desc=True)
        .execute()
    )

    return result.data or []


def admin_update_xp(email: str, new_xp: int) -> dict[str, Any] | None:
    result = (
        supabase.table("profiles")
        .update({"xp": new_xp})
        .eq("email", email)
        .execute()
    )

    return result.data[0] if result.data else None


def admin_delete_analysis(analysis_id: int) -> None:
    supabase.table("analyses").delete().eq("id", analysis_id).execute()