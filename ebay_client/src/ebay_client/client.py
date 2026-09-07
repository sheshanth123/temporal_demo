import requests
from ebay_client.config import EBAY_BASE_URL, EBAY_CA_BUNDLE, EBAY_VERIFY_SSL


class EbayBrowseClient:
    def __init__(self, token: str, marketplace_id: str = "EBAY_US"):
        self.base_url = EBAY_BASE_URL
        self.session = requests.Session()
        self.session.verify = EBAY_CA_BUNDLE or EBAY_VERIFY_SSL
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
            "Accept": "application/json",
        })

    def search_items(self, query: str, limit: int = 10) -> dict:
        """Search for listings using the Browse API."""
        endpoint = f"{self.base_url}/buy/browse/v1/item_summary/search"
        params = {"q": query, "limit": limit}
        response = self.session.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_item(self, item_id: str) -> dict:
        """Retrieve full item details for a specific item ID."""
        endpoint = f"{self.base_url}/buy/browse/v1/item/{item_id}"
        response = self.session.get(endpoint, timeout=30)
        response.raise_for_status()
        return response.json()
