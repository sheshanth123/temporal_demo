# eBay Browse API Pipeline (Temporal-Powered)

A resilient, durable data pipeline built with [Temporal](https://temporal.io/) and Python to search eBay listings and enrich item details using eBay's Browse REST API.

---

## Architecture & How It Works

This project runs as a distributed workflow system separated into two primary workflows orchestrated by a local Temporal server:

```
                  ┌─────────────────────────────────┐
                  │      Temporal Server (Dev)      │
                  │   localhost:7233 / UI :8233     │
                  └───────────────┬─────────────────┘
                                  │ Task Queue:
                                  │ "ebay-processing-queue"
                                  ▼
┌─────────────────────────┐                ┌─────────────────────────┐
│       CLI Runner        │                │      Worker Process     │
│   (uv run ebay-run)     │                │   (uv run ebay-worker)  │
├─────────────────────────┤                ├─────────────────────────┤
│ • Submits Workflow 1    │                │ • Listens on task queue │
│ • Awaits result         │                │ • Executes Activities:  │
│ • Submits Workflow 2    │                │   - OAuth token fetch   │
│ • Awaits result         │                │   - eBay search / fetch │
└─────────────────────────┘                │   - File I/O operations │
                                           └─────────────────────────┘
```

### 1. Workflow 1: Search Pipeline (`EbaySearchPipelineWorkflow`)
1. **Reads Input Queries**: Loads search keywords from `search_queries.txt` via `read_lines_from_file_activity`.
2. **Authenticates with eBay**: Requests an OAuth 2.0 client credentials bearer token from eBay identity service via `fetch_oauth_token_activity`.
3. **Searches Listings**: Executes search queries via eBay's Browse API (`/buy/browse/v1/item_summary/search`) using `search_ebay_activity`.
4. **Persists Unique IDs**: Extracts item IDs, deduplicates against existing records, and writes new IDs to `item_ids.txt` via `append_items_to_file_activity`.

### 2. Workflow 2: Enrichment Pipeline (`EbayItemEnrichmentWorkflow`)
1. **Reads Item IDs**: Loads the list of item IDs from `item_ids.txt`.
2. **Re-authenticates / Gets Token**: Obtains an OAuth access token.
3. **Fetches Full Details**: Calls eBay's item details endpoint (`/buy/browse/v1/item/{item_id}`) for each item via `fetch_item_details_activity`.
4. **Saves Structured JSONs**: Persists raw JSON payloads for each item under `./ebay_item_jsons/` using `save_item_json_activity`.

### Resilience & Retry Policy
All network activities contacting eBay use an exponential backoff retry policy:
- **Initial Interval**: 2 seconds
- **Backoff Coefficient**: 2.0
- **Max Interval**: 30 seconds
- **Max Attempts**: 4 attempts

If eBay rate limits or temporarily fails, Temporal automatically pauses and retries the activity without losing workflow state or progress.

---

## Prerequisites

- **Python 3.11+**
- [**uv**](https://docs.astral.sh/uv/) (fast Python package and project manager)
- [**Temporal CLI**](https://docs.temporal.io/cli) (or Docker Desktop)
- **eBay Developer Account**: Client ID (`App ID`) and Client Secret (`Cert ID`) from the [eBay Developer Portal](https://developer.ebay.com/).

---

## Step-by-Step Setup & Execution

### Step 1: Install Dependencies
Open a PowerShell terminal in the repository root and run:

```powershell
uv sync
```

This creates the `.venv` virtual environment and installs all dependencies (`temporalio`, `httpx`, `python-dotenv`).

---

### Step 2: Configure Environment Variables
Create or update `.env` in the project root:

```env
# eBay API Credentials
EBAY_CLIENT_ID=your-ebay-app-client-id
EBAY_CLIENT_SECRET=your-ebay-cert-client-secret
EBAY_BASE_URL=https://api.sandbox.ebay.com

# Target Marketplace and Locale
EBAY_MARKETPLACE_ID=EBAY_US
EBAY_ACCEPT_LANGUAGE=en-US
# Optional contextual location:
# EBAY_ENDUSER_CTX=contextualLocation=country=US,zip=94043

# Temporal Server Configuration
TEMPORAL_HOST=localhost:7233
TEMPORAL_UI_URL=http://localhost:8233
TASK_QUEUE=ebay-processing-queue
```

---

### Step 3: Start the Temporal Development Server
Open **Terminal 1** and start the local Temporal cluster:

```powershell
temporal server start-dev
```

*Alternative (Docker)*:
```powershell
docker run --rm -p 7233:7233 -p 8233:8233 temporalio/auto-setup:latest
```

Once running:
- **Temporal Server Address**: `localhost:7233`
- **Temporal Web UI**: [http://localhost:8233](http://localhost:8233)

Keep this terminal running.

---

### Step 4: Start the Temporal Worker
Open **Terminal 2** and launch the worker process:

```powershell
uv run ebay-worker
```

You should see:
```text
Worker listening on task queue: ebay-processing-queue
```
The worker will stay running, polling the task queue for work items and executing activities. Keep this terminal running.

---

### Step 5: Trigger the Workflows
Open **Terminal 3** and run the pipeline trigger script:

```powershell
uv run ebay-run
```

#### What happens during execution:
1. `ebay-run` writes default search keywords (`mechanical keyboard`, `gaming mouse`) to `search_queries.txt`.
2. Triggers `EbaySearchPipelineWorkflow` (`id: ebay-search-run-001`).
   - Searches eBay for each keyword in the specified marketplace and appends unique item IDs to `item_ids.txt`.
3. Triggers `EbayItemEnrichmentWorkflow` (`id: ebay-enrich-run-001`).
   - Fetches full details for each item ID and saves individual JSON files to `./ebay_item_jsons/<item_id>.json`.

---

### Step 6: Monitor & Inspect in Temporal Web UI
1. Visit [http://localhost:8233](http://localhost:8233).
2. Click on namespace `default`.
3. View the execution graph, payload inputs/outputs, activity timing, and retries.

---

## Supported Marketplace IDs (`EBAY_MARKETPLACE_ID`)

You can set `EBAY_MARKETPLACE_ID` in `.env` to search and fetch from any official eBay marketplace:

| Marketplace Code | Country / Site | Default Locale (`EBAY_ACCEPT_LANGUAGE`) |
| :--- | :--- | :--- |
| **`EBAY_US`** | United States (Default) | `en-US` |
| **`EBAY_GB`** | United Kingdom | `en-GB` |
| **`EBAY_DE`** | Germany | `de-DE` |
| **`EBAY_AU`** | Australia | `en-AU` |
| **`EBAY_CA`** | Canada | `en-CA` (or `fr-CA`) |
| **`EBAY_FR`** | France | `fr-FR` |
| **`EBAY_IT`** | Italy | `it-IT` |
| **`EBAY_ES`** | Spain | `es-ES` |
| **`EBAY_AT`** | Austria | `de-AT` |
| **`EBAY_BE`** | Belgium | `nl-BE` (or `fr-BE`) |
| **`EBAY_CH`** | Switzerland | `de-CH` (or `fr-CH`, `it-CH`) |
| **`EBAY_IE`** | Ireland | `en-IE` |
| **`EBAY_IN`** | India | `en-IN` |
| **`EBAY_HK`** | Hong Kong | `zh-HK` |
| **`EBAY_MY`** | Malaysia | `en-MY` (or `ms-MY`) |
| **`EBAY_PH`** | Philippines | `en-PH` |
| **`EBAY_SG`** | Singapore | `en-SG` |
| **`EBAY_PL`** | Poland | `pl-PL` |
| **`EBAY_NL`** | Netherlands | `nl-NL` |
| **`EBAY_MOTORS_US`** | eBay Motors (US) | `en-US` |

---

## Troubleshooting & SSL Options

### Corporate Proxy / Custom CA Certificates
If your environment inspects TLS traffic or uses custom certificates, configure the CA bundle path in `.env`:

```env
EBAY_CA_BUNDLE=C:\path\to\company-ca.pem
```

### Disabling SSL Verification (Development / Debugging Only)
For temporary local testing behind restrictive firewalls:

```powershell
$env:EBAY_VERIFY_SSL = "false"
uv run ebay-worker
```
*(Run in the worker's terminal session)*

> [!WARNING]
> Do not disable SSL verification in production environments.
