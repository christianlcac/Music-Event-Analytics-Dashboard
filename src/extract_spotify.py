import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

ARTIST_NAMES = [
    "Josh Baker",
    "Kettama",
    "Prospa",
    "Chris Stassy",
    "Michael Jackson",
]


def get_access_token():
    """Read credentials and request a temporary Spotify access token."""
    load_dotenv(PROJECT_ROOT / ".env")

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing Spotify credentials. Check your project's .env file."
        )

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    response.raise_for_status()

    return response.json()["access_token"]


def search_artist(artist_name, access_token):
    """Retrieve artist search candidates from Spotify."""
    response = requests.get(
        "https://api.spotify.com/v1/search",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "q": artist_name,
            "type": "artist",
            "limit": 5,
        },
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    access_token = get_access_token()
    extracted_at = datetime.now(timezone.utc).isoformat()

    raw_responses = []
    artist_rows = []

    for artist_name in ARTIST_NAMES:
        print(f"Searching: {artist_name}")

        result = search_artist(artist_name, access_token)

        raw_responses.append({
            "search_name": artist_name,
            "extracted_at": extracted_at,
            "response": result,
        })

        candidates = result.get("artists", {}).get("items", [])

        exact_matches = [
            artist
            for artist in candidates
            if artist["name"].strip().casefold()
            == artist_name.strip().casefold()
        ]

        if len(exact_matches) != 1:
            print(
                f"  Needs manual review: "
                f"{len(exact_matches)} exact matches found."
            )
            continue

        artist = exact_matches[0]

        artist_rows.append({
            "search_name": artist_name,
            "artist_id": artist["id"],
            "artist_name": artist["name"],
            "spotify_url": artist.get("external_urls", {}).get("spotify"),
            "genres": "|".join(artist.get("genres") or []),
            "extracted_at": extracted_at,
        })

    json_path = RAW_DIR / "spotify_artist_search.json"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(raw_responses, file, ensure_ascii=False, indent=2)

    columns = [
        "search_name",
        "artist_id",
        "artist_name",
        "spotify_url",
        "genres",
        "extracted_at",
    ]

    csv_path = RAW_DIR / "spotify_artists.csv"
    pd.DataFrame(artist_rows, columns=columns).to_csv(
        csv_path,
        index=False,
        encoding="utf-8",
    )

    print(f"\nSaved {len(artist_rows)} matched artists.")
    print(f"Raw responses: {json_path}")
    print(f"Artist table: {csv_path}")


if __name__ == "__main__":
    main()