from openai import OpenAI

# Import the single source of truth configuration
from dfm_rule_pipeline.config import LLM_MAX_TOKENS, LLM_MODEL, GROQ_API_KEY_LIST

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
        self.max_tokens = LLM_MAX_TOKENS
        self.current_client_idx = 0

    def call(self, prompt: str, json_mode: bool = False) -> str:
        """
        Calls Groq API using round-robin keys. If the selected key fails
        because it is exhausted, invalid, or temporarily unavailable, try the
        next configured key before returning a fatal error.
        """
        if not self.clients:
            raise Exception("No Groq API keys configured.")

        start_idx = self.current_client_idx
        failures = []

        for attempt in range(len(self.clients)):
            used_idx = (start_idx + attempt) % len(self.clients)
            client = self.clients[used_idx]
            self.current_client_idx = (used_idx + 1) % len(self.clients)

            try:
                request_kwargs = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": self.max_tokens,
                }
                if json_mode:
                    request_kwargs["response_format"] = {"type": "json_object"}

                response = client.chat.completions.create(
                    **request_kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                message = str(e)
                failures.append(f"Key #{used_idx + 1}: {message}")
                print(f"    [Warning] Groq Failed on Key #{used_idx + 1}: {message}")

        joined_failures = " | ".join(failures)
        raise Exception(f"All Groq API keys failed after {len(self.clients)} attempts: {joined_failures}")
