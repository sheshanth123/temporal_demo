"""Durable Temporal workflows for the eBay pipelines."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities.fetch_listings import (
        fetch_item_details_activity, 
        fetch_oauth_token_activity, 
        read_lines_from_file_activity, 
        save_item_json_activity, 
        read_yaml_config_activity,
        fetch_item_batch_activity,
        save_batch_yaml_activity
    )
    import ulid

RETRY_POLICY = RetryPolicy(initial_interval=timedelta(seconds=2), backoff_coefficient=2.0, maximum_interval=timedelta(seconds=30), maximum_attempts=4)


@workflow.defn
class EbayItemEnrichmentWorkflow:
    """Workflow to fetch details for a list of items and save them individually to disk."""

    @workflow.run
    async def run(self, input_items_file: str, output_dir: str = "./ebay_items") -> dict:
        """Executes the enrichment pipeline by reading item IDs, fetching details, and writing JSON files."""
        item_ids = await workflow.execute_activity(read_lines_from_file_activity, input_items_file, start_to_close_timeout=timedelta(seconds=10))
        if not item_ids:
            return {"status": "skipped", "reason": "No item IDs to process"}
        token = await workflow.execute_activity(fetch_oauth_token_activity, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY)
        saved_paths = []
        for item_id in item_ids:
            data = await workflow.execute_activity(fetch_item_details_activity, {"token": token, "item_id": item_id}, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY)
            saved_paths.append(await workflow.execute_activity(save_item_json_activity, {"item_id": item_id, "data": data, "output_dir": output_dir}, start_to_close_timeout=timedelta(seconds=10)))
        return {"status": "completed", "items_processed": len(saved_paths), "output_dir": output_dir}


@workflow.defn
class EbayIngestionWorkflow:
    """Workflow to batch fetch eBay items and save them in a highly structured YAML format."""

    @workflow.run
    async def run(self, config_file: str, input_items_file: str, output_file: str) -> dict:
        """Executes the ingestion pipeline: reads config, fetches batches of items, normalizes records, and appends to YAML."""
        # 1. Read config
        config = await workflow.execute_activity(
            read_yaml_config_activity, config_file,
            start_to_close_timeout=timedelta(seconds=10)
        )

        if not config.get("enable_flag", True):
            return {"status": "skipped", "reason": "Pipeline is disabled in config."}

        # 2. Read Item IDs
        item_ids = await workflow.execute_activity(
            read_lines_from_file_activity, input_items_file,
            start_to_close_timeout=timedelta(seconds=10)
        )

        if not item_ids:
            return {"status": "skipped", "reason": "No item IDs to process."}

        # 3. Setup Context
        fetch_run_id = str(ulid.new())
        batch_start_time = workflow.now().isoformat()

        # 4. Fetch OAuth Token
        token = await workflow.execute_activity(
            fetch_oauth_token_activity,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY_POLICY
        )

        # 5. Chunking & Fetching
        page_size = config.get("page_size", 20)
        total_saved = 0

        for i in range(0, len(item_ids), page_size):
            chunk = item_ids[i:i + page_size]
            call_id = str(ulid.new())

            # Fetch batch from eBay
            batch_response = await workflow.execute_activity(
                fetch_item_batch_activity,
                {"token": token, "item_ids": chunk},
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RETRY_POLICY
            )

            items = batch_response.get("items", [])
            # Fallback
            if not items:
                items = batch_response.get("itemSummaries", [])
            if not items:
                continue

            # Prepare records matching schema
            records_to_save = []
            for item in items:
                record = {
                    "RECORD_ID": str(ulid.new()),
                    "CALL_ID": call_id,
                    "FETCH_RUN_ID": fetch_run_id,
                    "BATCH_START_TIME": batch_start_time,
                    "SOURCE_PLATFORM": config.get("source_platform", "EBAY"),
                    "LIST_ID": config.get("listing_id", "UNKNOWN"),
                    "MODE": config.get("mode", "POLL"),
                    "PAYLOAD": item
                }
                records_to_save.append(record)

            # Append to YAML
            if records_to_save:
                await workflow.execute_activity(
                    save_batch_yaml_activity,
                    {
                        "output_file": output_file,
                        "records": records_to_save
                    },
                    start_to_close_timeout=timedelta(seconds=10)
                )
                total_saved += len(records_to_save)

        return {
            "status": "completed",
            "fetch_run_id": fetch_run_id,
            "total_items_processed": total_saved,
            "output_file": output_file
        }
