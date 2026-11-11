import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ARTISTS_FILE = RAW_DIR / "spotify_artists.csv"


def get_api_key():
    """Load the Last.fm API key from the project's .env file."""
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        raise ValueError("LASTFM_API_KEY is missing from your .env file.")

    return api_key


def get_top_tracks(artist_name, api_key, limit=10):
    """Request an artist's top tracks from Last.fm."""
    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "artist.getTopTracks",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
            "autocorrect": 0,
        },
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    # Last.fm can return an API error inside a JSON response.
    if "error" in data:
        raise RuntimeError(
            f"Last.fm error {data['error']}: {data.get('message', '')}"
        )

    return data


def main():
    api_key = get_api_key()

    if not ARTISTS_FILE.exists():
        raise FileNotFoundError(
            "spotify_artists.csv was not found. "
            "Run extract_spotify.py first."
        )

    artists = pd.read_csv(ARTISTS_FILE)
    artists = artists.dropna(subset=["artist_id", "artist_name"])
    artists = artists.drop_duplicates(subset=["artist_id"])

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    extracted_at = datetime.now(timezone.utc).isoformat()
    raw_responses = []
    track_rows = []
    failures = []

    for artist in artists.itertuples(index=False):
        print(f"Getting top tracks: {artist.artist_name}")

        try:
            data = get_top_tracks(artist.artist_name, api_key)

            raw_responses.append({
                "spotify_artist_id": artist.artist_id,
                "requested_artist": artist.artist_name,
                "extracted_at": extracted_at,
                "response": data,
            })

            tracks = data.get("toptracks", {}).get("track", [])

            # Handle a single track represented as an object.
            if isinstance(tracks, dict):
                tracks = [tracks]

            for position, track in enumerate(tracks, start=1):
                track_rows.append({
                    "spotify_artist_id": artist.artist_id,
                    "requested_artist": artist.artist_name,
                    "lastfm_artist_name": track.get(
                        "artist", {}
                    ).get("name"),
                    "track_name": track.get("name"),
                    "lastfm_rank": position,
                    "lastfm_playcount": track.get("playcount"),
                    "lastfm_listeners": track.get("listeners"),
                    "track_mbid": track.get("mbid"),
                    "lastfm_url": track.get("url"),
                    "source": "lastfm",
                    "extracted_at": extracted_at,
                })

            print(f"  Retrieved {len(tracks)} tracks.")

        except (requests.RequestException, RuntimeError, ValueError) as error:
            # Avoid logging request URLs, which contain the API key.
            failures.append({
                "artist_name": artist.artist_name,
                "error_type": type(error).__name__,
            })
            print(f"  Failed: {type(error).__name__}")

        time.sleep(1)

    json_path = RAW_DIR / "lastfm_top_tracks_raw.json"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(raw_responses, file, ensure_ascii=False, indent=2)

    columns = [
        "spotify_artist_id",
        "requested_artist",
        "lastfm_artist_name",
        "track_name",
        "lastfm_rank",
        "lastfm_playcount",
        "lastfm_listeners",
        "track_mbid",
        "lastfm_url",
        "source",
        "extracted_at",
    ]

    csv_path = RAW_DIR / "lastfm_top_tracks.csv"
    pd.DataFrame(track_rows, columns=columns).to_csv(
        csv_path,
        index=False,
        encoding="utf-8",
    )

    print(f"\nSaved {len(track_rows)} track records.")
    print(f"Failed artists: {len(failures)}")

    for failure in failures:
        print(f"  {failure['artist_name']}: {failure['error_type']}")

    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()