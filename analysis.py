import json
import uuid
import time
from typing import Any

import streamlit as st
from google import genai
from google.genai import types

from utils import supabase


client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


# ----------------------------
# OUTILS
# ----------------------------
def parse_note(value: Any) -> int:
    try:
        note = int(str(value).split("/")[0].strip())
        return max(0, min(note, 10))
    except Exception:
        return 0


# ----------------------------
# ANALYSE GEMINI
# ----------------------------
def analyze_drawing(
    image_bytes: bytes,
    mime_type: str,
    age: int = 10,
    niveau: str = "Débutant",
    level: int = 0,
) -> dict[str, Any] | None:
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

        data["note"] = parse_note(data.get("note"))

        if not isinstance(data.get("points_forts"), list):
            data["points_forts"] = []

        if not isinstance(data.get("ameliorations"), list):
            data["ameliorations"] = []

        data.setdefault("defi", "")
        data.setdefault("message_coach", "")

        return data

    except Exception as e:
        error_text = str(e)

        if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
            st.warning("⏳ Quota Gemini atteint. Réessaie dans environ une minute.")
        elif "503" in error_text or "UNAVAILABLE" in error_text:
            st.warning("⏳ Gemini est temporairement surchargé. Réessaie dans quelques instants.")
        else:
            st.error("Erreur Gemini")
            st.code(error_text)

        return None


# ----------------------------
# STORAGE
# ----------------------------
def upload_image(email: str, uploaded_file: Any) -> str:
    file_bytes = uploaded_file.getvalue()
    file_ext = uploaded_file.name.split(".")[-1].lower()
    file_name = f"{email}/{uuid.uuid4()}.{file_ext}"

    supabase.storage.from_("drawings").upload(
        file_name,
        file_bytes,
        {"content-type": uploaded_file.type},
    )

    return supabase.storage.from_("drawings").get_public_url(file_name)


# ----------------------------
# SAUVEGARDE ANALYSE
# ----------------------------
def save_analysis(
    email: str,
    image_url: str,
    analysis: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        note = parse_note(analysis.get("note"))

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

    except Exception as e:
        st.error("Erreur sauvegarde analyse Supabase")
        st.code(str(e))
        st.stop()


# ----------------------------
# XP
# ----------------------------
def update_xp(
    email: str,
    profile: dict[str, Any],
    note: int,
) -> tuple[dict[str, Any], int]:
    xp_gain = note * 5
    new_xp = (profile.get("xp", 0) or 0) + xp_gain

    result = (
        supabase.table("profiles")
        .update({"xp": new_xp})
        .eq("email", email)
        .execute()
    )

    new_profile = result.data[0] if result.data else profile

    return new_profile, xp_gain