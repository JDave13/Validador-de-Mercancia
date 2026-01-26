# test_models.py
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("🔍 Buscando modelos disponibles para tu API KEY...")
for m in client.models.list(config={"page_size": 100}):
    if "generateContent" in m.supported_actions:
        print(f" - {m.name}")