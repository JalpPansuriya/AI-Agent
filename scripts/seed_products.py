"""
Standalone seed script — inserts 15 demo products if the table is empty.

Usage (from project root, via Docker):
    docker-compose exec app python scripts/seed_products.py

Usage (locally, with DATABASE_URL set in .env):
    PYTHONPATH=. python scripts/seed_products.py
"""

import asyncio
import os
import sys

# Ensure the project root is on PYTHONPATH when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.repositories import product_repo

PRODUCTS = [
    # ── Laptops ─────────────────────────────────────────────────────────────
    {
        "name": "QuantumBook Pro 16",
        "description": "Next-generation professional laptop with liquid cooling and quantum silicon CPU.",
        "category": "Laptops",
        "tags": ["quantum", "pro", "developer", "liquid-cooled", "laptop", "premium"],
        "price": 2499.99,
    },
    {
        "name": "AeroGlide UltraLight 13",
        "description": "Featherweight carbon fiber ultrabook with a 24-hour battery life and fanless design.",
        "category": "Laptops",
        "tags": ["ultrabook", "travel", "fanless", "carbon-fiber", "laptop", "lightweight"],
        "price": 1299.99,
    },
    {
        "name": "Nebula Horizon Gaming 17",
        "description": "Powerhouse gaming laptop featuring a holographic display and mechanical keyboard.",
        "category": "Laptops",
        "tags": ["gaming", "nebula", "holographic", "mechanical", "laptop", "rtx"],
        "price": 1899.99,
    },
    {
        "name": "PixelCraft Studio 15",
        "description": "Designed for creative professionals with 100% DCI-P3 OLED touch display.",
        "category": "Laptops",
        "tags": ["design", "studio", "creator", "oled", "touchscreen", "laptop"],
        "price": 1599.99,
    },
    {
        "name": "IronShield Business 14",
        "description": "MIL-SPEC rugged business laptop with a built-in privacy screen and biometric login.",
        "category": "Laptops",
        "tags": ["business", "rugged", "privacy", "biometric", "laptop", "secure"],
        "price": 1749.99,
    },
    # ── Phones ───────────────────────────────────────────────────────────────
    {
        "name": "Vortex Prime X",
        "description": "Premium smartphone with an under-display 200MP camera and modular rear panels.",
        "category": "Phones",
        "tags": ["smartphone", "vortex", "modular", "200mp", "premium", "phone"],
        "price": 999.99,
    },
    {
        "name": "Titan Rugged 5G",
        "description": "Unbreakable smartphone with thermal imaging, laser measure, and shockproof armor.",
        "category": "Phones",
        "tags": ["rugged", "outdoor", "thermal", "armored", "phone", "indestructible"],
        "price": 699.99,
    },
    {
        "name": "Nova Fold Flip",
        "description": "Ultra-thin flip smartphone featuring flexible glass and secondary cover display.",
        "category": "Phones",
        "tags": ["flip", "folding", "glass", "compact", "phone", "style"],
        "price": 1199.99,
    },
    {
        "name": "Zenith Eco Phone",
        "description": "100% biodegradable phone with circular design and user-repairable components.",
        "category": "Phones",
        "tags": ["eco", "green", "repairable", "biodegradable", "phone", "sustainable"],
        "price": 499.99,
    },
    {
        "name": "Pulse AI Phone",
        "description": "On-device AI phone with a dedicated neural processor and real-time translation.",
        "category": "Phones",
        "tags": ["ai", "neural", "translation", "on-device", "phone", "smart"],
        "price": 849.99,
    },
    # ── Accessories ──────────────────────────────────────────────────────────
    {
        "name": "Sonar ANC Earbuds",
        "description": "Active noise cancelling wireless earbuds with spatial audio and bone conduction.",
        "category": "Accessories",
        "tags": ["earbuds", "audio", "anc", "spatial", "wireless", "music"],
        "price": 199.99,
    },
    {
        "name": "OmniCharge Solar Hub",
        "description": "High-capacity 50,000mAh rugged power bank with built-in solar panels and folding stand.",
        "category": "Accessories",
        "tags": ["powerbank", "solar", "charger", "camping", "rugged"],
        "price": 89.99,
    },
    {
        "name": "HoloBeam Projector",
        "description": "Pocket-sized projector with 4K resolution and 360-degree laser rotation.",
        "category": "Accessories",
        "tags": ["projector", "video", "pocket", "laser", "home-theater"],
        "price": 299.99,
    },
    {
        "name": "ChronoFit Smart Ring",
        "description": "Sleek titanium smart ring tracking heart rate, sleep quality, and body temperature.",
        "category": "Accessories",
        "tags": ["ring", "fitness", "sleep", "wearable", "titanium"],
        "price": 249.99,
    },
    {
        "name": "MeshLink WiFi 7 Router",
        "description": "Tri-band WiFi 7 mesh router with AI traffic shaping and built-in VPN endpoint.",
        "category": "Accessories",
        "tags": ["wifi7", "router", "mesh", "networking", "vpn", "home"],
        "price": 349.99,
    },
]


async def seed() -> None:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"prepared_statement_cache_size": 0},
    )
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        existing = await product_repo.list_products(db)
        if existing:
            print(f"✅  Database already has {len(existing)} product(s). Skipping seed.")
            await engine.dispose()
            return

        print(f"🌱  Seeding {len(PRODUCTS)} products …")
        for p in PRODUCTS:
            await product_repo.create_product(
                db,
                name=p["name"],
                description=p["description"],
                category=p["category"],
                tags=p["tags"],
                price=p["price"],
            )
        print(f"✅  Successfully seeded {len(PRODUCTS)} products across Laptops, Phones, and Accessories.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
