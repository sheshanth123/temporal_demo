"""Long-running Temporal worker process."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

import config
from workflows import extractor_workflow
from workflows.activities import fetch_listings


async def _main() -> None:
    """Connects to the Temporal server and registers the worker with workflows and activities."""
    client = await Client.connect(config.TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=config.TASK_QUEUE,
        workflows=[extractor_workflow.EbayItemEnrichmentWorkflow, extractor_workflow.EbayIngestionWorkflow],
        activities=fetch_listings.ALL_ACTIVITIES,
    )
    print(f"Worker listening on task queue: {config.TASK_QUEUE}")
    await worker.run()


def run_worker() -> None:
    """Synchronous wrapper to start the Temporal worker daemon."""
    asyncio.run(_main())


if __name__ == "__main__":
    run_worker()
