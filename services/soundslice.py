from io import BytesIO
from soundsliceapi import Client, Constants
from typing import Optional
import os
from dotenv import load_dotenv
from pathlib import Path

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

    def create_and_upload_slice(self, score_name: str, musicxml: Optional[str] = None, title: Optional[str] = None, composer: Optional[str] = None) -> str:
        """Create a new Soundslice score and upload notation."""
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
        if musicxml:
            fp = BytesIO(musicxml.encode('utf-8'))
        else:
            fp = open(MUSIC_DIR + "/" + score_name, "rb")
        
        try:
            # Upload the notation
            self.client.upload_slice_notation(
                scorehash=scorehash,
                fp=fp,
                callback_url=callback_url
            )
        finally:
            fp.close()
        
        return scorehash 