import json
import tkinter as tk
from tkinter import messagebox

from ebay_client.auth import get_application_token
from ebay_client.client import EbayBrowseClient
from ebay_client.config import TEMPORAL_UI_URL


def wait_for_termination() -> None:
    """Keep the session alive until the user clicks the terminate button."""
    window = tk.Tk()
    window.title("eBay Client")
    window.geometry("360x140")
    window.resizable(False, False)

    tk.Label(
        window,
        text="eBay session is active.",
        font=("Segoe UI", 12),
    ).pack(pady=(24, 12))

    def terminate() -> None:
        if messagebox.askyesno("Terminate session", "Terminate the eBay session?"):
            window.destroy()

    tk.Button(
        window,
        text="Terminate session",
        command=terminate,
        width=20,
    ).pack()
    window.mainloop()


def main():
    print(f"Temporal UI: {TEMPORAL_UI_URL}")
    print("Start Temporal separately with: temporal server start-dev")
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
        wait_for_termination()
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
    wait_for_termination()


if __name__ == "__main__":
    main()
