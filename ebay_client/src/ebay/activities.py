"""Temporal activities that call eBay and persist pipeline data."""

import base64
import json
import os
from typing import Any

import httpx
from temporalio import activity

from ebay_client.config import EBAY_BASE_URL, EBAY_CA_BUNDLE, EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_VERIFY_SSL

VERIFY_SSL = EBAY_CA_BUNDLE or EBAY_VERIFY_SSL


@activity.defn
async def fetch_oauth_token_activity() -> str:
    credentials = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    async with httpx.AsyncClient(timeout=30.0, verify=VERIFY_SSL) as client:
        response = await client.post(
        f"{EBAY_BASE_URL}/identity/v1/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {encoded}"},
        data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
        )
    response.raise_for_status()
    return response.json()["access_token"]


@activity.defn
async def read_lines_from_file_activity(file_path: str) -> list[str]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


@activity.defn
async def search_ebay_activity(params: dict[str, Any]) -> list[str]:
    async with httpx.AsyncClient(timeout=30.0, verify=VERIFY_SSL) as client:
        response = await client.get(
        f"{EBAY_BASE_URL}/buy/browse/v1/item_summary/search",
        headers={"Authorization": f"Bearer {params['token']}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US", "Accept": "application/json"},
        params={"q": params["query"], "limit": params.get("limit", 3)},
        )
    response.raise_for_status()
    return [item["itemId"] for item in response.json().get("itemSummaries", []) if "itemId" in item]


@activity.defn
async def append_items_to_file_activity(params: dict[str, Any]) -> int:
    file_path = params["file_path"]
    existing = set(await read_lines_from_file_activity(file_path))
    new_ids = [item_id for item_id in params["item_ids"] if item_id not in existing]
    if new_ids:
        with open(file_path, "a", encoding="utf-8") as file:
            file.write("".join(f"{item_id}\n" for item_id in new_ids))
    return len(new_ids)


@activity.defn
async def fetch_item_details_activity(params: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0, verify=VERIFY_SSL) as client:
        response = await client.get(
        f"{EBAY_BASE_URL}/buy/browse/v1/item/{params['item_id']}",
        headers={"Authorization": f"Bearer {params['token']}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US", "Accept": "application/json"},
        )
    response.raise_for_status()
    return response.json()


@activity.defn
async def save_item_json_activity(params: dict[str, Any]) -> str:
    output_dir = params.get("output_dir", "./ebay_items")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{params['item_id'].replace('|', '_')}.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(params["data"], file, indent=2)
    return path


ALL_ACTIVITIES = [fetch_oauth_token_activity, read_lines_from_file_activity, search_ebay_activity, append_items_to_file_activity, fetch_item_details_activity, save_item_json_activity]
