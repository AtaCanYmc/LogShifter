# Architecture & Design Patterns

logshift is engineered around clean code paradigms, separation of concerns, and system decoupling.

## 1. Strategy Pattern (Decoupled Adapters)
All delivery destinations inherit from the abstract base class `TransportAdapter`:

```python
from logshift.core.adapter import TransportAdapter
```

Adapters only require implementing the async method:
`async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:`

This decoupling allows registering new adapters at runtime without editing `LogManager` logic.

## 2. Cursor-Based Pagination
For high-throughput tables, standard `LIMIT ... OFFSET` queries cause database performance bottlenecks. logshift uses cursor-based pagination tracking the maximum `id` returned, fetching records where `id > last_id`.

## 3. Resilient Retries
All adapter shipping actions are orchestrated by the `LogManager`, which wraps operations in an async retry loop implementing **Exponential Backoff**:

$$\text{delay} = \text{initial\_delay} \times \text{backoff}^{\text{attempt}-1}$$

This handles brief network hiccups gracefully without dropping logs.

## 4. OpenTelemetry Format
Before logs are dispatched to adapters, the `LogFetcher` automatically converts raw database rows into the standard OpenTelemetry OTLP log record structure, mapping:
- Timestamp
- Severity text (e.g. `INFO`, `ERROR`)
- Severity number (`1-24`)
- Body message
- Attributes dictionary (all metadata columns)
- Trace & Span IDs
