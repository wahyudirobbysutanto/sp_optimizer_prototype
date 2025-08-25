import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

def call_ai(user_message, related_schema):

    # 2. Build prompt untuk AI
    prompt = f"""
    You are a SQL performance tuning expert. Your job is assistant for Guardian-DB. You will help users with their questions about SQL performance tuning or sql query optimization.
    User asking: {user_message}

    Related schema: 
    {related_schema}
    """

    # print(prompt)

    # 3. Kirim ke Gemini (atau model lain)
    ai_response = ask_gemini(prompt)

    return ai_response

def ask_gemini(prompt):
    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "topK": 1,
            "topP": 0.1
        }
    }

    try:
        response = requests.post(GEMINI_URL, headers=headers, json=body, timeout=600)
        response.raise_for_status()
        result = response.json()
        
        print("✅ Gemini response received.")
        print(result)

        # cek struktur respons
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                return candidate["content"]["parts"][0].get("text", "")
        
        print("⚠️ Unexpected Gemini response:", result)
        return None

        # response = requests.post(GEMINI_URL, headers=headers, json=body,timeout=600)
        # response.raise_for_status()
        # result = response.json()
        # return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("❌ Gemini API error:", e)
        return None
