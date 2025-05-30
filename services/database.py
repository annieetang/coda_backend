from pymongo import MongoClient
from bson.binary import Binary
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MongoDatabase:
    def __init__(self):
        """Initialize MongoDB connection."""
        # Get MongoDB configuration from environment variables
        mongodb_username = os.getenv('MONGODB_USERNAME')
        mongodb_password = os.getenv('MONGODB_PASSWORD')
        mongodb_host = os.getenv('MONGODB_HOST', 'localhost')
        mongodb_port = os.getenv('MONGODB_PORT', '27017')
        mongodb_database = os.getenv('MONGODB_DATABASE', 'coda')
        
        # Construct MongoDB URI based on whether authentication is provided
        if mongodb_username and mongodb_password:
            self.uri = os.getenv('MONGODB_URI')
        else:
            self.uri = f"mongodb://{mongodb_host}:{mongodb_port}"
            
        # Initialize MongoDB client and database
        self.client = MongoClient(self.uri)
        self.db = self.client[mongodb_database]
        self.scores = self.db['scores']
        
        # Create index for score_name if it doesn't exist
        self.scores.create_index('score_name', unique=True)

    def save_score_hash(self, score_name: str, score_hash: bytes):
        """Save a score hash to MongoDB."""
        self.scores.update_one(
            {'score_name': score_name},
            {'$set': {'score_hash': score_hash}},
            upsert=True
        )

    def get_score_hash(self, score_name: str) -> bytes:
        """Get a score hash from MongoDB."""
        result = self.scores.find_one({'score_name': score_name})
        return result['score_hash'] if result else None

    def get_all_score_hashes(self) -> dict:
        """Get all score hashes from MongoDB."""
        cursor = self.scores.find({})
        return {doc['score_name']: doc['score_hash'] for doc in cursor} 