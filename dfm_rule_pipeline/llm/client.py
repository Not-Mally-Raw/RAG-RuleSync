import os
import time
from openai import OpenAI

# Import the single source of truth configuration
from dfm_rule_pipeline.config import LLM_MODEL, GROQ_API_KEY_LIST

class LLMClient:
    def __init__(self):
        self.clients = []
        for key in GROQ_API_KEY_LIST:
            self.clients.append(OpenAI(
                base_url="https://api.groq.com/openai/v1", 
                api_key=key,
                timeout=60.0
            ))
            
        if not self.clients:
            print("⚠️ Warning: No GROQ_API_KEYS found in .env or environment.")
        
        self.model = LLM_MODEL
        self.current_client_idx = 0

    def call(self, prompt: str) -> str:
        """
        Calls Groq API using round-robin keys. If a key hits a rate limit,
        we fail immediately per user request so the process can be halted.
        """
        if not self.clients:
            raise Exception("No Groq API keys configured.")
            
        # Select client and advance round-robin index
        client = self.clients[self.current_client_idx]
        used_idx = self.current_client_idx
        self.current_client_idx = (self.current_client_idx + 1) % len(self.clients)
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"    ⚠️ Groq Failed on Key #{used_idx + 1}: {e}")
            raise Exception(f"Fatal LLM Error on Key #{used_idx + 1}: {e}")