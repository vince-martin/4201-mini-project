import json
import os
from flask import Flask, request, jsonify
from flask.views import MethodView
import redis

# this code is built on the lab0 code
app = Flask(__name__)

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
        return redis_instance.hgetall(f"cart:{userid}")
    def add(self, userid, product_id, qty):
        redis_instance.hset(f"cart:{userid}", product_id, qty)
        return {"product_id": product_id, "quantity": qty} #echo back what wsa added
    def clear(self, userid):
        redis_instance.delete(f"cart:{userid}")

cart_manager = CartCtrl()

class CartAPI(MethodView):

    def get(self, userid):
        all_cart_items = cart_manager.get(userid)
        return jsonify({"userid": userid, "cart": all_cart_items}), 200

    def post(self, userid):
        """ add comment from request """
        item_data = request.get_json()
        product_id = item_data.get("product_id")
        qty = item_data.get("quantity")

        new_item = cart_manager.add(userid, product_id, qty)
        return jsonify(new_item), 201

    def delete(self, userid):
        cart_manager.clear(userid)
        return jsonify({"message": "deleted"}), 200

cart_view = CartAPI.as_view("cart_api")
app.add_url_rule("/cart/<string:userid>", view_func=cart_view, methods=["GET", "POST", "DELETE"])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)