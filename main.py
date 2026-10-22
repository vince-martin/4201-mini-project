import json
import os
import uuid
from decimal import Decimal
from flask import Flask, request, jsonify, g
from flask.views import MethodView
import redis
from datetime import datetime, timezone
from google.cloud import logging as cloud_logging

# this code is built on the lab0 code
app = Flask(__name__)

cloud_client = cloud_logging.Client()
cart_logger = cloud_client.logger("cart-service")

@app.before_request
def assign_correlation_id():
    g.correlation_id = (
        request.headers.get("correlation-id")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )

@app.after_request
def log_cart_request(response):
    now = datetime.now(timezone.utc)

    payload = {
        "timestamp": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "correlation-id": getattr(g, "correlation_id", ""),
        "service-id": "cart-service",
        "call-type": request.method,
        "reply-code": str(response.status_code)
    }

    severity = (
        "ERROR" if response.status_code >= 500
        else "WARNING" if response.status_code >= 400
        else "INFO"
    )

    cart_logger.log_struct(
        payload,
        severity=severity,
        timestamp=now,
        )
    return response

# get env variables for redis credentials
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

redis_instance = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    password=REDIS_PASSWORD, 
    decode_responses=True
)


class CartCtrl:
    def get(self, userid):
        return {
            product_id: json.loads(item)
            for product_id, item in redis_instance.hgetall(f"cart:{userid}").items()
        }
    def contains(self, userid, product_id):
        return redis_instance.hexists(f"cart:{userid}", product_id)
    def add(self, userid, product_id, qty, total_price):
        item = {"product_id": product_id, "quantity": qty, "total_price": total_price}
        redis_instance.hset(f"cart:{userid}", product_id, json.dumps(item))
        return item
    def clear(self, userid):
        redis_instance.delete(f"cart:{userid}")

cart_manager = CartCtrl()

class CartAPI(MethodView):

    def get(self, userid):
        all_cart_items = cart_manager.get(userid)
        total_price = sum(
            (Decimal(str(item["total_price"])) for item in all_cart_items.values()),
            Decimal("0"),
        )
        return jsonify({
            "userid": userid,
            "cart": all_cart_items,
            "total_price": float(total_price),
        }), 200

    def post(self, userid):
        item_data = request.get_json()
        if not isinstance(item_data, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        product_id = item_data.get("product_id")
        qty = item_data.get("quantity")
        price = item_data.get("price")
        total_price = float(Decimal(str(price)) * qty)
        already_present = cart_manager.contains(userid, product_id)
        new_item = cart_manager.add(userid, product_id, qty, total_price)
        return jsonify(new_item), 200 if already_present else 201

    def delete(self, userid):
        cart_manager.clear(userid)
        return jsonify({"message": "deleted"}), 200

cart_view = CartAPI.as_view("cart_api")
app.add_url_rule("/cart/<string:userid>", view_func=cart_view, methods=["GET", "POST", "DELETE"])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)