"""Submit the eBay search and enrichment workflows."""

import asyncio
import time
from pathlib import Path

from temporalio.client import Client

from ebay import config, workflows


async def _main() -> None:
    client = await Client.connect(config.TEMPORAL_HOST)
    root = Path.cwd()
    queries_path = root / "search_queries.txt"
    items_path = root / "item_ids.txt"
    queries_path.write_text("pokemon cards", encoding="utf-8")

    run_id_suffix = int(time.time())
    print("\n--- Triggering Workflow 1: Search ---")
    search_result = await client.execute_workflow(
        workflows.EbaySearchPipelineWorkflow.run,
        args=[str(queries_path), str(items_path)],
        id=f"ebay-search-run-{run_id_suffix}",
        task_queue=config.TASK_QUEUE,
    )
    print("Search Result:", search_result)

    print("\n--- Triggering Workflow 2: Enrichment ---")
    enrich_result = await client.execute_workflow(
        workflows.EbayItemEnrichmentWorkflow.run,
        args=[str(items_path), str(root / "ebay_item_jsons")],
        id=f"ebay-enrich-run-{run_id_suffix}",
        task_queue=config.TASK_QUEUE,
    )
    print("Enrichment Result:", enrich_result)



def run_pipeline() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run_pipeline()
