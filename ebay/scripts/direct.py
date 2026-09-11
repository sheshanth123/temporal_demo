"""Standalone eBay API Client.

Directly test authentication, search, and item detail retrieval
without requiring Temporal server or worker processes.
"""

"""CLI Tool to directly test eBay API calls for token generation, search, and fetching items."""

import argparse
import base64
import json
import sys
from typing import Any

import httpx

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workers', 'extractor')))
from config import (
    EBAY_ACCEPT_LANGUAGE,
    EBAY_BASE_URL,
    EBAY_CA_BUNDLE,
    EBAY_CLIENT_ID,
    EBAY_CLIENT_SECRET,
    EBAY_ENDUSER_CTX,
    EBAY_MARKETPLACE_ID,
    EBAY_VERIFY_SSL,
    SUPPORTED_MARKETPLACES,
)

VERIFY_SSL = EBAY_CA_BUNDLE or EBAY_VERIFY_SSL


class EbayApiClient:
    """Convenience client for querying eBay Browse and Identity REST APIs directly."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        marketplace_id: str | None = None,
        language: str | None = None,
        enduser_ctx: str | None = None,
    ):
        self.client_id = client_id or EBAY_CLIENT_ID
        self.client_secret = client_secret or EBAY_CLIENT_SECRET
        self.base_url = (base_url or EBAY_BASE_URL).rstrip("/")
        self.marketplace_id = marketplace_id or EBAY_MARKETPLACE_ID
        self.language = language or EBAY_ACCEPT_LANGUAGE
        self.enduser_ctx = enduser_ctx or EBAY_ENDUSER_CTX
        self._token: str | None = None

        if not self.client_id or not self.client_secret:
            raise ValueError("Missing EBAY_CLIENT_ID or EBAY_CLIENT_SECRET.")

    def get_headers(self, marketplace_id: str | None = None) -> dict[str, str]:
        """Generate common headers for Browse API calls."""
        if not self._token:
            self.get_token()

        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-EBAY-C-MARKETPLACE-ID": marketplace_id or self.marketplace_id,
            "Accept": "application/json",
        }
        if self.language:
            headers["Accept-Language"] = self.language
        if self.enduser_ctx:
            headers["X-EBAY-C-ENDUSERCTX"] = self.enduser_ctx
        return headers

    def get_token(self, force_refresh: bool = False) -> str:
        """Fetch an OAuth 2.0 Client Credentials Access Token from eBay."""
        if self._token and not force_refresh:
            return self._token

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        with httpx.Client(timeout=30.0, verify=VERIFY_SSL) as client:
            resp = client.post(
                f"{self.base_url}/identity/v1/oauth2/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {encoded}",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            return self._token

    def search_items(
        self,
        query: str,
        limit: int = 5,
        marketplace_id: str | None = None,
        raw: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Search items using the Browse API (/buy/browse/v1/item_summary/search)."""
        headers = self.get_headers(marketplace_id=marketplace_id)
        with httpx.Client(timeout=30.0, verify=VERIFY_SSL) as client:
            resp = client.get(
                f"{self.base_url}/buy/browse/v1/item_summary/search",
                headers=headers,
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            if raw:
                return data
            return data.get("itemSummaries", [])

    def get_item(
        self,
        item_id: str,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch item details using the Browse API (/buy/browse/v1/item/{item_id})."""
        headers = self.get_headers(marketplace_id=marketplace_id)
        with httpx.Client(timeout=30.0, verify=VERIFY_SSL) as client:
            resp = client.get(
                f"{self.base_url}/buy/browse/v1/item/{item_id}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


def main() -> None:
    queries_file = r"scripts\search_queries.txt"
    output_file = "item_ids.txt"
    marketplace = None
    limit = 3

    import os
    if not os.path.exists(queries_file):
        print(f"Error: Queries file '{queries_file}' not found.")
        return

    with open(queries_file, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]

    if not queries:
        print("No queries found in file.")
        return

    client = EbayApiClient(marketplace_id=marketplace)
    print("Fetching OAuth Token...")
    client.get_token()

    all_item_ids = []

    for query in queries:
        print(f"Searching for: '{query}'...")
        items = client.search_items(query, limit=limit)
        if not items:
            print(f"  No items found for '{query}'.")
            continue
        
        count = 0
        for item in items:
            item_id = item.get("itemId")
            if item_id and item_id not in all_item_ids:
                all_item_ids.append(item_id)
                count += 1
        print(f"  Found {count} new unique items.")

    print(f"\nTotal unique item IDs found: {len(all_item_ids)}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item_id in all_item_ids:
            f.write(f"{item_id}\n")
            
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
