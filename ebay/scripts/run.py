"""Submit the eBay pipelines."""

import asyncio
import time
from pathlib import Path

from temporalio.client import Client

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workers', 'extractor')))
import config
from workflows import extractor_workflow


async def _main() -> None:
    """Connects to the Temporal server and triggers the Enrichment and Ingestion workflows."""
    client = await Client.connect(config.TEMPORAL_HOST)
    root = Path.cwd()
    pipeline_config = root / "input_data" / "input_data.yaml"

    run_id_suffix = int(time.time())

    print("\n--- Triggering Workflow 2: Enrichment ---")
    enrich_result = await client.execute_workflow(
        extractor_workflow.EbayItemEnrichmentWorkflow.run,
        args=[str(pipeline_config), str(root / "ebay_item_jsons")],
        id=f"ebay-enrich-run-{run_id_suffix}",
        task_queue=config.TASK_QUEUE,
    )
    print("Enrichment Result:", enrich_result)

    print("\n--- Triggering Workflow 3: Data Ingestion ---")
    ingest_result = await client.execute_workflow(
        extractor_workflow.EbayIngestionWorkflow.run,
        args=[str(pipeline_config), str(root / "ingestion_output.yaml")],
        id=f"ebay-ingest-run-{run_id_suffix}",
        task_queue=config.TASK_QUEUE,
    )
    print("Data Ingestion Result:", ingest_result)


def run_pipeline() -> None:
    """Synchronous wrapper to run the async pipeline execution."""
    asyncio.run(_main())


if __name__ == "__main__":
    run_pipeline()
