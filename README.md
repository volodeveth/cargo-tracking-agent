# Cargo Tracking Agent

Сервіс на Python, який приймає список номерів AWB та морських контейнерів, автоматично визначає тип кожного номера, отримує актуальний статус відстеження з доступних онлайн-джерел і повертає уніфікований, стабільний за схемою JSON з подіями, ETA/ETD, поточним статусом, джерелом даних, метриками якості та помилками для кожного номера.

---

## Зміст

1. [Огляд](#огляд)
2. [Архітектура](#архітектура)
3. [Як це працює](#як-це-працює)
4. [Локальний запуск](#локальний-запуск)
5. [Запуск через Docker](#запуск-через-docker)
6. [Вхідні формати](#вхідні-формати)
7. [Формат відповіді](#формат-відповіді)
8. [Підтримувані джерела](#підтримувані-джерела)
9. [Довідник статусів](#довідник-статусів)
10. [Коди помилок](#коди-помилок)
11. [Якість і ризик](#якість-і-ризик)
12. [Опційні можливості](#опційні-можливості)
13. [Як додати новий конектор](#як-додати-новий-конектор)
14. [Обмеження та відомі проблеми](#обмеження-та-відомі-проблеми)
15. [Відповідність критеріям приймання](#відповідність-критеріям-приймання)
16. [Додаткові завдання](#додаткові-завдання)

---

## Огляд

Cargo Tracking Agent обробляє пакет ідентифікаторів вантажів за один запит:

- Номери **AWB (Air Waybill)** у форматі `NNN-NNNNNNNN` (наприклад, `080-38652331`)
- Номери **морських контейнерів** у форматі ISO 6346 `AAAA NNNNNNN` (наприклад, `TLLU4912250`)

Кожен номер обробляється незалежно — збій по одному ніколи не блокує решту. На виході — стабільний за схемою JSON, структура якого однакова незалежно від джерела чи стану помилки, що робить його безпечним для подальшої інтеграції.

---

## Архітектура

```
API / CLI / Web UI
      │
Input Parser ──► Number Type Detector ──► Source Router
      │                                        │
      │                          ┌─────────────┴──────────────┐
      │                          ▼                            ▼
      │                  Source Connectors (Protocol)   (fallback chain)
      │                   ├ TrackTraceAirConnector
      │                   ├ TrackTraceContainerConnector
      │                   ├ CarrierWebsiteConnector
      │                   ├ CargoAiConnector (optional, API)
      │                   └ FixtureConnector (demo/tests)
      │                          │
      ▼                          ▼
   Parser  ◄──────────  Raw Response (HTML/JSON)
      │
Status Normalizer (deterministic dict + optional LLM fallback)
      │
Quality Scorer ──► JSON Response Builder ──► Output (full + short)
      │
Logger / Debug Artifacts (per-number step log)
```

### Відповідальність модулів

| Модуль | Відповідальність |
|---|---|
| `config.py` | Pydantic-settings; усе налаштування через env-змінні |
| `models/enums.py` | Енуми `NumberType`, `NormalizedStatus`, `ErrorCode`, `RiskLevel` |
| `models/schemas.py` | Моделі запиту/відповіді Pydantic v2 |
| `detection/detector.py` | `detect_type()`, `normalize_number()`, контрольна цифра ISO 6346 |
| `detection/awb_prefixes.py` | Таблиця відповідності AWB-префікса перевізнику |
| `connectors/base.py` | Protocol `Connector` + dataclass `ConnectorResult` |
| `connectors/registry.py` | Іменовані екземпляри конекторів |
| `connectors/track_trace_air.py` | Live-скрапер Playwright для авіавантажів track-trace.com |
| `connectors/track_trace_container.py` | Live-скрапер Playwright для контейнерів track-trace.com |
| `connectors/carrier_website.py` | Загальний fallback-конектор сайту перевізника |
| `connectors/cargoai.py` | Опційний конектор REST API CargoAI |
| `connectors/fixture.py` | Парсить збережені HTML-фікстури (працює без інтернету) |
| `parsers/track_trace_parser.py` | BeautifulSoup HTML → `ParsedTracking` |
| `parsers/dates.py` | Сирі рядки дати → ISO 8601 `DateInfo` |
| `normalization/normalizer.py` | `raw_status` → `NormalizedStatus` (детерміновані таблиці правил) |
| `normalization/rules_air.py` | Відповідність ключових слів авіавантажів статусам |
| `normalization/rules_container.py` | Відповідність ключових слів контейнерів статусам |
| `normalization/translate_uk.py` | `NormalizedStatus` → український рядок (статичний словник) |
| `quality/scorer.py` | Оцінка впевненості, `data_complete`, `missing_fields`, попередження |
| `quality/risk.py` | `risk_level`, `delay_detected`, причини |
| `llm/assistant.py` | Опційний OpenAI-сумісний LLM; детермінований fallback коли вимкнено |
| `storage/db.py` | Схема SQLite |
| `storage/cache.py` | Кеш результатів з TTL |
| `storage/history.py` | Історія статусів + порівняння під час ре-чеку |
| `pipeline/orchestrator.py` | Наскрізна обробка одного вантажу |
| `pipeline/router.py` | Побудова впорядкованого ланцюга конекторів за типом номера |
| `pipeline/queue.py` | Пул воркерів з обмеженням через `asyncio.Queue` |
| `pipeline/builder.py` | Складання `TrackingResponse` / `ShortResult` |
| `scheduler/recheck.py` | Завдання APScheduler для повторного трекінгу недоставлених вантажів |
| `webhook/notifier.py` | POST при зміні статусу з HMAC-підписом |
| `export/excel.py` | Експорт у Excel через openpyxl |
| `export/sheets.py` | Опційний експорт у Google Sheets |
| `api/app.py` | Збірка застосунку FastAPI |
| `api/routes.py` | `POST /track`, `POST /track/file`, `GET /results`, `GET /export` |
| `api/web.py` | Web UI завантаження файлу (HTML-сторінка) |
| `cli.py` | CLI-вхід: читання JSON/CSV → запис JSON |

---

## Як це працює

1. **Парсинг входу** — JSON або CSV зчитується в об'єкти `ShipmentInput`.
2. **Визначення типу** — `detect_type()` застосовує regex-патерни:
   - `^\d{3}-?\d{8}$` → `air_awb`
   - `^[A-Z]{4}\d{7}$` → `sea_container`
   - усе інше → `unknown` + помилка `INVALID_FORMAT`
3. **Маршрутизація джерел** — `router.py` будує впорядкований ланцюг конекторів для визначеного типу:
   - Авіа AWB: `TrackTraceAirConnector` → `CarrierWebsiteConnector` → `CargoAiConnector` → `FixtureConnector`
   - Контейнер: `TrackTraceContainerConnector` → `CarrierWebsiteConnector` → `FixtureConnector`
4. **Fallback по конекторах** — конектори пробуються по черзі; перемагає перший результат `OK`. Live-конектори використовують Playwright для скрапінгу track-trace.com. Якщо живий сайт повертає CAPTCHA або недоступний, конектор повертає `CAPTCHA_REQUIRED` чи `SOURCE_UNAVAILABLE`, і пробується наступний конектор у ланцюгу. `FixtureConnector` у кінці ланцюга парсить збережені зразкові HTML-сторінки й завжди дає результат для двох демо-номерів (`080-38652331` та `TLLU4912250`).
5. **Парсинг** — BeautifulSoup витягує події, дати (ETD/ETA/фактичні) та маршрут із сирого HTML.
6. **Нормалізація** — детерміновані таблиці правил за ключовими словами маплять текст `raw_status` у значення енума `NormalizedStatus`. Якщо опційний LLM увімкнено, а результат досі `unknown`, LLM пропонує значення з дозволеного енума; пропозиція валідується й відкидається, якщо невалідна.
7. **Оцінка якості та ризику** — впевненість, відсутні поля, виявлення затримки та рівень ризику обчислюються детерміновано.
8. **Вихід** — `build_response()` складає `TrackingResponse`; CLI пише його у JSON-файл або в stdout.

Шлях через live-конектор використовує Playwright (реальна автоматизація браузера). Запуск без доступного для Playwright Chromium усе одно працює через fallback на фікстури — повний пайплайн parse/normalize/quality відпрацьовує без доступу до інтернету.

---

## Локальний запуск

### Вимоги

- Python 3.11+
- (опційно) Chromium для live-скрапінгу

### Кроки

```bash
# 1. Створити та активувати віртуальне середовище
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. Встановити пакет у editable-режимі з dev-залежностями
pip install -e ".[dev]"

# 3. (Опційно) Встановити Chromium для live-скрапінгу track-trace.com
playwright install chromium

# 4. Скопіювати приклад env-файлу та налаштувати за потреби
cp .env.example .env

# 5. Запустити CLI
python -m tracking_agent.cli --input examples/input.json --output examples/output.json

# Вивести в stdout замість запису у файл
python -m tracking_agent.cli --input examples/input.json
```

### Запуск API

```bash
uvicorn tracking_agent.api.app:app --reload
```

Відкрийте http://localhost:8000 для web UI завантаження файлу (приймає `.csv` або `.xlsx`).

Трекінг через `curl`:

```bash
curl -X POST http://localhost:8000/track \
  -H "Content-Type: application/json" \
  -d '{
    "shipments": [
      {"id": "s1", "number": "080-38652331"},
      {"id": "s2", "number": "TLLU4912250"}
    ]
  }'
```

### Запуск тестів

```bash
pytest -q
```

---

## Запуск через Docker

```bash
# Скопіювати та налаштувати env
cp .env.example .env

# Зібрати та запустити
docker compose up
```

API доступний за адресою http://localhost:8000.

---

## Вхідні формати

### JSON

```json
{
  "shipments": [
    {"id": "internal-001", "number": "080-38652331"},
    {"id": "internal-002", "number": "501-20285134"},
    {"id": "internal-006", "number": "TLLU4912250"},
    {"id": "internal-011", "number": "hello-bad-number"}
  ]
}
```

Опційні поля для кожного вантажу: `type` (підказка, якій не довіряємо беззастережно), `carrier`, `comment`.

### CSV

```csv
id,number
internal-001,080-38652331
internal-006,TLLU4912250
```

---

## Формат відповіді

### Повний формат (за замовчуванням)

Верхньорівнева обгортка:

```json
{
  "request_id": "cli-728edc30",
  "checked_at": "2026-06-08T11:58:43.479070Z",
  "summary": {"total": 4, "success": 2, "failed": 2},
  "results": [...]
}
```

Кожен результат містить: `input`, `detected`, `tracking`, `source`, `quality`, `risk`, `errors`, `debug`.

Фрагмент результату для авіа AWB (з `examples/output.json`):

```json
{
  "input": {"id": "internal-001", "number": "080-38652331", "type": null, "carrier": null, "comment": null},
  "detected": {
    "type": "air_awb",
    "normalized_number": "080-38652331",
    "carrier": {"name": "LOT Polish Airlines", "code": "LO", "source": "awb_prefix"}
  },
  "tracking": {
    "current_status": "in_transit",
    "raw_status": "In transit / transfer (MAN)",
    "status_uk": "У дорозі",
    "last_event": {
      "event_name": "In transit / transfer (MAN)",
      "location": "DOH",
      "datetime": "2026-06-07T06:10:00+02:00",
      "is_actual": true
    },
    "dates": {
      "etd": {"datetime": "2026-06-05T18:00:00+08:00", "timezone": "+08:00", "timezone_confidence": "source_provided"},
      "eta": {"datetime": "2026-06-08T10:30:00+02:00", "timezone": "+02:00", "timezone_confidence": "source_provided"},
      "actual_departure": null,
      "actual_arrival": null
    },
    "route": {"origin": "HKG", "destination": "WAW", "transit_points": []},
    "events": [
      {"event_name": "Cargo received from shipper (RCS)", "normalized_status": "received", "location": "HKG", "datetime": "2026-06-05T09:15:00+08:00"},
      {"event_name": "Departed from origin airport (DEP)", "normalized_status": "departed", "location": "HKG", "datetime": "2026-06-05T18:45:00+08:00"},
      {"event_name": "In transit / transfer (MAN)", "normalized_status": "in_transit", "location": "DOH", "datetime": "2026-06-07T06:10:00+02:00"}
    ]
  },
  "source": {"primary_source": "track-trace.com/aircargo", "final_source": "fixtures", "url": "fixture://air_080-38652331.html"},
  "quality": {"confidence": 0.7, "data_complete": false, "missing_fields": ["actual_departure", "actual_arrival"], "warnings": []},
  "risk": {"risk_level": "medium", "delay_detected": true, "reasons": ["past_eta"]},
  "errors": [{"code": "PARTIAL_DATA", "message": "Some key fields are missing", "source": "fixtures"}]
}
```

### Короткий формат

`ShortResult` — компактний формат для інтеграцій, що містить: `id`, `number`, `type`, `current_status`, `eta`, `etd`, `last_event_at`, `source`, `errors`.

---

## Підтримувані джерела

| Джерело | Тип | Примітка |
|---|---|---|
| `track-trace.com/aircargo` | Live (Playwright) | Основне для авіа AWB; повертає `CAPTCHA_REQUIRED` за блокування |
| `track-trace.com/container` | Live (Playwright) | Основне для морських контейнерів; повертає `CAPTCHA_REQUIRED` за блокування |
| `carrier_website` | Live (заглушка) | Загальний fallback; розширюється під кожного перевізника |
| `cargoai` | API (опційно) | Потребує `CARGOAI_API_KEY`; пропускається без ключа |
| `fixtures` | Локальні HTML-файли | Завжди доступний fallback; парсить директорію `fixtures/` |

### Ланцюг fallback

Роутер пробує конектори по черзі. Перший конектор, що повертає `OK`, завершує ланцюг. Якщо live-конектор падає (мережева помилка, таймаут, CAPTCHA, потрібен логін), помилка фіксується по кожному конектору, і пробується наступний. Фінальний `FixtureConnector` використовує `fixtures/index.json` для пошуку заздалегідь збережених HTML-сторінок — якщо фікстури для номера немає, повертає `NOT_FOUND`.

---

## Довідник статусів

`normalized_status` завжди одне з цих значень:

| Значення | Зміст |
|---|---|
| `not_found` | Дані трекінгу не знайдено в жодному джерелі |
| `created` | Запис вантажу створено |
| `booked` | Бронювання підтверджено |
| `received` | Вантаж прийнято перевізником |
| `in_origin_terminal` | Вантаж прийнято в терміналі відправлення |
| `departed` | Відправлено з аеропорту / порту відправлення |
| `in_transit` | У дорозі або в точці перевантаження |
| `arrived` | Прибув до аеропорту / порту призначення |
| `customs` | На митному оформленні |
| `ready_for_pickup` | Доступний до видачі / повідомлено |
| `delivered` | Доставлено отримувачу |
| `container_picked_up` | Порожній контейнер забрано (море) |
| `container_returned` | Порожній контейнер повернуто в депо (море) |
| `exception` | Виняткова ситуація, затримання чи затримка від перевізника |
| `unknown` | Сирий статус наявний, але жодне правило не співпало |

Кожен результат також містить `status_uk` — той самий статус українською.

---

## Коди помилок

Усі помилки використовують один із восьми кодів (ніколи довільні рядки):

| Код | Зміст |
|---|---|
| `INVALID_FORMAT` | Номер не відповідає regex AWB чи контейнера |
| `NOT_FOUND` | Усі джерела не повернули даних трекінгу |
| `SOURCE_UNAVAILABLE` | Конектор не зміг дістатися джерела |
| `TIMEOUT` | Запит конектора перевищив налаштований таймаут |
| `CAPTCHA_REQUIRED` | Живий сайт заблокував запит через CAPTCHA |
| `LOGIN_REQUIRED` | Джерело вимагає автентифікацію, якої не надано |
| `PARSING_FAILED` | Джерело повернуло дані, які не вдалося розпарсити |
| `PARTIAL_DATA` | Дані отримано, але частина очікуваних полів відсутня |

Помилки — це список на кожному результаті; `PARTIAL_DATA` не блокує (результат усе одно вважається частковим успіхом).

---

## Якість і ризик

### Блок якості

| Поле | Опис |
|---|---|
| `confidence` | 0.0–1.0; на основі наявності подій, дат і маршруту |
| `data_complete` | `true` лише коли всі ключові поля заповнені |
| `missing_fields` | Список назв відсутніх полів |
| `warnings` | Некритичні зауваження (напр. `invalid_check_digit`, `status_normalized_by_llm`) |

### Блок ризику

| Поле | Опис |
|---|---|
| `risk_level` | `low` / `medium` / `high` |
| `delay_detected` | `true`, коли поточний час перевищив ETA, а статус не є термінальним |
| `reasons` | Список чинників (`past_eta`, `exception_status`) |

Логіка ризику:
- `delay_detected=true` → `medium`
- `exception_status` у причинах → `high`
- Інакше → `low`

---

## Опційні можливості

Усі опційні можливості мають детермінований fallback, тож їх безпечно лишати вимкненими.

| Можливість | Env-змінна(і) | За замовчуванням | Примітка |
|---|---|---|---|
| LLM-нормалізація статусів | `LLM_ENABLED`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Вимкнено | OpenAI-сумісний; за замовчуванням OpenRouter. Пропонує `NormalizedStatus` для невідомих сирих статусів; пропозиція валідується проти енума й відкидається, якщо невалідна. Ніколи не вигадує дати чи факти. |
| Webhook при зміні статусу | `WEBHOOK_URL`, `WEBHOOK_SECRET` | Вимкнено | POST з заголовком HMAC-SHA256; ретраї за збою; тихо вимкнено, коли `WEBHOOK_URL` порожній |
| Запланований ре-чек | `RECHECK_ENABLED`, `RECHECK_INTERVAL_MINUTES` | Вимкнено | APScheduler повторно трекає всі недоставлені номери з історії кожні N хвилин |
| Експорт у Google Sheets | встановити `.[sheets]` + env-змінні сервіс-акаунта | Вимкнено | Потребує екстри `google-api-python-client` та файлу облікових даних сервіс-акаунта; тихо відкочується до Excel |
| Кеш результатів | `CACHE_TTL_MINUTES` | 60 хв | На SQLite; ключ — нормалізований номер |
| Debug-артефакти | `DEBUG_ARTIFACTS` | Вимкнено | Зберігає сирий HTML і скриншоти по кожному номеру в `data/debug/` |

---

## Як додати новий конектор

1. **Реалізуйте** Protocol `Connector` у новому файлі під `src/tracking_agent/connectors/`:

```python
# src/tracking_agent/connectors/my_carrier.py
from __future__ import annotations
from ..models.enums import NumberType
from .base import Connector, ConnectorResult, ConnectorStatus, ErrorCode


class MyCarrierConnector:
    name = "my-carrier"
    supports = (NumberType.AIR_AWB,)

    async def fetch(self, normalized_number: str, number_type: NumberType) -> ConnectorResult:
        # Виклик API перевізника або скрапінг його сайту.
        # Повернути ConnectorResult зі status=ConnectorStatus.OK і raw_html=...
        # за успіху, або status=ConnectorStatus.ERROR і error_code=... за збою.
        ...
```

Protocol `Connector` вимагає трьох атрибутів: `name` (str), `supports` (кортеж `NumberType`) та async-метод `fetch(normalized_number, number_type) -> ConnectorResult`.

2. **Зареєструйте** конектор у `src/tracking_agent/connectors/registry.py`:

```python
from .my_carrier import MyCarrierConnector

def all_connectors():
    return {
        ...
        "my-carrier": MyCarrierConnector(),
    }
```

3. **Додайте його в ланцюг** у `src/tracking_agent/pipeline/router.py`:

```python
def build_chain(number_type: NumberType, use_fixtures: bool):
    reg = all_connectors()
    chain = []
    if number_type == NumberType.AIR_AWB:
        chain = [reg["track-trace.com/aircargo"], reg["my-carrier"], reg["carrier_website"], reg["cargoai"]]
    ...
```

Новий конектор пробуватиметься по черзі; якщо він падає, наступний конектор у ланцюгу пробується автоматично.

---

## Обмеження та відомі проблеми

- **Живі сайти вимагають CAPTCHA** — track-trace.com часто запускає CAPTCHA для автоматизованих запитів. Коли це стається, конектор повертає `CAPTCHA_REQUIRED`, і пайплайн переходить до наступного конектора (зрештою фікстур). Структурована помилка зберігається у відповіді.
- **Фікстури для демо** — `examples/output.json` і набір тестів використовують HTML-сторінки-фікстури в `fixtures/`. Лише `080-38652331` (авіа) та `TLLU4912250` (контейнер) мають фікстури; інші номери повертають `NOT_FOUND` від конектора фікстур.
- **Контрольна цифра ISO 6346** — детектор перевіряє контрольну цифру й додає попередження `invalid_check_digit` за невідповідності, але не відкидає номер і не зупиняє обробку.
- **З'єднання SQLite** — з'єднання відкриваються й закриваються на кожну операцію; немає явного пулу з'єднань чи тюнінгу `PRAGMA`. Підходить для прототипу; для production-навантаження замініть на PostgreSQL.
- **Google Sheets** — потребує опційної екстри `.[sheets]` (`pip install -e ".[sheets]"`) та файлу облікових даних сервіс-акаунта; без них коректно вимкнено.
- **LLM-нормалізація** — активується лише коли `LLM_ENABLED=true` і задано валідний `LLM_API_KEY`; вихід завжди валідується проти енума `NormalizedStatus` перед використанням.
- **Playwright Chromium** — має бути встановлений окремо (`playwright install chromium`) для live-скрапінгу; сам пакет не встановлює його автоматично.

---

## Відповідність критеріям приймання

| Критерій ТЗ §13 | Покриття |
|---|---|
| Запускається локально за README | Розділ `Локальний запуск` вище |
| Приймає JSON-список номерів вантажів | `POST /track`, CLI `--input`, `examples/input.json` |
| Кожен номер обробляється незалежно | Пул воркерів `pipeline/queue.py`; помилки ізольовані по результату |
| Автовизначення типу (AWB / контейнер) | `detection/detector.py` |
| Окрема логіка для AWB і контейнера | `rules_air.py`, `rules_container.py`, ланцюги конекторів за типом |
| Повертає валідний JSON | Схеми Pydantic v2 гарантують структуру; `examples/output.json` |
| `normalized_status` + `raw_status` | Обидва поля наявні в кожному результаті трекінгу |
| ETA/ETD за наявності | `dates.etd`, `dates.eta` (ISO 8601 з таймзоною) |
| Поля pickup / return контейнера | Статуси `container_picked_up`, `container_returned` + події |
| Список подій | `tracking.events[]` з `event_name`, `location`, `datetime`, `normalized_status` |
| Блок джерела даних | `source.primary_source`, `source.final_source`, `source.url` |
| Блок помилок зі зрозумілими кодами | `errors[]` з енумом `ErrorCode` на 8 значень |
| Без хардкоду номерів трекінгу | Усі номери надходять із входу; фікстури за нормалізованим номером, визначеним у рантаймі |
| Розширювані конектори | Protocol `Connector` — один файл + реєстрація, без змін ядра |
| README з прикладами запуску / входу / виходу / гайдом по конектору | Цей документ |

---

## Додаткові завдання

Окрім обов'язкового MVP, реалізовано **всі** опційні пункти з ТЗ §15. Кожен має детермінований fallback і вмикається через env, тож рев'ю запускається однією командою без жодних ключів.

| ТЗ §15 — додаткове завдання | Реалізація | Як увімкнути / перевірити |
|---|---|---|
| Черга обробки номерів | `pipeline/queue.py` — пул воркерів на `asyncio.Queue` з обмеженою конкурентністю | `MAX_CONCURRENCY` (за замовч. 3); застосовується до кожного батчу |
| Кешування результатів | `storage/cache.py` — кеш на SQLite з TTL, ключ = нормалізований номер | `CACHE_TTL_MINUTES` (за замовч. 60) |
| Повторна перевірка через інтервал | `scheduler/recheck.py` — завдання APScheduler, що ре-трекає недоставлені номери | `RECHECK_ENABLED=true`, `RECHECK_INTERVAL_MINUTES` |
| Webhook при зміні статусу | `webhook/notifier.py` — POST з підписом HMAC-SHA256 + ретраї | `WEBHOOK_URL`, `WEBHOOK_SECRET` |
| Порівняння попереднього статусу з новим | `storage/history.py` — історія статусів; `record()` повертає `True` лише за зміни | спрацьовує під час ре-чеку; diff `{old, new}` йде у webhook |
| Визначення затримки відносно ETA | `quality/risk.py` — `now > eta` і статус не термінальний → причина `past_eta` | поле `risk.delay_detected` у кожному результаті |
| Поля `risk_level` і `delay_detected` | `models/schemas.py` блок `Risk` + `quality/risk.py` | блок `risk` у кожному результаті (`low`/`medium`/`high`) |
| Автоматичний переклад raw status українською | `normalization/translate_uk.py` — статичний словник на всі 15 статусів (повне покриття) | поле `tracking.status_uk` (напр. `"У дорозі"`) |
| Простий web UI для завантаження Excel | `api/web.py` — `GET /` форма завантаження, `POST /track/file` парсить `.xlsx`/`.csv` | `uvicorn tracking_agent.api.app:app` → http://localhost:8000 |
| Експорт результату в Excel або Google Sheets | `export/excel.py` (openpyxl, завжди) + `export/sheets.py` (опційно) | Excel працює без налаштувань; Sheets — екстра `.[sheets]` + сервіс-акаунт |

Деталі конфігурації кожної можливості — у розділі [Опційні можливості](#опційні-можливості).
