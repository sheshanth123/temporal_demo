# eBay Data Ingestion Pipeline (Temporal)

A durable data pipeline built with Temporal to fetch, enrich, and ingest eBay listings into a unified schema.

---

## How It Works

The pipeline is orchestrated by a local Temporal server and executes three main workflows:

1. **Search Pipeline (`EbaySearchPipelineWorkflow`)**: Reads keywords from `search_queries.txt`, authenticates, and queries the eBay Browse API to find unique item IDs, saving them to `item_ids.txt`.
2. **Enrichment Pipeline (`EbayItemEnrichmentWorkflow`)**: Fetches detailed JSON payloads for each item ID and saves them individually to `./ebay_item_jsons/`.
3. **Data Ingestion Pipeline (`EbayIngestionWorkflow`)**: 
   - Loads pipeline parameters from `config.yaml` and synthetic item IDs from `item_ids.txt`.
   - Fetches items concurrently in chunks of 20.
   - Generates deterministic tracking ULIDs (`FETCH_RUN_ID`, `CALL_ID`, `RECORD_ID`) and captures `BATCH_START_TIME` for consistent reads.
   - Outputs the unified, structured payloads into `ingestion_output.yaml`.

---

## Steps to Run

### 1. Install Dependencies
Ensure you have [uv](https://docs.astral.sh/uv/) installed, then run:
```powershell
uv sync
```

### 2. Configure Environment & Parameters
**Create a `.env` file in the root directory:**
```env
EBAY_CLIENT_ID=your-ebay-app-client-id
EBAY_CLIENT_SECRET=your-ebay-cert-client-secret
EBAY_BASE_URL=https://api.sandbox.ebay.com
EBAY_MARKETPLACE_ID=EBAY_US
TEMPORAL_HOST=localhost:7233
TASK_QUEUE=ebay-processing-queue
```

**Ensure your `config.yaml` is set up:**
```yaml
listing_id: "SYNTHETIC_E-GOLD"
source_platform: "EBAY"
mode: "POLL"
page_size: 20
enable_flag: true
```

### 3. Start Temporal Server
In a new terminal, start the local Temporal cluster:
```powershell
temporal server start-dev
```
*(You can view the execution UI at http://localhost:8233)*

### 4. Start the Worker Process
In a separate terminal, launch the worker that listens for tasks:
```powershell
uv run ebay-worker
```

### 5. Trigger the Pipeline
In a third terminal, submit the workflows to the cluster:
```powershell
uv run ebay-run
```
This will automatically execute the workflows, ultimately generating your populated `ingestion_output.yaml` file.
