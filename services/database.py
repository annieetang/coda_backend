from pymongo import MongoClient
from bson.binary import Binary
import os
from dotenv import load_dotenv
from typing import Optional, Dict, List, Tuple

# Load environment variables
load_dotenv()

class MongoDatabase:
    def __init__(self):
        """Initialize MongoDB connection."""
        # Get MongoDB configuration from environment variables
        mongodb_username = os.getenv('MONGODB_USERNAME')
        mongodb_password = os.getenv('MONGODB_PASSWORD')
        mongodb_host = os.getenv('MONGODB_HOST')
        mongodb_port = os.getenv('MONGODB_PORT')
        mongodb_database = os.getenv('MONGODB_DATABASE')
        
        # Construct MongoDB URI based on whether authentication is provided
        if mongodb_username and mongodb_password:
            self.uri = os.getenv('MONGODB_URI')
        else:
            self.uri = f"mongodb://{mongodb_host}:{mongodb_port}"
            
        # Initialize MongoDB client and database
        self.client = MongoClient(self.uri)
        self.db = self.client[mongodb_database]
        self.scores = self.db['scores']
        self.exercises = self.db['exercises']

    def save_score(self, score_name: str, title: str = None, composer: str = None, data: bytes = None, score_hash: bytes = None) -> bool:
        """
        Save a score to MongoDB with all required fields.
        
        Args:
            score_name (str): Unique identifier for the score
            title (str, optional): Title of the score
            composer (str, optional): Name of the composer
            data (bytes, optional): The actual score data
            score_hash (bytes, optional): The score hash
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            if data is None:
                data = b''
            # if score already exists, ignore upload
            if self.scores.find_one({'score_name': score_name}):
                print("score already exists, ignoring upload")
                return True
            
            self.scores.update_one(
                {'score_name': score_name},
                {'$set': {
                    'title': title if title is not None else score_name,
                    'composer': composer if composer is not None else "",
                    'data': Binary(data),
                    'score_hash': score_hash
                }},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving score: {e}")
            return False
    
    def update_score_with_slicehash(self, score_name: str, soundslice_hash: str) -> bool:
        """
        Update a score with a Soundslice hash.
        """
        try:
            self.scores.update_one({'score_name': score_name}, {'$set': {'soundslice_hash': soundslice_hash}})
            return True
        except Exception as e:
            print(f"Error updating score with Soundslice hash: {e}")
            return False

    def get_score(self, score_name: str) -> Optional[Dict]:
        """
        Retrieve a complete score entry by its name.
        
        Args:
            score_name (str): The unique identifier of the score
            
        Returns:
            Optional[Dict]: Score document with all fields if found, None otherwise
        """
        result = self.scores.find_one({'score_name': score_name})
        if not result:
            return None
        
        return {
            'score_name': result['score_name'],
            'title': result.get('title', result['score_name']),
            'composer': result.get('composer'),
            'data': result.get('data'),
            'score_hash': result.get('score_hash')
        }

    def get_all_scores(self) -> List[Dict]:
        """
        Get all scores with their metadata (excluding XML data for efficiency).
        
        Returns:
            List[Dict]: List of score metadata
        """
        cursor = self.scores.find(
            {}, 
            {'xml_data': 0}  # Exclude XML data from results
        )
        return list(cursor)

    def delete_score(self, score_name: str) -> bool:
        """
        Delete a score from the database.
        
        Args:
            score_name (str): The unique identifier of the score
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            result = self.scores.delete_one({'score_name': score_name})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting score: {e}")
            return False 
    
    def save_exercise(self, score_name: str, title: str = None, composer: str = None, data: bytes = None, score_hash: bytes = None) -> bool:
        """
        Save an exercise to MongoDB with all required fields.
        """
        try:
            if data is None:
                data = b''
            self.exercises.update_one(
                {'score_name': score_name},
                {'$set': {
                    'title': title or score_name,
                    'composer': composer,
                    'data': Binary(data),
                    'score_hash': score_hash
                }},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving exercise: {e}")
            return False
    
    def update_exercise_with_slicehash(self, score_name: str, soundslice_hash: str) -> bool:
        """
        Update an exercise with a Soundslice hash.
        """
        try:
            self.exercises.update_one({'score_name': score_name}, {'$set': {'soundslice_hash': soundslice_hash}})
            return True
        except Exception as e:
            print(f"Error updating exercise with Soundslice hash: {e}")
            return False

    def get_exercise(self, score_name: str) -> Optional[Dict]:
        """
        Retrieve an exercise by its name.
        """
        result = self.exercises.find_one({'score_name': score_name})
        if not result:
            return None
        return result
