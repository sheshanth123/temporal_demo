import json
from ebay_client.auth import get_application_token
from ebay_client.client import EbayBrowseClient


def main():
    print("Obtaining OAuth token...")
    token = get_application_token()
    client = EbayBrowseClient(token=token)
    print("OAuth Token obtained successfully.\n")

    search_query = "diamond"
    print(f"--- Searching for: '{search_query}' ---")
    search_results = client.search_items(query=search_query, limit=10)

    item_summaries = search_results.get("itemSummaries", [])
    if not item_summaries:
        print("No items found. If on sandbox, ensure test inventory exists.")
        return

    print(f"Found {len(item_summaries)} items:")
    for item in item_summaries:
        price = item.get("price", {})
        print(f"- {item.get('title')} | Price: {price.get('value')} {price.get('currency')}")

    first_item_id = item_summaries[0].get("itemId")
    print(f"\n--- Fetching details for item ID: {first_item_id} ---")
    item_details = client.get_item(first_item_id)
    print(json.dumps({
        "title": item_details.get("title"),
        "price": item_details.get("price"),
        "condition": item_details.get("condition"),
        "itemLocation": item_details.get("itemLocation"),
    }, indent=2))


if __name__ == "__main__":
    main()
