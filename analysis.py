import json
import uuid
import streamlit as st
from google import genai
from google.genai import types
from utils import supabase
import time

def analyze_drawing(image_bytes, mime_type, age=10, niveau="Débutant", level=0):
    prompt = f"""
Tu es un coach de dessin IA pour enfants.

Analyse le dessin et réponds UNIQUEMENT avec ce JSON exact :

{{
  "note": 7,
  "points_forts": [
    "point positif 1",
    "point positif 2"
  ],
  "ameliorations": [
    "conseil simple 1",
    "conseil simple 2"
  ],
  "defi": "un petit défi amusant pour le prochain dessin",
  "message_coach": "un message encourageant"
}}

Règles obligatoires :
- Ne décris pas seulement l'image.
- Donne une note entière entre 1 et 10.
- Les points_forts doivent être des qualités du dessin.
- Les ameliorations doivent être des conseils pour progresser.
- Réponds seulement en JSON, sans texte autour.

Profil :
- âge : {age}
- niveau déclaré : {niveau}
- niveau XP : {level}
"""

    try:
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

        data = json.loads(response.text)

        if "note" not in data:
            st.error("Gemini n'a pas renvoyé une analyse au bon format.")
            st.write(data)
            return None

        return data

    except Exception as e:
        st.error("Erreur Gemini")
        st.code(str(e))
        return None


client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


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