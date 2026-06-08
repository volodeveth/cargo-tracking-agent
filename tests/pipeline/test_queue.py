import asyncio
from tracking_agent.pipeline.queue import run_batch


def test_run_batch_preserves_order_and_runs_all():
    async def handler(x):
        await asyncio.sleep(0)
        return x * 2

    out = asyncio.run(run_batch([1, 2, 3], handler, concurrency=2))
    assert out == [2, 4, 6]
