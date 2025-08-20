import pymongo
import os
from dotenv import load_dotenv

load_dotenv()  # load variables from .env

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set. Please check your .env file.")

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB connection successful!")
    
    db = client["cpq_db"]
    quotes_collection = db["quotes"]
    clients_collection = db["clients"]  # New collection for client information
    hubspot_contacts_collection = db["hubspot_contacts"]  # New collection for HubSpot contacts
    quote_status_collection = db["quote_status"]  # New collection for quote status tracking
    
except pymongo.errors.ServerSelectionTimeoutError:
    print("❌ MongoDB connection failed: Server not reachable")
    raise
except pymongo.errors.ConnectionFailure:
    print("❌ MongoDB connection failed: Connection error")
    raise
except Exception as e:
    print(f"❌ MongoDB connection failed: {str(e)}")
    raise
