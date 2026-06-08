from ..models.enums import NormalizedStatus as S

_UK = {
    S.NOT_FOUND: "Не знайдено",
    S.CREATED: "Створено",
    S.BOOKED: "Заброньовано",
    S.RECEIVED: "Прийнято",
    S.IN_ORIGIN_TERMINAL: "У терміналі відправлення",
    S.DEPARTED: "Відправлено",
    S.IN_TRANSIT: "У дорозі",
    S.ARRIVED: "Прибув",
    S.CUSTOMS: "Митне оформлення",
    S.READY_FOR_PICKUP: "Готовий до видачі",
    S.DELIVERED: "Доставлено",
    S.CONTAINER_PICKED_UP: "Контейнер забрано",
    S.CONTAINER_RETURNED: "Контейнер повернуто",
    S.EXCEPTION: "Виняткова ситуація",
    S.UNKNOWN: "Невідомо",
}


def to_ukrainian(status: S) -> str:
    return _UK.get(status, "Невідомо")
