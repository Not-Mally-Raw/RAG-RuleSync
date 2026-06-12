import os
from openai import OpenAI
from dotenv import load_dotenv

# Load key from .env
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

print("Initializing client...")
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)

try:
    print("Calling Groq API (models.list)...")
    response = client.models.list()
    print("\n✅ Success! Connection works. Available models:")
    for m in response.data[:3]:
        print("-", m.id)
except Exception as e:
    print("\n❌ Failed to connect:", e)