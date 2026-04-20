import os

from dotenv import load_dotenv

load_dotenv()

AGENT_TOKEN = os.getenv("AGENT_TOKEN")

if not AGENT_TOKEN:
    raise ValueError("AGENT_TOKEN não foi definido no arquivo .env")