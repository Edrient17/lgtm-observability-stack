import json
import logging
import os
import random
import time

import requests
from flask import Flask, Response, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "api-service")
SERVICE_ROLE = os.getenv("SERVICE_ROLE", "api")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8081")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8082")
PORT = int(os.getenv("PORT", "8080"))


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
            "service": SERVICE_NAME,
            "role": SERVICE_ROLE,
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
    resource = Resource.create({"service.name": SERVICE_NAME, "service.role": SERVICE_ROLE})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
    trace.set_tracer_provider(provider)


def simulated_delay(low=0.03, high=0.25):
    delay = random.uniform(low, high)
    time.sleep(delay)
    return round(delay, 3)


def get_json(url):
    response = requests.get(url, timeout=3)
    response.raise_for_status()
    return response.json()


configure_logging()
configure_tracing()

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(SERVICE_NAME)

REQUEST_COUNT = Counter(
    "demo_app_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "demo_app_request_duration_seconds",
    "HTTP request latency",
    ["service", "endpoint"],
)


@app.before_request
def start_timer():
    request.start_time = time.time()


@app.after_request
def record_metrics(response):
    endpoint = request.endpoint or "unknown"
    REQUEST_COUNT.labels(SERVICE_NAME, request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(SERVICE_NAME, endpoint).observe(time.time() - request.start_time)
    return response


@app.get("/")
def index():
    logger.info("handled index request")
    return jsonify({"service": SERVICE_NAME, "role": SERVICE_ROLE, "status": "ok"})


@app.get("/work")
def work():
    with tracer.start_as_current_span("synthetic-work"):
        delay = simulated_delay(0.05, 0.35)
        logger.info("completed synthetic work in %.3fs", delay)
        return jsonify({"service": SERVICE_NAME, "delay_seconds": delay})


@app.get("/error")
def error():
    with tracer.start_as_current_span("synthetic-error"):
        logger.error("intentional demo error")
        return jsonify({"service": SERVICE_NAME, "error": "intentional demo error"}), 500


@app.get("/checkout")
def checkout():
    with tracer.start_as_current_span("checkout-flow") as span:
        if SERVICE_ROLE != "api":
            return jsonify({"error": "checkout is only served by api-service"}), 404

        user_id = random.randint(1000, 9999)
        cart_total = round(random.uniform(10, 250), 2)
        span.set_attribute("demo.user_id", user_id)
        span.set_attribute("demo.cart_total", cart_total)

        try:
            order = get_json(f"{ORDER_SERVICE_URL}/orders?user_id={user_id}&amount={cart_total}")
        except requests.RequestException as exc:
            logger.exception("checkout failed while calling order-service")
            return jsonify({"service": SERVICE_NAME, "error": "order-service unavailable", "detail": str(exc)}), 502

        logger.info("checkout completed order_id=%s total=%.2f", order.get("order_id"), cart_total)
        return jsonify({"service": SERVICE_NAME, "checkout": "ok", "order": order})


@app.get("/orders")
def create_order():
    with tracer.start_as_current_span("create-order") as span:
        if SERVICE_ROLE != "order":
            return jsonify({"error": "orders are only served by order-service"}), 404

        amount = float(request.args.get("amount", "0"))
        user_id = request.args.get("user_id", "unknown")
        order_id = f"ord-{random.randint(10000, 99999)}"
        delay = simulated_delay(0.04, 0.22)
        span.set_attribute("demo.order_id", order_id)
        span.set_attribute("demo.amount", amount)

        try:
            payment = get_json(f"{PAYMENT_SERVICE_URL}/payments?order_id={order_id}&amount={amount}")
        except requests.RequestException as exc:
            logger.exception("order failed while calling payment-service order_id=%s", order_id)
            return jsonify({"service": SERVICE_NAME, "order_id": order_id, "error": "payment failed", "detail": str(exc)}), 502

        logger.info("created order_id=%s user_id=%s delay=%.3fs", order_id, user_id, delay)
        return jsonify(
            {
                "service": SERVICE_NAME,
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount,
                "delay_seconds": delay,
                "payment": payment,
            }
        )


@app.get("/payments")
def authorize_payment():
    with tracer.start_as_current_span("authorize-payment") as span:
        if SERVICE_ROLE != "payment":
            return jsonify({"error": "payments are only served by payment-service"}), 404

        order_id = request.args.get("order_id", "unknown")
        amount = float(request.args.get("amount", "0"))
        delay = simulated_delay(0.02, 0.3)
        span.set_attribute("demo.order_id", order_id)
        span.set_attribute("demo.amount", amount)

        if random.random() < 0.12:
            logger.error("payment authorization failed order_id=%s amount=%.2f", order_id, amount)
            return jsonify({"service": SERVICE_NAME, "order_id": order_id, "status": "declined"}), 500

        logger.info("payment authorized order_id=%s amount=%.2f delay=%.3fs", order_id, amount, delay)
        return jsonify({"service": SERVICE_NAME, "order_id": order_id, "status": "authorized", "delay_seconds": delay})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
