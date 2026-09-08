"""Durable Temporal workflows for the eBay pipelines."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ebay_client.activities import append_items_to_file_activity, fetch_item_details_activity, fetch_oauth_token_activity, read_lines_from_file_activity, save_item_json_activity, search_ebay_activity

RETRY_POLICY = RetryPolicy(initial_interval=timedelta(seconds=2), backoff_coefficient=2.0, maximum_interval=timedelta(seconds=30), maximum_attempts=4)


@workflow.defn
class EbaySearchPipelineWorkflow:
    @workflow.run
    async def run(self, input_queries_file: str, output_items_file: str) -> dict:
        queries = await workflow.execute_activity(read_lines_from_file_activity, input_queries_file, start_to_close_timeout=timedelta(seconds=10))
        if not queries:
            return {"status": "skipped", "reason": "No queries found in file"}
        token = await workflow.execute_activity(fetch_oauth_token_activity, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY)
        item_ids = []
        for query in queries:
            item_ids.extend(await workflow.execute_activity(search_ebay_activity, {"token": token, "query": query, "limit": 3}, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY))
        count = await workflow.execute_activity(append_items_to_file_activity, {"file_path": output_items_file, "item_ids": item_ids}, start_to_close_timeout=timedelta(seconds=10))
        return {"status": "completed", "queries_processed": len(queries), "new_items_saved": count, "target_file": output_items_file}


@workflow.defn
class EbayItemEnrichmentWorkflow:
    @workflow.run
    async def run(self, input_items_file: str, output_dir: str = "./ebay_items") -> dict:
        item_ids = await workflow.execute_activity(read_lines_from_file_activity, input_items_file, start_to_close_timeout=timedelta(seconds=10))
        if not item_ids:
            return {"status": "skipped", "reason": "No item IDs to process"}
        token = await workflow.execute_activity(fetch_oauth_token_activity, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY)
        saved_paths = []
        for item_id in item_ids:
            data = await workflow.execute_activity(fetch_item_details_activity, {"token": token, "item_id": item_id}, start_to_close_timeout=timedelta(seconds=30), retry_policy=RETRY_POLICY)
            saved_paths.append(await workflow.execute_activity(save_item_json_activity, {"item_id": item_id, "data": data, "output_dir": output_dir}, start_to_close_timeout=timedelta(seconds=10)))
        return {"status": "completed", "items_processed": len(saved_paths), "output_dir": output_dir}
