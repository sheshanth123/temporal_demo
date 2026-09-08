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
- **eBay Developer Account**: An App ID (Client ID) and Cert ID (Client Secret) from the [eBay Developer Portal](https://developer.ebay.com/).

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
Create a `.env` file in the project root directory (or edit the existing one):

```env
EBAY_CLIENT_ID=your-ebay-app-client-id
EBAY_CLIENT_SECRET=your-ebay-cert-client-secret
EBAY_BASE_URL=https://api.sandbox.ebay.com
TEMPORAL_HOST=localhost:7233
TEMPORAL_UI_URL=http://localhost:8233
TASK_QUEUE=ebay-processing-queue
```

> [!NOTE]
> - By default, `EBAY_BASE_URL` uses `https://api.sandbox.ebay.com`. If you have production keys, change it to `https://api.ebay.com`.
> - Never commit your `.env` file to source control.

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
- **Temporal Web UI**: [http://localhost:8233](http://localhost:8233) (Open this in your browser to inspect workflows in real time!)

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
   - The worker executes the activities, searches eBay, and creates `item_ids.txt`.
   - Output summary printed to the console:
     ```text
     Search Result: {'status': 'completed', 'queries_processed': 2, 'new_items_saved': 6, 'target_file': '...\\item_ids.txt'}
     ```
3. Triggers `EbayItemEnrichmentWorkflow` (`id: ebay-enrich-run-001`).
   - The worker reads `item_ids.txt`, queries eBay item endpoints, and saves each item's payload to `ebay_item_jsons/<item_id>.json`.
   - Output summary printed to the console:
     ```text
     Enrichment Result: {'status': 'completed', 'items_processed': 6, 'output_dir': '...\\ebay_item_jsons'}
     ```

---

### Step 6: Monitor & Inspect in Temporal Web UI
1. Visit [http://localhost:8233](http://localhost:8233).
2. Click on namespace `default`.
3. You will see both workflow runs:
   - `ebay-search-run-001`
   - `ebay-enrich-run-001`
4. Click on any workflow run to inspect:
   - Visual timeline and execution graph.
   - Input arguments and return values.
   - Activity execution attempts, inputs, outputs, and any retry/error stacks.

---

## Customizing Queries and Inputs

- **Custom Search Terms**: Modify or populate `search_queries.txt` with one search query per line before running.
- **Custom Workflow IDs**: If you run `uv run ebay-run` multiple times, note that Temporal workflow IDs must be unique for concurrent runs or configured with specific reuse policies. In `src/ebay/run.py`, you can change or parameterize the IDs (e.g., appending a timestamp).

---

## Troubleshooting & SSL Options

### Corporate Proxy / Custom CA Certificates
If your environment inspects TLS traffic or uses custom certificates, configure the CA bundle path in `.env`:

```env
EBAY_CA_BUNDLE=C:\path\to\company-ca.pem
```

### Disabling SSL Verification (Development / Debugging Only)
For temporary local testing behind restrictive firewalls, you can temporarily disable verification:

```powershell
$env:EBAY_VERIFY_SSL = "false"
uv run ebay-worker
```
*(Run in the worker's terminal session)*

> [!WARNING]
> Do not disable SSL verification in production environments.
