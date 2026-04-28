import json
import uuid
import streamlit as st
from google import genai
from google.genai import types
from utils import supabase


client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def analyze_drawing(image_bytes, mime_type, age=10, niveau="Débutant", level=0):
    prompt = f"""
Tu es un coach de dessin IA bienveillant.

Profil :
- âge : {age}
- niveau déclaré : {niveau}
- niveau XP : {level}

Réponds uniquement en JSON valide :
{{
  "note": 7,
  "points_forts": ["...", "..."],
  "ameliorations": ["...", "..."],
  "defi": "...",
  "message_coach": "..."
}}

La note doit être un entier entre 1 et 10.
"""

    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]

    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

            return json.loads(response.text)

        except Exception as e:
            continue

    st.error("❌ Aucun modèle Gemini disponible pour le moment. Réessaie dans quelques minutes.")
    return None


def save_analysis(email, image_url, analysis):
    note = int(str(analysis.get("note", 0)).split("/")[0].strip())

    result = supabase.table("analyses").insert({
        "email": email,
        "image_url": image_url,
        "note": note,
        "points_forts": analysis.get("points_forts", []),
        "ameliorations": analysis.get("ameliorations", []),
        "defi": analysis.get("defi", ""),
        "message_coach": analysis.get("message_coach", ""),
    }).execute()

    return result.data[0] if result.data else None


def upload_image(email, uploaded_file):
    file_bytes = uploaded_file.getvalue()
    file_ext = uploaded_file.name.split(".")[-1]
    file_name = f"{email}/{uuid.uuid4()}.{file_ext}"

    supabase.storage.from_("drawings").upload(
        file_name,
        file_bytes,
        {"content-type": uploaded_file.type}
    )

    return supabase.storage.from_("drawings").get_public_url(file_name)


def update_xp(email, profile, note):
    xp_gain = note * 5
    new_xp = profile.get("xp", 0) + xp_gain

    result = (
        supabase.table("profiles")
        .update({"xp": new_xp})
        .eq("email", email)
        .execute()
    )

    return result.data[0] if result.data else profile, xp_gain