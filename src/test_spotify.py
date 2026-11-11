import os
import requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

token_url = "https://accounts.spotify.com/api/token"

response = requests.post(
    token_url,
    data={"grant_type": "client_credentials"},
    auth=(client_id, client_secret),
)

response.raise_for_status()
token = response.json()["access_token"]

print("Spotify access token received successfully")