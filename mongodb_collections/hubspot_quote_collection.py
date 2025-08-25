from datetime import datetime
from bson import ObjectId
from cpq.db import db


class HubSpotQuoteCollection:
    """Stores quotes created from HubSpot data (deals/contacts).

    Expected schema (flexible):
    {
        _id,
        source: 'hubspot',
        hubspot_deal_id?, hubspot_contact_id?,
        client: { name, company, email, phone },
        service_type?, total_cost?,
        created_at, updated_at
    }
    """

    def __init__(self):
        self.collection = db["hubspot_quotes"]

    def create_quote(self, quote_data: dict):
        now = datetime.now()
        quote_data.setdefault("source", "hubspot")
        quote_data.setdefault("created_at", now)
        quote_data["updated_at"] = now
        return self.collection.insert_one(quote_data)

    def get_quote_by_id(self, quote_id: str):
        try:
            return self.collection.find_one({"_id": ObjectId(quote_id)})
        except Exception:
            return None

    def get_all_quotes(self, limit: int = 100):
        return list(self.collection.find({}).sort("created_at", -1).limit(limit))


