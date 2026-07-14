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
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8081")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8082")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://cart-service:8083")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8084")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8085")
PORT = int(os.getenv("PORT", "8080"))

PRODUCTS = [
    {"sku": "sku-1001", "name": "LGTM Hoodie", "price": 59.0},
    {"sku": "sku-1002", "name": "Trace Mug", "price": 18.5},
    {"sku": "sku-1003", "name": "Metric Notebook", "price": 12.0},
    {"sku": "sku-1004", "name": "Log Sticker Pack", "price": 7.5},
]


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


def require_role(role):
    if SERVICE_ROLE != role:
        return jsonify({"error": f"this endpoint is only served by {role}-service"}), 404
    return None


def choose_sku():
    return random.choice(PRODUCTS)["sku"]


configure_logging()
configure_tracing()

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app, excluded_urls="/metrics")
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


@app.get("/browse")
def browse():
    if response := require_role("api"):
        return response

    with tracer.start_as_current_span("browse-flow") as span:
        category = random.choice(["apparel", "office", "stickers"])
        span.set_attribute("demo.category", category)
        try:
            catalog = get_json(f"{CATALOG_SERVICE_URL}/catalog?category={category}")
            inventory = get_json(f"{INVENTORY_SERVICE_URL}/inventory/check?sku={catalog['featured_sku']}")
        except requests.RequestException as exc:
            logger.exception("browse failed while calling downstream services")
            return jsonify({"service": SERVICE_NAME, "error": "browse downstream unavailable", "detail": str(exc)}), 502

        logger.info("browse completed category=%s featured_sku=%s", category, catalog["featured_sku"])
        return jsonify({"service": SERVICE_NAME, "flow": "browse", "catalog": catalog, "inventory": inventory})


@app.get("/cart/add")
def add_to_cart():
    if SERVICE_ROLE == "api":
        with tracer.start_as_current_span("cart-add-flow") as span:
            sku = request.args.get("sku", choose_sku())
            user_id = request.args.get("user_id", str(random.randint(1000, 9999)))
            span.set_attribute("demo.sku", sku)
            span.set_attribute("demo.user_id", user_id)

            try:
                cart = get_json(f"{CART_SERVICE_URL}/cart/add?user_id={user_id}&sku={sku}")
            except requests.RequestException as exc:
                logger.exception("cart add failed while calling cart-service")
                return jsonify({"service": SERVICE_NAME, "error": "cart-service unavailable", "detail": str(exc)}), 502

            logger.info("cart add completed user_id=%s sku=%s", user_id, sku)
            return jsonify({"service": SERVICE_NAME, "flow": "cart-add", "cart": cart})

    if SERVICE_ROLE == "cart":
        with tracer.start_as_current_span("cart-add-item") as span:
            sku = request.args.get("sku", choose_sku())
            user_id = request.args.get("user_id", "unknown")
            span.set_attribute("demo.sku", sku)
            span.set_attribute("demo.user_id", user_id)
            try:
                product = get_json(f"{CATALOG_SERVICE_URL}/catalog/item?sku={sku}")
                inventory = get_json(f"{INVENTORY_SERVICE_URL}/inventory/reserve?sku={sku}&qty=1")
            except requests.RequestException as exc:
                logger.exception("cart-service failed while validating sku=%s", sku)
                return jsonify({"service": SERVICE_NAME, "error": "cart validation failed", "detail": str(exc)}), 502

            delay = simulated_delay(0.02, 0.14)
            logger.info("added item to cart user_id=%s sku=%s delay=%.3fs", user_id, sku, delay)
            return jsonify(
                {
                    "service": SERVICE_NAME,
                    "user_id": user_id,
                    "sku": sku,
                    "product": product,
                    "inventory": inventory,
                    "delay_seconds": delay,
                }
            )

    return jsonify({"error": "cart add is served by api-service or cart-service"}), 404


@app.get("/checkout")
def checkout():
    if response := require_role("api"):
        return response

    with tracer.start_as_current_span("checkout-flow") as span:
        user_id = request.args.get("user_id", str(random.randint(1000, 9999)))
        span.set_attribute("demo.user_id", user_id)

        try:
            cart = get_json(f"{CART_SERVICE_URL}/cart/items?user_id={user_id}")
            order = get_json(f"{ORDER_SERVICE_URL}/orders?user_id={user_id}&amount={cart['total']}&sku={cart['sku']}")
        except requests.RequestException as exc:
            logger.exception("checkout failed while calling downstream services")
            return jsonify({"service": SERVICE_NAME, "error": "checkout downstream unavailable", "detail": str(exc)}), 502

        logger.info("checkout completed user_id=%s order_id=%s total=%.2f", user_id, order.get("order_id"), cart["total"])
        return jsonify({"service": SERVICE_NAME, "flow": "checkout", "cart": cart, "order": order})


