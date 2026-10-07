import main


def test_get_cart_returns_items(monkeypatch):
    monkeypatch.setattr(
        main.cart_manager,
        "get",
        lambda userid: {"book-1": "2"},
    )
    client = main.app.test_client()

    response = client.get("/cart/testuser")

    assert response.status_code == 200
    assert response.get_json() == {
        "userid": "testuser",
        "cart": {"book-1": "2"},
    }


def test_add_item_returns_created_item(monkeypatch):
    monkeypatch.setattr(
        main.cart_manager,
        "add",
        lambda userid, product_id, qty: {
            "product_id": product_id,
            "quantity": qty,
        },
    )
    client = main.app.test_client()

    response = client.post(
        "/cart/testuser",
        json={"product_id": "book-1", "quantity": 2},
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "product_id": "book-1",
        "quantity": 2,
    }


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