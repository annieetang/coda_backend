from io import BytesIO
from soundsliceapi import Client, Constants
from typing import Optional
import os
from dotenv import load_dotenv
from pathlib import Path
from services.database import MongoDatabase

db = MongoDatabase()
load_dotenv()

SOUNDSLICE_APP_ID = os.getenv("SOUNDSLICE_APP_ID")
SOUNDSLICE_PASSWORD = os.getenv("SOUNDSLICE_PASSWORD")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
MUSIC_DIR = os.path.join(PROJECT_ROOT, "cs99/coda_backend/music_scores")

class SoundsliceService:
    def __init__(self):
        self.client = Client(SOUNDSLICE_APP_ID, SOUNDSLICE_PASSWORD)

    def create_and_upload_slice(self, score_name: str, musicxml: str, title: str, composer: str) -> str:
        """Create a new Soundslice score and upload notation."""

        if not musicxml:
            # try to find the score in the database
            score = db.get_score(score_name)
            if score:
                musicxml = score['data']
                if not musicxml:
                    raise ValueError("Score data is empty")
            else:
                raise ValueError("Score not found")

        # Create a new slice
        res = self.client.create_slice(
            name=title,
            artist=composer,
            embed_status=Constants.EMBED_STATUS_ON_ALLOWLIST,
        )
        scorehash = res['scorehash']
        
        # Use environment-based callback URL
        callback_url = f"{BASE_URL}/slice_callback"
        
        # Handle the XML content
        if isinstance(musicxml, str):
            file_pointer = BytesIO(musicxml.encode('utf-8'))
        else:
            file_pointer = BytesIO(musicxml)
        
        try:
            # Upload the notation
            self.client.upload_slice_notation(
                scorehash=scorehash,
                fp=file_pointer,
                callback_url=callback_url
            )
        finally:
            file_pointer.close()
        
        return scorehash 