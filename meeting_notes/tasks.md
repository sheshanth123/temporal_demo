Here is a step-by-step implementation guide for building the data pipeline, detailing the required processes and data structures at each stage.

### Phase 1: Define Data Contracts and Scope
Before writing any code, each team member (Minerva, Pooja, Hemant) must create a detailed Markdown document defining their specific inputs and outputs.
*   **Document Structure:** Clearly outline what is **in scope, out of scope, dependencies, and assumptions**.
*   **Minerva's Scope:** Focus on connecting to sources and polling data. Explicitly state that historical data retrieval is out of scope and that you are depending on the Sandbox API for now.
*   **Pooja's Scope:** Focus on compaction, inferring schemas, and flagging schema drifts. Note that actually *handling* schema drift (e.g., stopping the pipeline) is out of scope for the current sprint.
*   **AI Code Generation:** These detailed documents, along with sample inputs and outputs, should be fed into Claude to help generate the initial code and folder structures.

### Phase 2: Orchestration and Configuration (Minerva Setup)
The pipeline relies on **Temporal** as the orchestrator to read metadata and trigger jobs. Instead of hardcoding configurations, store them in a **YAML file or DynamoDB** to allow for CI/CD updates and to meet Non-Functional Requirements (NFRs).
*   **Required Configuration Data:**
    *   **Sourcing List ID & Platform Name:** Identifies the target platform and list (e.g., "auction listing for baseball cards").
    *   **Endpoint / Data Connector:** Specifies which connector to use.
    *   **Priority:** Matches Temporal's prioritization settings to determine execution order.
    *   **Mode:** Defines behavior through feature flags and run parameters (e.g., polling vs. backfilling, backfill windows of 15 to 90 days, and a standard page size of 20).
    *   **Enable Flag:** An active status flag (Yes/No) to quickly turn ad-hoc jobs on or off without deploying code.
    *   **Credential References:** Pointers to AWS Secrets so API keys are securely referenced rather than hardcoded.

### Phase 3: Data Ingestion and Timestamping (Minerva Execution)
When Temporal triggers the job, Minerva fetches item IDs sequentially or in parallel, making API calls in **batches of 20 items**. 
*   **Synthetic Data:** For Sprint Zero, use synthetic data to unblock development while waiting for live production data to become available. 
*   **Timestamping Data (Consistent Get):** Apply a **single, consistent timestamp** to all records in a batch, reflecting the exact moment the process started. For example, if a job runs hourly, all 20 records in that batch share the same truncated hourly timestamp, acting as a historical system state pointer.
*   **Ingestion Output Data:** 
    *   **FID:** A running sequence ID.
    *   **CID & RID:** Rotating sequence IDs (hexadecimal or 4-digit).

### Phase 4: Data Compaction and Parquet Generation (Pooja Execution)
Once Minerva writes individual records to DynamoDB, Pooja's process must pick them up, validate them, and compact them into larger files.
*   **File Creation:** Convert the records into **250 MB Parquet files**.
*   **Storage Routing:** Send the processed files to two locations: an **S3 discard zone** and **S3 bronze staging**.
*   **Compaction Log Data:** Create a `Process Run ID` (or `Compaction Run ID`) log that tracks the lifecycle of the compaction. This log must include the source count, discarded record count, validations performed, high/low watermarks, and final process status. This log should be embedded as a header in the Parquet files or written to the database.

### Phase 5: Output Schema Validation
Ensure the final output schema is properly mapped and stripped of redundancies.
*   **Additions:** Include a **Variant column** for specific data traits, and a **Schema Version ID** that acts as a pointer to the Kafka or Data Catalog Schema Registry where the inferred schema characteristics are stored. 
*   **Removals:** Remove redundant columns like `Record ID` (since `RID` exists) and `Record Type` (since it is captured by the Version ID).