"""Long-running Temporal worker process."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from ebay import activities, config, workflows


async def _main() -> None:
    client = await Client.connect(config.TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=config.TASK_QUEUE,
        workflows=[workflows.EbaySearchPipelineWorkflow, workflows.EbayItemEnrichmentWorkflow, workflows.EbayIngestionWorkflow],
        activities=activities.ALL_ACTIVITIES,
    )
    print(f"Worker listening on task queue: {config.TASK_QUEUE}")
    await worker.run()


def run_worker() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    run_worker()
