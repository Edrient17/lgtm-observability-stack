import json
import logging
import os
import random
import time

from flask import Flask, Response, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "demo-app")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")


class TraceContextFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        context = span.get_span_context()
        if context.is_valid:
            record.trace_id = format(context.trace_id, "032x")
            record.span_id = format(context.span_id, "016x")
        else:
            record.trace_id = ""
            record.span_id = ""
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", ""),
            "span_id": getattr(record, "span_id", ""),
        }
        return json.dumps(payload)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceContextFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def configure_tracing():
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
    trace.set_tracer_provider(provider)


configure_logging()
configure_tracing()

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer(__name__)
logger = logging.getLogger("demo-app")

REQUEST_COUNT = Counter("demo_app_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("demo_app_request_duration_seconds", "HTTP request latency", ["endpoint"])


@app.before_request
def start_timer():
    request.start_time = time.time()


@app.after_request
def record_metrics(response):
    endpoint = request.endpoint or "unknown"
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(endpoint).observe(time.time() - request.start_time)
    return response


@app.get("/")
def index():
    logger.info("handled index request")
    return jsonify({"service": SERVICE_NAME, "status": "ok"})


@app.get("/work")
def work():
    with tracer.start_as_current_span("synthetic-work"):
        delay = random.uniform(0.05, 0.35)
        time.sleep(delay)
        logger.info("completed synthetic work in %.3fs", delay)
        return jsonify({"delay_seconds": round(delay, 3)})


@app.get("/error")
def error():
    with tracer.start_as_current_span("synthetic-error"):
        logger.error("intentional demo error")
        return jsonify({"error": "intentional demo error"}), 500


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

