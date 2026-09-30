from __future__ import annotations

import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def configure_observability(app: FastAPI) -> None:
    configure_logging()
    registry = CollectorRegistry()
    requests = Counter(
        "fantasy_hud_http_requests_total",
        "HTTP requests",
        ["method", "path", "status"],
        registry=registry,
    )
    latency = Histogram(
        "fantasy_hud_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
        registry=registry,
    )
    logger = logging.getLogger("fantasy_hud.http")

    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        started = time.perf_counter()
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        span = trace.get_current_span()
        trace_id = format(span.get_span_context().trace_id, "032x")
        try:
            response = await call_next(request)
        except Exception:
            requests.labels(request.method, request.url.path, "500").inc()
            logger.exception(
                "request failed", extra={"request_id": request_id, "trace_id": trace_id}
            )
            raise
        elapsed = time.perf_counter() - started
        requests.labels(request.method, request.url.path, str(response.status_code)).inc()
        latency.labels(request.method, request.url.path).observe(elapsed)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request complete method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
            extra={"request_id": request_id, "trace_id": trace_id},
        )
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")

    provider = TracerProvider(resource=Resource.create({"service.name": "fantasy-hud-api"}))
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
