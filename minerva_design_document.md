# Tasks

*   **Scope & Data Contract Documentation:** Create a clear contract detailing in-scope items (polling mode), out-of-scope items (e.g., historical backfill, dynamic sourcing), assumptions, dependencies (e.g., using Sandbox API as a fallback for Production API), and sample input/outputs.
*   **eBay API Ingestion:** Build the data connector to fetch listing data from the eBay API (primarily focusing on polling mode).
*   **Pagination & Batching:** Implement chunking logic to process and query the items in batches of 20.
*   **Decoupled Configuration:** Externalize pipeline configurations (using YAML or DynamoDB) to avoid hardcoding. This includes parameters like source listing IDs, endpoints, priority, page size, mode, schedule, and an enable/disable flag.
*   **Secrets Management:** Integrate with AWS Secrets Manager to securely retrieve eBay API credentials (reference keys) at runtime.
*   **MVCC Timestamps:** Apply consistent read timestamps (BST / FFST) at the start of the job run to ensure a frozen, persisted state for the entire batch.
*   **Hierarchical ID Generation:** Generate and assign sequence IDs to incoming data (running FID, rotating CID and RID) for robust data lineage.
*   **Raw Data Storage:** Write the ingested raw payload records individually into DynamoDB, making them available for downstream compaction and processing (by Pooja).

## Scope and Assumptions

### In Scope
*   **eBay API Polling:** Building the data connector to connect to and fetch listing data from eBay APIs using the standard polling mode.
*   **Secrets Management:** Securely connecting to and managing API credentials via AWS Secrets Manager.
*   **Schema Inference:** Inferring the schema of the incoming JSON payloads to register the version ID.
*   **Sandbox Integration:** Operating on the eBay Sandbox API as a contingency for initial development and testing.

### Out of Scope
*   **Historical Data Backfill:** Fetching historical records (e.g., pulling the last 90 days of data) is deferred to future sprints.
*   **Dynamic Source Listing:** Automatically retrieving dynamic lists from the upstream sourcing engine. (A hardcoded/synthetic configuration will be used temporarily).
*   **Multiple Database Sourcing:** Fetching from multiple distinct source databases at once.
*   **Automated Schema Drift Handling:** While schema changes can be inferred/flagged, automatically reacting to schema drift (e.g., halting the pipeline) is not covered in this sprint.

