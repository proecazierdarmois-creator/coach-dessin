from supabase import create_client
import streamlit as st

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)

def get_profile(email):
    result = supabase.table("profiles").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None

def ensure_profile(email):
    profile = get_profile(email)
    if profile:
        return profile

    result = supabase.table("profiles").insert({
        "email": email,
        "xp": 0,
    }).execute()

    return result.data[0]

def get_analyses(email):
    result = (
        supabase.table("analyses")
        .select("*")
        .eq("email", email)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []