import base64
import requests
from ebay_client.config import (
    EBAY_BASE_URL,
    EBAY_CA_BUNDLE,
    EBAY_CLIENT_ID,
    EBAY_CLIENT_SECRET,
    EBAY_VERIFY_SSL,
)


def get_application_token() -> str:
    """Fetch an OAuth 2.0 application access token using client credentials."""
    auth_url = f"{EBAY_BASE_URL}/identity/v1/oauth2/token"
    credentials = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    b64_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_credentials}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    response = requests.post(
        auth_url,
        headers=headers,
        data=data,
        timeout=30,
        verify=EBAY_CA_BUNDLE or EBAY_VERIFY_SSL,
    )
    response.raise_for_status()
    return response.json()["access_token"]
