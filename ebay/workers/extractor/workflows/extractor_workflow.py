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
    async def run(self, pipeline_config_file: str, output_dir: str = "./ebay_items") -> dict:
        """Executes the enrichment pipeline by reading item IDs from pipeline config, fetching details, and writing JSON files."""
        config_data = await workflow.execute_activity(
            read_yaml_config_activity, pipeline_config_file,
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        listings = config_data.get("listings", [])
        active_listings = [
            lst for lst in listings 
            if lst.get("enable") is True and str(lst.get("source_platform")).lower() == "ebay"
        ]
        item_ids = [lst.get("listing_id") for lst in active_listings if lst.get("listing_id")]

        if not item_ids:
            return {"status": "skipped", "reason": "No active item IDs to process"}
            
        token = await workflow.execute_activity(fetch_oauth_token_activity, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY)
        
        page_size = active_listings[0].get("page_size", 20) if active_listings else 20
        saved_paths = []
        
        for i in range(0, len(item_ids), page_size):
            chunk = item_ids[i:i + page_size]
            batch_response = await workflow.execute_activity(
                fetch_item_batch_activity,
                {"token": token, "item_ids": chunk},
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RETRY_POLICY
            )
            
            items = batch_response.get("items", [])
            if not items:
                items = batch_response.get("itemSummaries", [])
                
            for item in items:
                item_id = item.get("itemId")
                if item_id:
                    path = await workflow.execute_activity(
                        save_item_json_activity, 
                        {"item_id": item_id, "data": item, "output_dir": output_dir}, 
                        start_to_close_timeout=timedelta(seconds=10)
                    )
                    saved_paths.append(path)
                    
        return {"status": "completed", "items_processed": len(saved_paths), "output_dir": output_dir}


@workflow.defn
class EbayIngestionWorkflow:
    """Workflow to batch fetch eBay items and save them in a highly structured YAML format."""

    @workflow.run
    async def run(self, pipeline_config_file: str, output_file: str) -> dict:
        """Executes the ingestion pipeline: reads config, fetches batches of items, normalizes records, and appends to YAML."""
        # 1. Read Pipeline Config
        config_data = await workflow.execute_activity(
            read_yaml_config_activity, pipeline_config_file,
            start_to_close_timeout=timedelta(seconds=10)
        )

        listings = config_data.get("listings", [])
        
        # 2. Filter Active Listings
        active_ebay_listings = [
            lst for lst in listings 
            if lst.get("enable") is True and str(lst.get("source_platform")).lower() == "ebay"
        ]

        if not active_ebay_listings:
            return {"status": "skipped", "reason": "No active eBay listings found in config."}

        # Build map for easy lookup by ID
        listing_map = {lst["listing_id"]: lst for lst in active_ebay_listings if "listing_id" in lst}
        item_ids = list(listing_map.keys())

        # 3. Setup Context
        fetch_run_id = str(ulid.new())
        batch_start_time = workflow.now().isoformat()
        
        # We will use the page_size from the first listing as our batching size, default to 20
        page_size = active_ebay_listings[0].get("page_size", 20)

        # 4. Fetch OAuth Token
        token = await workflow.execute_activity(
            fetch_oauth_token_activity,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RETRY_POLICY
        )

        # 5. Chunking & Fetching
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
            if not items:
                items = batch_response.get("itemSummaries", [])
            if not items:
                continue

            # Prepare records matching schema
            records_to_save = []
            for item in items:
                fetched_item_id = item.get("itemId")
                # Look up the original listing config for this item
                item_config = listing_map.get(fetched_item_id, {})
                
                record = {
                    "RECORD_ID": str(ulid.new()),
                    "CALL_ID": call_id,
                    "FETCH_RUN_ID": fetch_run_id,
                    "BATCH_START_TIME": batch_start_time,
                    "SOURCE_PLATFORM": str(item_config.get("source_platform", "EBAY")).upper(),
                    "LIST_ID": item_config.get("listing_id", fetched_item_id),
                    "LIST_NAME": item_config.get("listing_name", "UNKNOWN"),
                    "MODE": str(item_config.get("mode", "POLLING")).upper(),
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
