# dfm_rule_pipeline/config.py
import os
from dotenv import load_dotenv

# Ensure .env is loaded once globally when config is imported
load_dotenv(override=True)

# LLM Configuration
LLM_PROVIDER = "groq"
LLM_MODEL = "openai/gpt-oss-20b"
keys_str = os.getenv("GROQ_API_KEYS", "")
if keys_str:
    GROQ_API_KEY_LIST = [k.strip() for k in keys_str.split(",") if k.strip()]
else:
    singular = os.getenv("GROQ_API_KEY")
    GROQ_API_KEY_LIST = [singular] if singular else []

# Embeddings Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
