"""Temporal activities that call eBay and persist pipeline data."""

import base64
import json
import os
from typing import Any

import httpx
from temporalio import activity
import yaml

from ebay.config import (
    EBAY_ACCEPT_LANGUAGE,
    EBAY_BASE_URL,
    EBAY_CA_BUNDLE,
    EBAY_CLIENT_ID,
    EBAY_CLIENT_SECRET,
    EBAY_ENDUSER_CTX,
    EBAY_MARKETPLACE_ID,
    EBAY_VERIFY_SSL,
)

VERIFY_SSL = EBAY_CA_BUNDLE or EBAY_VERIFY_SSL


def get_browse_headers(token: str, marketplace_id: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id or EBAY_MARKETPLACE_ID,
        "Accept": "application/json",
    }
    if EBAY_ACCEPT_LANGUAGE:
        headers["Accept-Language"] = EBAY_ACCEPT_LANGUAGE
    if EBAY_ENDUSER_CTX:
        headers["X-EBAY-C-ENDUSERCTX"] = EBAY_ENDUSER_CTX
    return headers



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
async def fetch_item_details_activity(params: dict[str, Any]) -> dict[str, Any]:
    headers = get_browse_headers(params["token"], params.get("marketplace_id"))
    async with httpx.AsyncClient(timeout=30.0, verify=VERIFY_SSL) as client:
        response = await client.get(
            f"{EBAY_BASE_URL}/buy/browse/v1/item/{params['item_id']}",
            headers=headers,
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

# --- Minerva Redesign Activities ---

ALL_ACTIVITIES = [fetch_oauth_token_activity, read_lines_from_file_activity, search_ebay_activity, append_items_to_file_activity, fetch_item_details_activity, save_item_json_activity]
import yaml
# --- Ebay Redesign Activities ---

@activity.defn
async def read_yaml_config_activity(file_path: str) -> dict[str, Any]:
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


@activity.defn
async def fetch_item_batch_activity(params: dict[str, Any]) -> dict[str, Any]:
    headers = get_browse_headers(params["token"], params.get("marketplace_id"))
    item_ids_str = ",".join(params["item_ids"])
    async with httpx.AsyncClient(timeout=30.0, verify=VERIFY_SSL) as client:
        response = await client.get(
            f"{EBAY_BASE_URL}/buy/browse/v1/item",
            params={"item_group_ids": item_ids_str}, # The standard get items endpoint might differ, using standard params. Actually item_ids is standard for getting multiple.
            # Using item_ids per eBay Browse API
        )
        if response.status_code == 400:
            # Let's fallback if item_group_ids vs item_ids is wrong for this sandbox env
            response = await client.get(
                f"{EBAY_BASE_URL}/buy/browse/v1/item",
                params={"item_ids": item_ids_str},
                headers=headers,
            )
    
    if response.status_code == 404:
        return {"items": []}
    response.raise_for_status()
    return response.json()
    import asyncio
    async def fetch_one(client, item_id):
        resp = await client.get(f"{EBAY_BASE_URL}/buy/browse/v1/item/{item_id}", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

    async with httpx.AsyncClient(timeout=30.0, verify=VERIFY_SSL, limits=httpx.Limits(max_connections=10)) as client:
        tasks = [fetch_one(client, item_id) for item_id in params["item_ids"]]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
    items = [r for r in results if r is not None]
    return {"items": items}


@activity.defn
async def save_minerva_batch_yaml_activity(params: dict[str, Any]) -> str:
async def save_batch_yaml_activity(params: dict[str, Any]) -> str:
    output_file = params["output_file"]
    records = params["records"]
    
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    # Dump records as a YAML list
    with open(output_file, "a", encoding="utf-8") as f:
        yaml.dump(records, f, default_flow_style=False, sort_keys=False)
        
    return output_file


ALL_ACTIVITIES = [
    fetch_oauth_token_activity, 
    read_lines_from_file_activity, 
    fetch_item_details_activity, 
    save_item_json_activity,
    read_yaml_config_activity,
    fetch_item_batch_activity,
    save_minerva_batch_yaml_activity
    save_batch_yaml_activity
]
