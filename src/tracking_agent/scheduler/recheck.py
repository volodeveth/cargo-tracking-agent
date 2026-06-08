from __future__ import annotations
from ..pipeline.orchestrator import process_shipment
from ..storage.history import History
from ..webhook.notifier import notify_status_change
from ..config import get_settings
from ..models.schemas import ShipmentInput


async def recheck_numbers(items: list[tuple[str, str]], db_path: str | None = None):
    settings = get_settings()
    history = History(db_path or settings.db_path)
    changes = []
    for sid, number in items:
        res = await process_shipment(ShipmentInput(id=sid, number=number))
        status = res.tracking.current_status.value if res.tracking and res.tracking.current_status else "unknown"
        old = history.last_status(number)
        if history.record(number, status):
            change = {"id": sid, "number": number, "old": old, "new": status}
            changes.append(change)
            await notify_status_change(settings.webhook_url, settings.webhook_secret, change)
    return changes


from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: E402

_scheduler: AsyncIOScheduler | None = None


def start_scheduler(items_provider):
    global _scheduler
    settings = get_settings()
    if not settings.recheck_enabled:
        return None
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(lambda: recheck_numbers(items_provider()),
                       "interval", minutes=settings.recheck_interval_minutes)
    _scheduler.start()
    return _scheduler