@app.get("/catalog")
def catalog():
    if response := require_role("catalog"):
        return response

    with tracer.start_as_current_span("list-catalog") as span:
        category = request.args.get("category", "all")
        product = random.choice(PRODUCTS)
        delay = simulated_delay(0.02, 0.18)
        span.set_attribute("demo.category", category)
        span.set_attribute("demo.featured_sku", product["sku"])
        logger.info("catalog listed category=%s featured_sku=%s delay=%.3fs", category, product["sku"], delay)
        return jsonify(
            {
                "service": SERVICE_NAME,
                "category": category,
                "featured_sku": product["sku"],
                "products": PRODUCTS,
                "delay_seconds": delay,
            }
        )


@app.get("/catalog/item")
def catalog_item():
    if response := require_role("catalog"):
        return response

    with tracer.start_as_current_span("get-catalog-item"):
        sku = request.args.get("sku", choose_sku())
        product = next((item for item in PRODUCTS if item["sku"] == sku), PRODUCTS[0])
        delay = simulated_delay(0.01, 0.09)
        logger.info("catalog item resolved sku=%s delay=%.3fs", sku, delay)
        return jsonify({"service": SERVICE_NAME, "product": product, "delay_seconds": delay})


@app.get("/inventory/check")
def inventory_check():
    if response := require_role("inventory"):
        return response

    with tracer.start_as_current_span("check-inventory") as span:
        sku = request.args.get("sku", choose_sku())
        stock = random.randint(0, 50)
        delay = simulated_delay(0.02, 0.16)
        span.set_attribute("demo.sku", sku)
        span.set_attribute("demo.stock", stock)
        logger.info("inventory checked sku=%s stock=%s delay=%.3fs", sku, stock, delay)
        return jsonify({"service": SERVICE_NAME, "sku": sku, "stock": stock, "available": stock > 0, "delay_seconds": delay})


@app.get("/inventory/reserve")
def inventory_reserve():
    if response := require_role("inventory"):
        return response

    with tracer.start_as_current_span("reserve-inventory") as span:
        sku = request.args.get("sku", choose_sku())
        qty = int(request.args.get("qty", "1"))
        delay = simulated_delay(0.03, 0.2)
        span.set_attribute("demo.sku", sku)
        span.set_attribute("demo.qty", qty)

        logger.info("inventory reserved sku=%s qty=%s delay=%.3fs", sku, qty, delay)
        return jsonify({"service": SERVICE_NAME, "sku": sku, "reserved": True, "qty": qty, "delay_seconds": delay})


@app.get("/cart/items")
def cart_items():
    if response := require_role("cart"):
        return response

    with tracer.start_as_current_span("get-cart-items") as span:
        user_id = request.args.get("user_id", "unknown")
        sku = choose_sku()
        qty = random.randint(1, 3)
        product = next((item for item in PRODUCTS if item["sku"] == sku), PRODUCTS[0])
        total = round(product["price"] * qty, 2)
        delay = simulated_delay(0.02, 0.13)
        span.set_attribute("demo.user_id", user_id)
        span.set_attribute("demo.sku", sku)
        span.set_attribute("demo.total", total)
        logger.info("cart loaded user_id=%s sku=%s total=%.2f delay=%.3fs", user_id, sku, total, delay)
        return jsonify({"service": SERVICE_NAME, "user_id": user_id, "sku": sku, "qty": qty, "total": total, "delay_seconds": delay})


@app.get("/orders")
def create_order():
    if response := require_role("order"):
        return response

    with tracer.start_as_current_span("create-order") as span:
        amount = float(request.args.get("amount", "0"))
        user_id = request.args.get("user_id", "unknown")
        sku = request.args.get("sku", choose_sku())
        order_id = f"ord-{random.randint(10000, 99999)}"
        delay = simulated_delay(0.04, 0.22)
        span.set_attribute("demo.order_id", order_id)
        span.set_attribute("demo.amount", amount)

        try:
            inventory = get_json(f"{INVENTORY_SERVICE_URL}/inventory/reserve?sku={sku}&qty=1")
            payment = get_json(f"{PAYMENT_SERVICE_URL}/payments?order_id={order_id}&amount={amount}")
        except requests.RequestException as exc:
            logger.exception("order failed order_id=%s sku=%s", order_id, sku)
            return jsonify({"service": SERVICE_NAME, "order_id": order_id, "error": "order downstream failed", "detail": str(exc)}), 502

        logger.info("created order_id=%s user_id=%s delay=%.3fs", order_id, user_id, delay)
        return jsonify(
            {
                "service": SERVICE_NAME,
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount,
                "delay_seconds": delay,
                "inventory": inventory,
                "payment": payment,
            }
        )


@app.get("/payments")
def authorize_payment():
    if response := require_role("payment"):
        return response

    with tracer.start_as_current_span("authorize-payment") as span:
        order_id = request.args.get("order_id", "unknown")
        amount = float(request.args.get("amount", "0"))
        delay = simulated_delay(0.02, 0.3)
        span.set_attribute("demo.order_id", order_id)
        span.set_attribute("demo.amount", amount)

        logger.info("payment authorized order_id=%s amount=%.2f delay=%.3fs", order_id, amount, delay)
        return jsonify({"service": SERVICE_NAME, "order_id": order_id, "status": "authorized", "delay_seconds": delay})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
