import main
import json
from unittest.mock import Mock
import pytest


def test_get_cart_returns_items(monkeypatch):
    monkeypatch.setattr(
        main.cart_manager,
        "get",
        lambda userid: {"book-1": {"product_id": "book-1", "quantity": 2, "total_price": 5}},
    )
    client = main.app.test_client()

    response = client.get("/cart/testuser")

    assert response.status_code == 200
    assert response.get_json() == {
        "userid": "testuser",
        "cart": {"book-1": {"product_id": "book-1", "quantity": 2, "total_price": 5}},
        "total_price": 5.0,
    }


@pytest.mark.parametrize("already_present, status", [(False, 201), (True, 200)])
def test_add_item_returns_created_item(monkeypatch, already_present, status):
    storage = Mock()
    storage.hexists.return_value = already_present
    monkeypatch.setattr(main, "redis_instance", storage)
    client = main.app.test_client()

    response = client.post(
        "/cart/testuser",
        json={"product_id": "testitem-123", "quantity": 4, "price": 2.5},
    )

    expected = {
        "product_id": "testitem-123",
        "quantity": 4,
        "total_price": 10,
    }
    assert response.status_code == status
    assert response.get_json() == expected
    storage.hexists.assert_called_once_with("cart:testuser", "testitem-123")
    storage.hset.assert_called_once()
    cart_key, product_id, stored_item = storage.hset.call_args.args
    assert cart_key == "cart:testuser"
    assert product_id == "testitem-123"
    assert json.loads(stored_item) == expected
    storage.hgetall.return_value = {product_id: stored_item}
    assert client.get("/cart/testuser").get_json()["cart"] == {product_id: expected}


@pytest.mark.parametrize("payload", [
    {},
    [],
    {"product_id": "book-1", "quantity": 2},
    {"product_id": "", "quantity": 2, "price": 2.5},
    {"product_id": "book-1", "quantity": 0, "price": 2.5},
    {"product_id": "book-1", "quantity": True, "price": 2.5},
    {"product_id": "book-1", "quantity": 2, "price": -1},
    {"product_id": "book-1", "quantity": 2, "price": "2.5"},
    {"product_id": "book-1", "quantity": 2, "price": float("nan")},
    {"product_id": "book-1", "quantity": 2, "price": float("inf")},
    {"product_id": "book-1", "quantity": 2, "price": 1e308},
])
def test_invalid_item_is_rejected(monkeypatch, payload):
    storage = Mock()
    monkeypatch.setattr(main, "redis_instance", storage)
    response = main.app.test_client().post("/cart/testuser", json=payload)
    assert response.status_code == 400
    storage.hexists.assert_not_called()
    storage.hset.assert_not_called()


def test_total_price_uses_decimal_arithmetic(monkeypatch):
    storage = Mock()
    storage.hexists.return_value = False
    monkeypatch.setattr(main, "redis_instance", storage)
    response = main.app.test_client().post(
        "/cart/testuser", json={"product_id": "book-1", "quantity": 3, "price": 0.1},
    )
    assert response.status_code == 201
    assert response.get_json()["total_price"] == 0.3


def test_delete_cart_clears_user_cart(monkeypatch):
    cleared_users = []
    monkeypatch.setattr(
        main.cart_manager,
        "clear",
        lambda userid: cleared_users.append(userid),
    )
    client = main.app.test_client()

    response = client.delete("/cart/testuser")

    assert response.status_code == 200
    assert response.get_json() == {"message": "deleted"}
    assert cleared_users == ["testuser"]