"""Configuration parameters for the eBay Temporal pipeline."""

import os
from dotenv import load_dotenv

load_dotenv()

# eBay OAuth Credentials
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")

# eBay API Endpoint (defaults to Sandbox)
EBAY_BASE_URL = os.getenv("EBAY_BASE_URL", "https://api.sandbox.ebay.com")

# SSL Configuration (useful if behind a corporate proxy)
EBAY_CA_BUNDLE = os.getenv("EBAY_CA_BUNDLE")
EBAY_VERIFY_SSL = os.getenv("EBAY_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

# Temporal Server Configuration
TEMPORAL_UI_URL = os.getenv("TEMPORAL_UI_URL", "http://localhost:8233")
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")

# Temporal Task Queue Name (worker and workflows must match this)
TASK_QUEUE = os.getenv("TASK_QUEUE", "ebay-processing-queue")

# eBay Marketplace & Request Context Configuration
EBAY_MARKETPLACE_ID = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
EBAY_ACCEPT_LANGUAGE = os.getenv("EBAY_ACCEPT_LANGUAGE")
EBAY_ENDUSER_CTX = os.getenv("EBAY_ENDUSER_CTX")

# Standard eBay Marketplaces Reference
SUPPORTED_MARKETPLACES = {
    "EBAY_US": {"name": "United States", "default_locale": "en-US"},
    "EBAY_GB": {"name": "United Kingdom", "default_locale": "en-GB"},
    "EBAY_DE": {"name": "Germany", "default_locale": "de-DE"},
    "EBAY_AU": {"name": "Australia", "default_locale": "en-AU"},
    "EBAY_CA": {"name": "Canada", "default_locale": "en-CA"},
    "EBAY_FR": {"name": "France", "default_locale": "fr-FR"},
    "EBAY_IT": {"name": "Italy", "default_locale": "it-IT"},
    "EBAY_ES": {"name": "Spain", "default_locale": "es-ES"},
    "EBAY_AT": {"name": "Austria", "default_locale": "de-AT"},
    "EBAY_BE": {"name": "Belgium", "default_locale": "nl-BE"},
    "EBAY_CH": {"name": "Switzerland", "default_locale": "de-CH"},
    "EBAY_IE": {"name": "Ireland", "default_locale": "en-IE"},
    "EBAY_IN": {"name": "India", "default_locale": "en-IN"},
    "EBAY_HK": {"name": "Hong Kong", "default_locale": "zh-HK"},
    "EBAY_MY": {"name": "Malaysia", "default_locale": "en-MY"},
    "EBAY_PH": {"name": "Philippines", "default_locale": "en-PH"},
    "EBAY_SG": {"name": "Singapore", "default_locale": "en-SG"},
    "EBAY_PL": {"name": "Poland", "default_locale": "pl-PL"},
    "EBAY_NL": {"name": "Netherlands", "default_locale": "nl-NL"},
    "EBAY_MOTORS_US": {"name": "eBay Motors (US)", "default_locale": "en-US"},
}


if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
    raise ValueError("Missing EBAY_CLIENT_ID or EBAY_CLIENT_SECRET in environment.")
