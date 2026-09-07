import os
from dotenv import load_dotenv

load_dotenv()

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_BASE_URL = os.getenv("EBAY_BASE_URL", "https://api.sandbox.ebay.com")

if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
    raise ValueError("Missing EBAY_CLIENT_ID or EBAY_CLIENT_SECRET in environment.")
