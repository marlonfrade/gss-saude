import requests
import json
import logging

logger = logging.getLogger(__name__)

class TallosAPI:
    def __init__(self, token):
        self.base_url = "https://api.tallos.com.br"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.token = token

    def get_chat_history(self):
        """Fetch chat history from Tallos API"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/chat/history",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching chat history: {e}")
            return None

    def send_message(self, customer_id, message, operator_id=None):
        """Send a message through Tallos API
        
        Args:
            customer_id (str): ID of the customer to send message to
            message (str): Message content to send
            operator_id (str, optional): ID of the operator sending the message
            
        Returns:
            dict: Response from API if successful, None if error
        """
        try:
            payload = {
                "message": message,
                "sent_by": "operator",
                "operator": operator_id
            }

            response = requests.post(
                f"{self.base_url}/v2/messages/{customer_id}/send",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return {"status": "success", "response": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            return {"status": "error", "message": str(e)}

    def get_customers(self, limit=1000, page=1, channels=None):
        """Fetch customers from Tallos API"""
        try:
            params = {
                'limit': limit,
                'page': page
            }
            if channels:
                params['channels'] = channels

            response = requests.get(
                f"{self.base_url}/v2/customers",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching customers: {e}")
            return None
    def get_employees(self):
        """Fetch employees from Tallos API"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/employees",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching employees: {e}")
            return None
    def get_templates(self):
        """Fetch message templates from Tallos API"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/template/all",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching templates: {e}")
            return None
    def create_contact(self, contact_data):
        """Create a new contact in Tallos API
        
        Args:
            contact_data (dict): Complete contact information following Tallos API format
                
        Returns:
            dict: Response from API if successful, None if error
        """
        try:
            response = requests.post(
                f"{self.base_url}/v2/contacts/whatsapp-business-by-brokers",
                headers=self.headers,
                json=contact_data
            )
            logger.info(f"Contact data: {contact_data}")
            logger.info(f"Response: {response.json()}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating contact: {e}")
            return None
    def get_whatsapp_integrations(self):
        """Fetch WhatsApp integrations from Tallos API"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/whatsapp/integrations/official",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching WhatsApp integrations: {e}")
            return None
