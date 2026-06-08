from __future__ import annotations
import asyncio
from typing import Awaitable, Callable, TypeVar
from ..config import get_settings

T = TypeVar("T")
R = TypeVar("R")


async def run_batch(items: list[T], handler: Callable[[T], Awaitable[R]],
                    concurrency: int | None = None) -> list[R]:
    if concurrency is None:
        concurrency = get_settings().max_concurrency
    sem = asyncio.Semaphore(concurrency)
    results: list[R] = [None] * len(items)  # type: ignore

    async def worker(idx: int, item: T):
        async with sem:
            results[idx] = await handler(item)

    await asyncio.gather(*(worker(i, it) for i, it in enumerate(items)))
    return results
