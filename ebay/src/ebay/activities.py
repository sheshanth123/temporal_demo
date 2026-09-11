"""Temporal activities that call eBay and persist pipeline data."""

import asyncio
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
    """
    Constructs the HTTP headers required by the eBay Browse API.
    
    Why it's required:
    - The eBay REST APIs strictly require the `Authorization` header for access.
    - The `X-EBAY-C-MARKETPLACE-ID` header is mandatory to tell eBay which 
      regional market (e.g., US, UK, Germany) you are querying, which dictates 
      the currency, pricing, and availability returned.
    """
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
    """
    Authenticates with eBay's OAuth2 endpoint using the application's client credentials.
    
    What it does: 
    Encodes the client ID and secret, makes a request to the eBay identity endpoint, 
    and returns a short-lived bearer access token. This token is passed to subsequent 
    API calls to prove the application has permission to access the eBay API.
    """
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
    """
    Reads a plain text file line by line and strips out whitespace and empty lines.
    
    What it does:
    Opens a file at the given path (e.g., `item_ids.txt`) and returns a Python list 
    of the lines. It is primarily used to load the initial list of item IDs that 
    the pipeline needs to process.
    """
    if not os.path.exists(file_path):
        return []
    with open(file_path, encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


@activity.defn
async def fetch_item_details_activity(params: dict[str, Any]) -> dict[str, Any]:
    """
    Fetches the full details of a single eBay item using its specific item ID.
    
    What it does:
    Calls the eBay Browse API (`/buy/browse/v1/item/{item_id}`) using the provided 
    OAuth token and marketplace headers, and returns the raw JSON response containing 
    the item's title, price, description, images, and other metadata.
    """
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
    """
    Saves raw JSON data to a file within a designated output directory.
    
    What it does:
    Takes an item's JSON payload and writes it to disk (e.g., inside `./ebay_items`). 
    The filename is safely generated from the item ID (replacing pipes with underscores). 
    This is used by the Enrichment Workflow to keep a raw copy of the data.
    """
    output_dir = params.get("output_dir", "./ebay_items")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{params['item_id'].replace('|', '_')}.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(params["data"], file, indent=2)
    return path


@activity.defn
async def read_yaml_config_activity(file_path: str) -> dict[str, Any]:
    """
    Loads a YAML configuration file from the filesystem into a Python dictionary.
    
    What it does:
    Reads a file like `config.yaml` and parses it. This is used by the Ingestion 
    Workflow to dynamically supply pipeline parameters (like page size, source platform, 
    and execution mode) without hardcoding them into the Python logic.
    """
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


@activity.defn
async def fetch_item_batch_activity(params: dict[str, Any]) -> dict[str, Any]:
    """
    Concurrently fetches details for a batch of eBay items by their IDs.
    
    What it does:
    Takes a list of item IDs (e.g., a chunk of 20) and uses `asyncio.gather` to make 
    parallel HTTP requests to the eBay Browse API for each individual item. It ignores 
    items that return a 404 (Not Found) and aggregates the successful responses into 
    a single list to return to the workflow.
    """
    headers = get_browse_headers(params["token"], params.get("marketplace_id"))
    
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
async def save_batch_yaml_activity(params: dict[str, Any]) -> str:
    """
    Appends a batch of structured records to a YAML file.
    
    What it does:
    Takes the structured, normalized records generated by the Ingestion Workflow 
    (which include metadata like RECORD_ID and BATCH_START_TIME) and appends them 
    safely to the main `ingestion_output.yaml` file so they can be processed downstream.
    """
    output_file = params["output_file"]
    records = params["records"]
    
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
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
    save_batch_yaml_activity
]
