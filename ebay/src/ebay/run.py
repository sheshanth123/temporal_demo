"""Submit the eBay search and enrichment workflows."""

import asyncio
import time
from pathlib import Path

from temporalio.client import Client

from ebay import config, workflows


async def _main() -> None:
    client = await Client.connect(config.TEMPORAL_HOST)
    root = Path.cwd()
    items_path = root / "item_ids.txt"

    run_id_suffix = int(time.time())

    print("\n--- Triggering Workflow 2: Enrichment ---")
    enrich_result = await client.execute_workflow(
        workflows.EbayItemEnrichmentWorkflow.run,
        args=[str(items_path), str(root / "ebay_item_jsons")],
        id=f"ebay-enrich-run-{run_id_suffix}",
        task_queue=config.TASK_QUEUE,
    )
    print("Enrichment Result:", enrich_result)

    print("\n--- Triggering Workflow 3: Minerva Ingestion ---")
    minerva_result = await client.execute_workflow(
        workflows.MinervaIngestionWorkflow.run,
        args=[str(root / "config.yaml"), str(items_path), str(root / "minerva_output.yaml")],
        id=f"minerva-ingest-run-{run_id_suffix}",
    print("\n--- Triggering Workflow 3: Data Ingestion ---")
    ingest_result = await client.execute_workflow(
        workflows.EbayIngestionWorkflow.run,
        args=[str(root / "config.yaml"), str(items_path), str(root / "ingestion_output.yaml")],
        id=f"ebay-ingest-run-{run_id_suffix}",
        task_queue=config.TASK_QUEUE,
    )
    print("Minerva Ingestion Result:", minerva_result)
    print("Data Ingestion Result:", ingest_result)



def run_pipeline() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run_pipeline()
