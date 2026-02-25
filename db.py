# db.py
import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
redis_client = None
use_redis = False
if REDIS_URL:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        use_redis = True
    except Exception:
        use_redis = False

from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLITE_URL = os.getenv("CHAT_SQLITE_PATH", "sqlite:///./chat_histories.db")
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_history"
    session_id = Column(String, primary_key=True, index=True)
    messages_json = Column(Text)

Base.metadata.create_all(bind=engine)


def save_chat_history(session_id: str, messages: List[Dict[str, Any]]):
    """
    messages: list of {"role": "human"|"ai", "content": "..."}
    """
    if use_redis and redis_client:
        redis_client.set(f"chat:{session_id}", json.dumps(messages))
        return

    db = SessionLocal()
    try:
        existing = db.query(ChatHistory).filter_by(session_id=session_id).first()
        if existing:
            existing.messages_json = json.dumps(messages)
        else:
            db.add(ChatHistory(session_id=session_id, messages_json=json.dumps(messages)))
        db.commit()
    finally:
        db.close()


def load_chat_history(session_id: str) -> List[Dict[str, Any]]:
    if use_redis and redis_client:
        raw = redis_client.get(f"chat:{session_id}")
        return [] if not raw else json.loads(raw)

    db = SessionLocal()
    try:
        row = db.query(ChatHistory).filter_by(session_id=session_id).first()
        return json.loads(row.messages_json) if row and row.messages_json else []
    finally:
        db.close()


def clear_chat_history(session_id: str):
    if use_redis and redis_client:
        redis_client.delete(f"chat:{session_id}")
        return

    db = SessionLocal()
    try:
        db.query(ChatHistory).filter_by(session_id=session_id).delete()
        db.commit()
    finally:
        db.close()






# db.py
# import os
# import json
# from typing import List, Dict, Any, Optional
# from dotenv import load_dotenv
# load_dotenv()

# REDIS_URL = os.getenv("REDIS_URL")  # if set, Redis will be used
# SQLITE_PATH = os.getenv("CHAT_SQLITE_PATH", "./chat_histories.db")

# # ---------- Redis backend (optional) ----------
# redis_client = None
# use_redis = False
# if REDIS_URL:
#     try:
#         import redis
#         redis_client = redis.from_url(REDIS_URL, decode_responses=True)
#         use_redis = True
#     except Exception:
#         use_redis = False

# # ---------- SQLite backend ----------
# import sqlite3
# _conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
# _cursor = _conn.cursor()
# # Create table for chat histories (session_id, messages_json)
# _cursor.execute("""
# CREATE TABLE IF NOT EXISTS chat_history (
#     session_id TEXT PRIMARY KEY,
#     messages_json TEXT
# )
# """)
# _conn.commit()

# def save_chat_history(session_id: str, messages: List[Dict[str, Any]]):
#     """
#     messages: list of {"role": "human"|"ai", "content": "..."}
#     """
#     if use_redis and redis_client:
#         redis_client.set(f"chat:{session_id}", json.dumps(messages))
#         return
#     # SQLite
#     _cursor.execute("""
#     INSERT INTO chat_history (session_id, messages_json)
#     VALUES (?, ?)
#     ON CONFLICT(session_id) DO UPDATE SET messages_json=excluded.messages_json
#     """, (session_id, json.dumps(messages)))
#     _conn.commit()

# def load_chat_history(session_id: str) -> List[Dict[str, Any]]:
#     if use_redis and redis_client:
#         raw = redis_client.get(f"chat:{session_id}")
#         if not raw:
#             return []
#         return json.loads(raw)
#     _cursor.execute("SELECT messages_json FROM chat_history WHERE session_id = ?", (session_id,))
#     row = _cursor.fetchone()
#     if not row:
#         return []
#     return json.loads(row[0])

# def clear_chat_history(session_id: str):
#     if use_redis and redis_client:
#         redis_client.delete(f"chat:{session_id}")
#         return
#     _cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
#     _conn.commit()


