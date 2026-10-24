"""
AI-powered search using Claude API
"""
import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


def _get_client():
    return Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def search_notes(query: str, notes: list[dict]) -> str:
    """
    Use Claude to find the most relevant notes for a query.
    Returns a formatted answer string.
    """
    if not notes:
        return "Hozircha hech qanday eslatma saqlanmagan."

    notes_text = ""
    for i, note in enumerate(notes, 1):
        notes_text += f"\n[{i}] ID:{note['id']} | Sarlavha: {note['title']}\n"
        notes_text += f"    Sana: {note['created_at'][:16].replace('T', ' ')}\n"
        notes_text += f"    Mazmun: {note['content']}\n"

    prompt = f"""Siz shaxsiy yordamchisiz. Foydalanuvchi quyidagi so'rovni berdi:
"{query}"

Foydalanuvchining barcha eslatmalari:
{notes_text}

Vazifangiz:
1. So'rovga eng mos keladigan eslatma(lar)ni toping
2. Javobni o'zbek tilida, qisqa va aniq yozing
3. Eslatma topilsa: sarlavha, sana va mazmunini ko'rsating
4. Topilmasa: "Bunday ma'lumot topilmadi" deya xabar bering
5. Agar bir nechta mos bo'lsa, hammasini ko'rsating"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def parse_reminder_datetime(text: str) -> dict:
    """
    Use Claude to parse natural language date/time from user input.
    Returns: {"task": "...", "datetime": "YYYY-MM-DDTHH:MM:SS", "error": null}
    """
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    prompt = f"""Hozirgi vaqt: {now}

Foydalanuvchi quyidagi xabarni yubordi:
"{text}"

Bu xabardan vazifa va eslatma vaqtini ajratib oling.

Quyidagi JSON formatda javob bering (boshqa hech narsa yozmang):
{{
  "task": "vazifa matni",
  "datetime": "YYYY-MM-DDTHH:MM:SS",
  "error": null
}}

Agar vaqt aniqlab bo'lmasa:
{{
  "task": null,
  "datetime": null,
  "error": "Vaqt aniqlanmadi. Iltimos, aniqroq yozing. Masalan: ertaga soat 14:00 da uchrashuv"
}}

Muhim: faqat JSON qaytaring, boshqa matn yo'q."""

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
