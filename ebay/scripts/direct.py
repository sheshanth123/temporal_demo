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
    parser = argparse.ArgumentParser(
        description="Single CLI tool to test eBay OAuth token, Search items, and Get item details."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: token
    subparsers.add_parser("token", help="Fetch and display OAuth 2.0 access token")

    # Command: search
    search_parser = subparsers.add_parser("search", help="Search items by query")
    search_parser.add_argument("query", type=str, help="Search query (e.g. 'gaming mouse')")
    search_parser.add_argument("--limit", "-l", type=int, default=3, help="Max items to retrieve")
    search_parser.add_argument("--marketplace", "-m", type=str, default=None, help="Marketplace ID (e.g. EBAY_US)")
    search_parser.add_argument("--raw", action="store_true", help="Print raw API response JSON")

    # Command: get
    get_parser = subparsers.add_parser("get", help="Get item details by Item ID")
    get_parser.add_argument("item_id", type=str, help="eBay item ID (e.g. 'v1|110590237758|0')")
    get_parser.add_argument("--marketplace", "-m", type=str, default=None, help="Marketplace ID (e.g. EBAY_US)")

    # Command: test (Runs token, search, and get in one shot)
    test_parser = subparsers.add_parser("test", help="Test token, search query, and fetch first item in one shot")
    test_parser.add_argument("--query", "-q", type=str, default="gaming mouse", help="Test query")
    test_parser.add_argument("--marketplace", "-m", type=str, default=None, help="Marketplace ID")

    # Command: marketplaces
    subparsers.add_parser("marketplaces", help="List supported eBay marketplaces")

    args = parser.parse_args()

    if not args.command:
        # Default behavior when no arguments are passed: run the complete test
        args.command = "test"
        args.query = "gaming mouse"
        args.marketplace = None

    if args.command == "marketplaces":
        print("\nSupported eBay Marketplaces:")
        for code, info in SUPPORTED_MARKETPLACES.items():
            print(f"  - {code:<16}: {info['name']} (locale: {info['default_locale']})")
        return

    client = EbayApiClient(marketplace_id=getattr(args, "marketplace", None))

    if args.command == "token":
        print("\n--- Requesting OAuth Token ---")
        token = client.get_token()
        print(f"Token: {token}\n")

    elif args.command == "search":
        print(f"\n--- Searching for '{args.query}' on {args.marketplace or client.marketplace_id} ---")
        result = client.search_items(args.query, limit=args.limit, raw=args.raw)
        if args.raw:
            print(json.dumps(result, indent=2))
        else:
            items = result if isinstance(result, list) else []
            print(f"Found {len(items)} items:\n")
            for idx, item in enumerate(items, start=1):
                item_id = item.get("itemId")
                title = item.get("title")
                price = item.get("price", {}).get("value")
                currency = item.get("price", {}).get("currency")
                print(f"[{idx}] {title}")
                print(f"    Item ID: {item_id}")
                print(f"    Price:   {price} {currency}")
                print(f"    URL:     {item.get('itemWebUrl')}\n")

    elif args.command == "get":
        print(f"\n--- Fetching Item Details for '{args.item_id}' on {args.marketplace or client.marketplace_id} ---")
        details = client.get_item(args.item_id)
        print(f"Title:     {details.get('title')}")
        print(f"Condition: {details.get('condition')}")
        price = details.get("price", {})
        print(f"Price:     {price.get('value')} {price.get('currency')}")
        print(f"Category:  {details.get('categoryPath')}")
        print(f"Item URL:  {details.get('itemWebUrl')}")
        print("\nRaw JSON preview (first 5 keys):")
        preview = {k: details[k] for k in list(details.keys())[:5]}
        print(json.dumps(preview, indent=2))

    elif args.command == "test":
        print(f"==================================================")
        print(f"eBay Direct API Test (Marketplace: {client.marketplace_id})")
        print(f"Base URL: {client.base_url}")
        print(f"==================================================")

        print("\n[Step 1] Fetching OAuth Token...")
        token = client.get_token()
        print(f"  ✓ Success! Token starts with: {token[:20]}...")

        print(f"\n[Step 2] Searching for: '{args.query}' (limit 2)...")
        items = client.search_items(args.query, limit=2)
        if not items:
            print("  ! No items found for query.")
            return

        print(f"  ✓ Success! Found {len(items)} items.")
        first_item = items[0]
        item_id = first_item.get("itemId")
        print(f"  - Title:   {first_item.get('title')}")
        print(f"  - Item ID: {item_id}")
        print(f"  - Price:   {first_item.get('price', {}).get('value')} {first_item.get('price', {}).get('currency')}")

        if item_id:
            print(f"\n[Step 3] Fetching full details for item '{item_id}'...")
            details = client.get_item(item_id)
            print(f"  ✓ Success! Item Details retrieved:")
            print(f"    - Title:       {details.get('title')}")
            print(f"    - Condition:   {details.get('condition')}")
            print(f"    - Seller:      {details.get('seller', {}).get('username')}")
            print(f"    - URL:         {details.get('itemWebUrl')}")


if __name__ == "__main__":
    main()
