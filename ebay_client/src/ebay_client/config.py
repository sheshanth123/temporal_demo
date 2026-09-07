import os
from dotenv import load_dotenv

load_dotenv()

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EBAY_BASE_URL = os.getenv("EBAY_BASE_URL", "https://api.sandbox.ebay.com")
EBAY_CA_BUNDLE = os.getenv("EBAY_CA_BUNDLE")
EBAY_VERIFY_SSL = os.getenv("EBAY_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}
TEMPORAL_UI_URL = os.getenv("TEMPORAL_UI_URL", "http://localhost:8233")

if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
    raise ValueError("Missing EBAY_CLIENT_ID or EBAY_CLIENT_SECRET in environment.")
