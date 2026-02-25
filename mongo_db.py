from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from bson.json_util import dumps
from pymongo.errors import PyMongoError
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION')


class ChatHistory:
    """
    Saves and loads the chat history of the conversations we had with the AI
    """

    def __init__(self):
        self.client = MongoClient(MONGO_URI,tlsAllowInvalidCertificates=False)
        self.db = self.client[MONGO_DB]
        self.collection = self.db[MONGO_COLLECTION]
        self.collection.create_index("session_id",unique=True)

    def new_chat(self, session_id: Optional[str]):
        """
        Create a brand new chat document in MongoDB.
        Does NOT overwrite existing chats.
        """

        if not session_id:
            raise ValueError("session_id is required to create a new chat")

        doc = {
            "session_id": session_id,
            "messages_json": json.dumps([]),   # start empty
            "question": "",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self.collection.insert_one(doc)
            return doc  # return the newly created chat

        except DuplicateKeyError:
            # Chat already exists; do NOT recreate. Just return the existing one.
            existing = self.collection.find_one({"session_id": session_id})
            return self.convert_objectid(existing)

        except PyMongoError as e:
            raise e
    
    def save_chat_history(self, session_id: str, messages: List[Dict[str, Any]],question:str):
        """
        Persist messages to MongoDB (upsert) and update Redis cache if available.
        messages: list of {"role": "human"|"ai", "content": "..."}
        """
        doc = {
            "session_id": session_id,
            "messages_json": json.dumps(messages),
            "question":question,
            "updated_at": datetime.utcnow().isoformat(),
        }
    
        try:
            self.collection.update_one(
                {"session_id": session_id},
                {"$set": doc},
                upsert=True
            )
            self.collection.find()
        except PyMongoError as e:
            # raise or log — for now re-raise so caller knows
            raise
    def load_chat_history(self,session_id: str) -> List[Dict[str, Any]]:
        try:
            row = self.collection.find_one({"session_id": session_id}, {"_id": 0, "messages_json": 1})
        except PyMongoError:
            # on mongo error, return empty list to avoid crashing caller
            return []
    
        if not row or not row.get("messages_json"):
            return []

        try:
            messages = json.loads(row["messages_json"])
        except Exception:
            messages = []

        # populate redis cache (best-effort)
        # if self._redis and messages is not None:
        #     try:
        #         self._redis.set(self._redis_key(session_id), json.dumps(messages))
        #     except Exception:
        #         pass

        return messages
    
    

    def convert_objectid(self,obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {k: self.convert_objectid(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.convert_objectid(i) for i in obj]
        return obj

    def load_all(self):
        try:
            documents = list(self.collection.find())
            history = [self.convert_objectid(doc) for doc in documents]
            return history
        except PyMongoError:
            return []
        
    def clear_chat_history(self,session_id:str):
        """
        Delete chat history from MongoDB and Redis (if available).
        """
        try:
            self.collection.delete_one({"session_id": session_id})
        except PyMongoError:
            # ignore or re-raise depending on your needs
            pass