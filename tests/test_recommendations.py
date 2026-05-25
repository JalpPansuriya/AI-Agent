import pytest
from httpx import AsyncClient
import uuid
from unittest.mock import patch
from sqlalchemy import select
from app.models.models import Product, User, RequestLog
from app.main import seed_products

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def mock_redis(monkeypatch):
    import fakeredis.aioredis as fake_redis
    fake_client = fake_redis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.core.redis.redis_client", fake_client)
    yield fake_client

async def create_user_helper(client: AsyncClient, email: str, name: str, role: str = "user", db = None) -> str:
    """Helper to register a user, set their role in DB, and log in to get access token."""
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "Password123",
            "full_name": name
        }
    )
    
    # If role needs to be updated (e.g. admin)
    if role != "user" and db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.role = role
        await db.commit()
        
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "Password123"
        }
    )
    return login_resp.json()["access_token"]

async def test_startup_seeding(client: AsyncClient, db):
    # Verify that seed_products correctly populates the database when empty
    # Clean the products table first
    await db.execute(Product.__table__.delete())
    await db.commit()
    
    # Invoke seeding manually
    await seed_products(db)
    
    result = await db.execute(select(Product))
    products = list(result.scalars().all())
    assert len(products) == 12
    
    categories = {p.category for p in products}
    assert "Laptops" in categories
    assert "Phones" in categories
    assert "Accessories" in categories

async def test_list_products_and_category_filter(client: AsyncClient, db):
    await seed_products(db)
    token = await create_user_helper(client, "normal@example.com", "Normal User")
    
    # GET /products without filter
    response = await client.get("/api/v1/products", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 12
    
    # GET /products with filter
    response_laptops = await client.get(
        "/api/v1/products?category=Laptops",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response_laptops.status_code == 200
    laptops_data = response_laptops.json()
    assert len(laptops_data) == 4
    for p in laptops_data:
        assert p["category"] == "Laptops"

async def test_admin_create_product(client: AsyncClient, db):
    admin_token = await create_user_helper(client, "admin_create@example.com", "Admin Create", "admin", db)
    user_token = await create_user_helper(client, "user_create@example.com", "User Create", "user", db)
    
    # 1. Admin can create a product -> 201
    prod_payload = {
        "name": "Super Ring",
        "description": "Smart ring of power.",
        "category": "Accessories",
        "tags": ["magic", "ring", "power"],
        "price": 299.99
    }
    
    admin_resp = await client.post(
        "/api/v1/products",
        json=prod_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_resp.status_code == 201
    admin_data = admin_resp.json()
    assert admin_data["name"] == "Super Ring"
    assert "id" in admin_data
    
    # 2. Non-admin cannot create a product -> 403
    user_resp = await client.post(
        "/api/v1/products",
        json=prod_payload,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert user_resp.status_code == 403
    assert user_resp.json()["detail"] == "Not enough permissions"

async def test_admin_update_and_soft_delete(client: AsyncClient, db):
    admin_token = await create_user_helper(client, "admin_delete@example.com", "Admin Delete", "admin", db)
    
    # Create product to delete
    create_resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Soft Deleted Laptop",
            "description": "Soon to be deleted.",
            "category": "Laptops",
            "tags": ["delete", "temp"],
            "price": 100.00
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    product_id = create_resp.json()["id"]
    
    # Admin can update product
    update_resp = await client.put(
        f"/api/v1/products/{product_id}",
        json={"name": "Updated Laptop Name", "price": 99.99},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Laptop Name"
    assert update_resp.json()["price"] == 99.99
    
    # Admin can soft delete a product -> 204
    delete_resp = await client.delete(
        f"/api/v1/products/{product_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete_resp.status_code == 204
    
    # Verify product no longer appears in GET /products
    get_resp = await client.get("/api/v1/products", headers={"Authorization": f"Bearer {admin_token}"})
    products_list = get_resp.json()
    for p in products_list:
        assert p["id"] != product_id
        
    # Verify in DB that is_active is False
    prod_in_db = await db.get(Product, uuid.UUID(product_id))
    assert prod_in_db is not None
    assert prod_in_db.is_active is False

@patch("app.services.recommendation_service.call_openai")
async def test_contextual_recommendations(mock_call_openai, client: AsyncClient, db):
    await seed_products(db)
    token = await create_user_helper(client, "recs@example.com", "Recs User")
    
    # Create a chat session
    session_resp = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Gaming Chat"},
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_resp.json()["id"]
    
    # Send a message about gaming laptops
    # We patch call_openai in the recommendations extraction
    mock_call_openai.return_value = (
        '{"interests": ["gaming", "rtx", "Laptops"]}',
        {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
    )
    
    # When sending a chat message, it calls recommendation_service and returns MessageResponse
    # We mock openai in chat_service.call_openai as well
    with patch("app.services.chat_service.call_openai") as mock_chat_openai:
        mock_chat_openai.return_value = (
            "Here is the perfect gaming laptop recommendation.",
            {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        )
        
        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "I need a high performance gaming laptop"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        msg_data = response.json()
        assert "recommendations" in msg_data
        assert msg_data["recommendations"] is not None
        assert len(msg_data["recommendations"]) > 0
        
        # Verify that it matched the holographic display "Nebula Horizon Gaming 17" due to "gaming" tag overlap
        rec_names = [p["name"] for p in msg_data["recommendations"]]
        assert "Nebula Horizon Gaming 17" in rec_names
        
    # GET /recommendations (using most recent session)
    get_recs = await client.get("/api/v1/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert get_recs.status_code == 200
    assert len(get_recs.json()) > 0

async def test_recommendations_authorization_and_fallbacks(client: AsyncClient, db):
    await seed_products(db)
    token1 = await create_user_helper(client, "owner_rec@example.com", "Owner Rec", "user", db)
    token2 = await create_user_helper(client, "attacker_rec@example.com", "Attacker Rec", "user", db)
    
    session_resp = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "My Session"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    session_id = session_resp.json()["id"]
    
    # 1. Non-existent session -> 404
    fake_id = str(uuid.uuid4())
    resp_404 = await client.get(f"/api/v1/recommendations/{fake_id}", headers={"Authorization": f"Bearer {token1}"})
    assert resp_404.status_code == 404
    
    # 2. Attacker gets Forbidden -> 403
    resp_403 = await client.get(f"/api/v1/recommendations/{session_id}", headers={"Authorization": f"Bearer {token2}"})
    assert resp_403.status_code == 403
    
    # 3. Valid owner session with no messages -> falls back to recent active products -> 200
    resp_fallback = await client.get(f"/api/v1/recommendations/{session_id}", headers={"Authorization": f"Bearer {token1}"})
    assert resp_fallback.status_code == 200
    data = resp_fallback.json()
    assert len(data) == 5
