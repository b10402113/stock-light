"""Script to manually enqueue a batch job to api_queue for testing.

Run with: python scripts/test_enqueue_api_batch.py
"""

import asyncio
from arq import create_pool
from src.tasks.config import redis_settings
from src.clients.redis_client import StockRedisClient
from src.config import settings


async def main():
    """Enqueue a test batch job to api_queue."""
    # Create ARQ pool
    redis_pool = await create_pool(redis_settings)

    # Get active stocks from Redis
    redis_client = StockRedisClient(pool=redis_pool)
    active_stock_ids = await redis_client.get_active_stocks()

    print(f"Found {len(active_stock_ids)} active stocks")

    if not active_stock_ids:
        print("No active stocks to test")
        await redis_pool.close()
        return

    # Take first 5 stocks for testing
    test_batch = active_stock_ids[:5]
    print(f"Test batch: {test_batch}")

    # Enqueue job to api_queue
    job = await redis_pool.enqueue_job(
        "update_stock_prices_batch",
        test_batch,
        _queue_name="api_queue"  # Send to API queue
    )

    print(f"✅ Enqueued job: {job.job_id}")
    print(f"   Queue: api_queue")
    print(f"   Batch size: {len(test_batch)}")

    # Close pool
    await redis_pool.close()


if __name__ == "__main__":
    asyncio.run(main())