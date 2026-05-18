import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Explicitly find .env relative to this file's location
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/.env"))
load_dotenv(dotenv_path)

_client = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        print(f"Connecting to: {uri[:40]}...")  # remove this line after confirming
        _client = MongoClient(uri)
    return _client

def get_db():
    client = get_client()
    db_name = os.getenv("MONGO_DB_NAME", "aaip_db")
    return client[db_name]