from typing import Optional
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.redis import redis_client
from app.api.v1 import auth, chat, websocket, recommendations, products, admin
from app.core.middleware import RequestLoggingMiddleware
from app.core.config import settings
from loguru import logger

# Configure structured JSON logging for Loguru to stdout
logger.remove()
logger.add(sys.stdout, format="{message}", serialize=True)

# Configure Sentry Integration
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run DB seeding on startup
    await seed_products()
    yield

app = FastAPI(title="AI Support Engine", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

async def _run_seeding(db: AsyncSession):
    """Seed 12 default products across Laptops, Phones, and Accessories."""
    from app.repositories import product_repo
    logger.info("Database is empty. Seeding 12 default products across Laptops, Phones, and Accessories...")
    
    # Category: Laptops
    await product_repo.create_product(
        db,
        name="QuantumBook Pro 16",
        description="Next-generation professional laptop with liquid cooling and quantum silicon CPU.",
        category="Laptops",
        tags=["quantum", "pro", "developer", "liquid-cooled", "laptop", "premium"],
        price=2499.99
    )
    await product_repo.create_product(
        db,
        name="AeroGlide UltraLight 13",
        description="Featherweight carbon fiber ultrabook with a 24-hour battery life and fanless design.",
        category="Laptops",
        tags=["ultrabook", "travel", "fanless", "carbon-fiber", "laptop", "lightweight"],
        price=1299.99
    )
    await product_repo.create_product(
        db,
        name="Nebula Horizon Gaming 17",
        description="Powerhouse gaming laptop featuring a holographic display and mechanical keyboard.",
        category="Laptops",
        tags=["gaming", "nebula", "holographic", "mechanical", "laptop", "rtx"],
        price=1899.99
    )
    await product_repo.create_product(
        db,
        name="PixelCraft Studio 15",
        description="Designed specifically for creative designers with 100% DCI-P3 OLED touch display.",
        category="Laptops",
        tags=["design", "studio", "creator", "oled", "touchscreen", "laptop"],
        price=1599.99
    )
    
    # Category: Phones
    await product_repo.create_product(
        db,
        name="Vortex Prime X",
        description="Premium smartphone with an under-display 200MP camera and modular rear panels.",
        category="Phones",
        tags=["smartphone", "vortex", "modular", "200mp", "premium", "phone"],
        price=999.99
    )
    await product_repo.create_product(
        db,
        name="Titan Rugged 5G",
        description="Unbreakable smartphone with thermal imaging, laser measure, and shockproof armor.",
        category="Phones",
        tags=["rugged", "outdoor", "thermal", "armored", "phone", "indestructible"],
        price=699.99
    )
    await product_repo.create_product(
        db,
        name="Nova Fold Flip",
        description="Ultra-thin flip smartphone featuring flexible glass and secondary cover display.",
        category="Phones",
        tags=["flip", "folding", "glass", "compact", "phone", "style"],
        price=1199.99
    )
    await product_repo.create_product(
        db,
        name="Zenith Eco Phone",
        description="100% biodegradable phone with circular design and user-repairable components.",
        category="Phones",
        tags=["eco", "green", "repairable", "biodegradable", "phone", "sustainable"],
        price=499.99
    )
    
    # Category: Accessories
    await product_repo.create_product(
        db,
        name="Sonar ANC Earbuds",
        description="Active noise cancelling wireless earbuds with spatial audio and bone conduction.",
        category="Accessories",
        tags=["earbuds", "audio", "anc", "spatial", "wireless", "music"],
        price=199.99
    )
    await product_repo.create_product(
        db,
        name="OmniCharge Solar Hub",
        description="High-capacity 50,000mAh rugged power bank with built-in solar panels and folding stand.",
        category="Accessories",
        tags=["powerbank", "solar", "charger", "camping", "rugged"],
        price=89.99
    )
    await product_repo.create_product(
        db,
        name="HoloBeam Projector",
        description="Pocket-sized projector with 4K resolution and 360-degree laser rotation.",
        category="Accessories",
        tags=["projector", "video", "pocket", "laser", "home-theater"],
        price=299.99
    )
    await product_repo.create_product(
        db,
        name="ChronoFit Smart Ring",
        description="Sleek titanium smart ring tracking heart rate, sleep quality, and body temperature.",
        category="Accessories",
        tags=["ring", "fitness", "sleep", "wearable", "titanium"],
        price=249.99
    )
    logger.info("DB successfully seeded with 12 default products!")

async def seed_products(db: Optional[AsyncSession] = None):
    """Seed 12 beautiful products across categories if the products table is empty."""
    from app.core.database import AsyncSessionLocal
    from app.repositories import product_repo
    
    if db is None:
        async with AsyncSessionLocal() as session:
            existing_products = await product_repo.list_products(session)
            if not existing_products:
                await _run_seeding(session)
    else:
        existing_products = await product_repo.list_products(db)
        if not existing_products:
            await _run_seeding(db)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    # Test database connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    # Test Redis connectivity
    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"disconnected: {str(e)}"

    overall_status = "healthy"
    if db_status != "connected" or redis_status != "connected":
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "db": db_status,
        "redis": redis_status
    }
