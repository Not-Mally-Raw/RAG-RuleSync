import urllib.request
import ssl

try:
    print("Testing connection to Groq in Python...")
    # Bypass SSL verification to check if SSL interception is the cause
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    response = urllib.request.urlopen("https://api.groq.com/openai/v1/models", context=ctx)
    print("Success! Status code:", response.status)
except Exception as e:
    print("Failed to connect:", e)
    