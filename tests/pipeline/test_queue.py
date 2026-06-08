import asyncio
from tracking_agent.pipeline.queue import run_batch


def test_run_batch_preserves_order_and_runs_all():
    async def handler(x):
        await asyncio.sleep(0)
        return x * 2

    out = asyncio.run(run_batch([1, 2, 3], handler, concurrency=2))
    assert out == [2, 4, 6]


def test_run_batch_empty_returns_empty():
    async def handler(x):
        return x

    assert asyncio.run(run_batch([], handler, concurrency=2)) == []


def test_run_batch_respects_concurrency_limit():
    state = {"cur": 0, "peak": 0}

    async def handler(x):
        state["cur"] += 1
        state["peak"] = max(state["peak"], state["cur"])
        await asyncio.sleep(0.02)
        state["cur"] -= 1
        return x

    out = asyncio.run(run_batch(list(range(10)), handler, concurrency=3))
    assert out == list(range(10))
    assert state["peak"] <= 3


def test_run_batch_zero_concurrency_does_not_deadlock():
    async def handler(x):
        return x

    async def go():
        return await asyncio.wait_for(run_batch([1, 2, 3], handler, concurrency=0), timeout=3)

    assert asyncio.run(go()) == [1, 2, 3]