### Assumptions & Dependencies
*   **Synthetic Data / Hardcoded Lists:** It is assumed that Minerva will use a hardcoded synthetic list of item IDs (stored in YAML or DynamoDB) until the actual sourcing engine is ready to provide live data.
*   **Production API Dependency:** Final production implementation is dependent on receiving access to the eBay Production API; until then, the Sandbox API fulfills the dependency.
*   **Downstream Compaction:** It is assumed that Minerva’s responsibility ends at writing raw JSON records to DynamoDB, which will subsequently be picked up, validated, and compacted into Parquet format by a separate downstream process (Pooja's component).

## Minerva's Output (Downstream Handoff)

This section defines exactly what data Minerva produces and hands off to other components in the pipeline.

### 1. Output to Pooja (Compaction & Validation)
Minerva is responsible for fetching and writing raw, individual records directly to DynamoDB. Pooja's downstream process will then pick these up to validate and compact them into Parquet files.
*   **Delivery Mechanism:** Individual uncompacted records persisted directly into DynamoDB.
*   **Data Structure Provided:** The data contract columns up to the "mode" column, plus the actual data payload. (The last three specific metadata columns are excluded from Pooja's feed).
*   **Key Fields Included:**
    *   **Hierarchical IDs (`FID`, `CID`, `RID`):** Sequence and chunk tracking IDs to identify exactly which fetch run and batch the record belongs to.
    *   **MVCC Timestamp (`BST` / `FFST`):** The consistent read timestamp indicating the exact time the batch/fetch job was started.
    *   **Schema Version ID:** The registry ID pointing to the inferred schema of the payload.
    *   **Variant Column:** The column containing the actual fetched JSON payload data from the eBay API.

### 2. Output to Hemant (Orchestration & Metadata)
*   **Data Structure Provided:** Hemant receives the *entire* complete metadata structure, which includes all columns (specifically the last three metadata columns that are excluded from Pooja's input).

## Validation Evidence (Transcript Traceability)

The following tables trace every requirement back to the meeting transcript to confirm its assignment to Minerva.

### 1. Minerva's Output (Downstream Handoff)

| Point in Document | Assigned to Minerva? | Evidence (As-is from Transcript) |
| :--- | :---: | :--- |
| **Delivery Mechanism (Pooja):** Individual uncompacted records persisted directly into DynamoDB. | **Yes** | *"Minerva is writing one by one in DynamoDB. Pooja picks this up... They will take it, compact it and write it back."* (Line 45) |
| **Data Structure (Pooja):** Data contract columns up to the "mode" column (excluding the last three). | **Yes** | *"So what exactly I need to provide to Pooja, the first ah other than the last three all all of them. Till mode, till mode."* (Line 25) |
| **Key Fields: FID, CID, RID:** Sequence and chunk tracking IDs. | **Yes** | *"So when they come back, there you will have a serial number... FID, CID, RID can be four digits... FID alone will be a running sequence. RID, CID, and RID can be a rotating sequence."* (Line 3) |
| **Key Fields: MVCC Timestamp (BST/FFST):** Timestamp for when the batch/fetch job started. | **Yes** | *"that will be the timestamp that will assign... this BST batch standard time will have the batch 20 records... F is for the entire fetch run, what is the time."* (Lines 7-9) |
| **Key Fields: Schema Version ID:** Registry ID pointing to the inferred schema. | **Yes** | *"Version something where once the schema is inferred, there is a registry of schema... that version ID should be put here... That JSON's ID is coming as version ID."* (Lines 23, 99) |
| **Key Fields: Variant Column:** Column containing the actual JSON payload data. | **Yes** | *"In this there is no variant column. Variant column should also be added. Variant column is your data man."* (Lines 89-91) |
| **Output to Hemant:** Hemant receives the entire complete metadata structure (including the last three columns). | **Yes** | *"This is what Hemant gets. This is not what Minerva gives to Pooja. Ah the last three right? Last three columns. Everything, this entire structure is what Hemant gets."* (Line 23) |

### 2. Tasks

| Point in Document | Assigned to Minerva? | Evidence (As-is from Transcript) |
| :--- | :---: | :--- |
| **Scope & Data Contract Documentation:** Document in-scope/out-of-scope items, assumptions, dependencies. | **Yes** | *"Minerva will create Minerva's input and output... What will be in the document? You will say what will you do? What will you not do?... What is your dependency?"* (Lines 61, 69-71) |
| **eBay API Ingestion:** Fetch listing data from the eBay API (polling mode). | **Yes** | *"Minerva is getting the data from eBay sources... Polling alone will be..."* (Line 67, 71) |
| **Pagination & Batching:** Implement chunking logic in batches of 20. | **Yes** | *"we will get multiple records in one call... you have a list, in that list there will be 20 batches. Each batch will have 20 items... you will send 20 in one call."* (Lines 1-3) |
| **Decoupled Configuration:** Externalize configurations (YAML/DynamoDB) for parameters. | **Yes** | *"Don't hardcode it, you will put it in a YAML... keep it in DynamoDB anywhere... this is Minerva's configuration. You just man it..."* (Lines 17, 55) |
| **Secrets Management:** Securely retrieve credentials via AWS Secrets Manager at runtime. | **Yes** | *"A credential reference point to secret. AWS secret... Minerva you you write the credentials hardcoded into the data connector... Remove all that and give..."* (Lines 39-45) |
| **MVCC Timestamps:** Consistent read timestamps at the start of the job. | **Yes** | *"when Minerva started the work, first read from the list... that will be the timestamp that will assign..."* (Lines 7-9) |
| **Hierarchical ID Generation:** Generate sequence IDs to incoming data. | **Yes** | *"FID, CID, RID can be four digits... FID alone will be a running sequence. RID, CID, and RID can be a rotating sequence."* (Line 3) |
| **Raw Data Storage:** Write raw records to DynamoDB. | **Yes** | *"Minerva is writing one by one in DynamoDB. Pooja picks this up... "* (Line 45) |

### 3. Scope and Assumptions

| Point in Document | Assigned to Minerva? | Evidence (As-is from Transcript) |
| :--- | :---: | :--- |
| **In Scope: eBay API Polling / Sandbox** | **Yes** | *"Polling alone will be you you are not doing historical data."* (Line 71) <br> *"You will tell like for me to do the job right now I am using the sandbox API."* (Line 71) |
| **In Scope: Secrets / Schema Inference** | **Yes** | *"ability to connect manage secrets hmm."* (Line 71)<br> *"Version something where once the schema is inferred..."* (Line 23) |
| **Out of Scope: Historical Data Backfill** | **Yes** | *"Polling alone will be you you are not doing historical data."* (Line 71) |
| **Out of Scope: Dynamic Source Listing** | **Yes** | *"You are not going to have a dynamic list source listing."* (Line 69) <br> *"Minerva's list is synthetic data by the way. That hardcoded list right?"* (Line 79) |
| **Out of Scope: Multiple Database Sourcing** | **Yes** | *"You are not going to implement the sourcing multiple database."* (Line 69) |
| **Out of Scope: Automated Schema Drift Handling** | **Yes** | *"schema drift handling whereby when you say schema drift handling it is turning off the pipeline isn't it? That work you are not doing..."* (Lines 75-77) |
| **Assumption: Synthetic Data / Hardcoded List** | **Yes** | *"Minerva's list is synthetic data by the way. That hardcoded list right? That that is synthetic data."* (Line 79) |
| **Dependency: Production API Dependency** | **Yes** | *"I have a dependency on the production API... If dependency is not met, you will operate on contingency. You will do it on sandbox."* (Line 71) |
| **Dependency: Downstream Compaction** | **Yes** | *"Minerva is writing one by one in DynamoDB. Pooja picks this up... They will take it, compact it and write it back."* (Line 45) |
