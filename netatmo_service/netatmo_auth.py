import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
INITIAL_REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

TOKEN_URL = "https://api.netatmo.com/oauth2/token"
TOKENS_FILE = "tokens.json"


def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)

    data = {
        "refresh_token": INITIAL_REFRESH_TOKEN,
        "access_token": None,
        "expires_at": 0
    }
    save_tokens(data)
    return data


def save_tokens(data):
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def refresh_access_token():
    tokens = load_tokens()

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = requests.post(TOKEN_URL, data=payload, timeout=10)
    response.raise_for_status()

    data = response.json()

    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + data.get("expires_in", 10800) - 60
    }

    save_tokens(tokens)
    return tokens["access_token"]


def get_access_token():
    tokens = load_tokens()
    if tokens["access_token"] and time.time() < tokens["expires_at"]:
        return tokens["access_token"]

    return refresh_access_token()
