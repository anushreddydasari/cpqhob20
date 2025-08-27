import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HubSpotBasic:
    def __init__(self):
        self.api_key = os.getenv('HUBSPOT_API_KEY')
        if not self.api_key:
            raise ValueError("❌ HUBSPOT_API_KEY not found in .env file")
        
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        print(f"✅ API Key loaded: {self.api_key[:10]}...{self.api_key[-4:]}")
    
    def test_connection(self):
        """Test basic HubSpot API connection"""
        try:
            print("🔄 Testing HubSpot connection...")
            
            # Test with a simple endpoint
            url = f"{self.base_url}/crm/v3/objects/contacts"
            response = requests.get(url, headers=self.headers, params={"limit": 1})
            
            print(f"📡 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                total_contacts = data.get('total', 0)
                print(f"✅ SUCCESS! Connected to HubSpot")
                print(f"📊 Total contacts available: {total_contacts}")
                return {"success": True, "total_contacts": total_contacts}
                
            elif response.status_code == 401:
                print("❌ Unauthorized - Check your API key permissions")
                print("💡 Make sure your API key has these scopes:")
                print("   - CRM Access")
                print("   - Contacts (Read)")
                return {"success": False, "error": "Unauthorized"}
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_basic_contacts(self, limit=5):
        """Fetch basic contact information"""
        try:
            print(f"🔄 Fetching {limit} contacts from HubSpot...")
            
            url = f"{self.base_url}/crm/v3/objects/contacts"
            params = {
                "limit": limit,
                "properties": "firstname,lastname,email,phone,company,jobtitle"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                contacts = []
                
                for contact in data.get('results', []):
                    properties = contact.get('properties', {})
                    contact_info = {
                        "id": contact.get('id'),
                        "name": f"{properties.get('firstname', '')} {properties.get('lastname', '')}".strip(),
                        "email": properties.get('email', ''),
                        "phone": properties.get('phone', ''),
                        "company": properties.get('company', ''),
                        "job_title": properties.get('jobtitle', ''),
                        "source": "HubSpot"
                    }
                    contacts.append(contact_info)
                
                print(f"✅ Successfully fetched {len(contacts)} contacts")
                return {"success": True, "contacts": contacts, "total": len(contacts)}
                
            else:
                print(f"❌ Failed to fetch contacts: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Error fetching contacts: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_recent_contacts(self, limit=50):
        """Fetch most recently updated contacts using the CRM search API sorted by lastmodifieddate."""
        try:
            url = f"{self.base_url}/crm/v3/objects/contacts/search"
            payload = {
                "sorts": ["-lastmodifieddate"],
                "properties": [
                    "firstname",
                    "lastname",
                    "email",
                    "phone",
                    "company",
                    "jobtitle",
                    "lastmodifieddate"
                ],
                "limit": limit
            }
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}", "details": response.text}

            data = response.json()
            contacts = []
            for contact in data.get('results', []):
                props = contact.get('properties', {})
                contacts.append({
                    "id": contact.get('id'),
                    "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                    "email": props.get('email', ''),
                    "phone": props.get('phone', ''),
                    "company": props.get('company', ''),
                    "job_title": props.get('jobtitle', ''),
                    "source": "HubSpot",
                    "last_modified": props.get('lastmodifieddate')
                })
            return {"success": True, "contacts": contacts, "total": len(contacts)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_contact_by_email(self, email: str):
        """Fetch a single contact by email with core properties."""
        try:
            if not email:
                return {"success": False, "error": "email required"}

            url = f"{self.base_url}/crm/v3/objects/contacts/search"
            payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email
                            }
                        ]
                    }
                ],
                "properties": [
                    "firstname",
                    "lastname",
                    "email",
                    "phone",
                    "company",
                    "jobtitle"
                ],
                "limit": 1
            }

            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}", "details": response.text}

            data = response.json()
            results = data.get('results', [])
            if not results:
                return {"success": False, "error": "not_found"}

            contact = results[0]
            props = contact.get('properties', {})
            normalized = {
                "hubspot_id": contact.get('id'),
                "name": f"{props.get('firstname','')} {props.get('lastname','')}".strip(),
                "email": props.get('email',''),
                "phone": props.get('phone',''),
                "company": props.get('company',''),
                "job_title": props.get('jobtitle','')
            }
            return {"success": True, "contact": normalized}
        except Exception as e:
            return {"success": False, "error": str(e)}

def main():
    """Test the basic HubSpot connection"""
    print("🧪 Testing Basic HubSpot Connection")
    print("=" * 50)
    
    try:
        # Initialize connection
        hubspot = HubSpotBasic()
        
        # Test connection
        connection_result = hubspot.test_connection()
        
        if connection_result["success"]:
            print("\n🎉 HubSpot connection successful!")
            
            # Try to fetch some contacts
            contacts_result = hubspot.get_basic_contacts(limit=3)
            
            if contacts_result["success"]:
                print("\n📋 Sample Contacts from HubSpot:")
                for i, contact in enumerate(contacts_result["contacts"], 1):
                    print(f"   {i}. {contact['name']} - {contact['email']}")
                    print(f"      Company: {contact['company'] or 'N/A'}")
                    print(f"      Phone: {contact['phone'] or 'N/A'}")
                    print()
            else:
                print(f"⚠️ Could not fetch contacts: {contacts_result['error']}")
                
        else:
            print(f"\n❌ HubSpot connection failed: {connection_result['error']}")
            
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")

if __name__ == "__main__":
    main()
