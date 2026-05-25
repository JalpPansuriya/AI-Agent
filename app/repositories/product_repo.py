import uuid
from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Product

async def get_products_by_interests(db: AsyncSession, interests: List[str], limit: int = 5) -> List[Product]:
    """
    Retrieve active products matching interest tags (using overlap) or category matching.
    Query: WHERE is_active = True AND (tags && ARRAY[interests] OR category = ANY(interests))
    """
    if not interests:
        return []
        
    stmt = (
        select(Product)
        .where(
            Product.is_active == True,
            or_(
                Product.tags.overlap(interests),
                Product.category.in_(interests)
            )
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_recent_products(db: AsyncSession, limit: int = 5) -> List[Product]:
    """Retrieve the most recent active products, sorted by creation date descending."""
    stmt = (
        select(Product)
        .where(Product.is_active == True)
        .order_by(Product.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_product_by_id(db: AsyncSession, product_id: uuid.UUID) -> Optional[Product]:
    """Retrieve a product by its UUID (including inactive ones for admin/soft-delete lookup)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()

async def list_products(db: AsyncSession, category: Optional[str] = None) -> List[Product]:
    """List active products, optionally filtered by category."""
    stmt = select(Product).where(Product.is_active == True)
    if category:
        stmt = stmt.where(Product.category.ilike(category))
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def create_product(db: AsyncSession, name: str, description: str, category: str, tags: List[str], price: float) -> Product:
    """Create a new product record."""
    product = Product(
        name=name,
        description=description,
        category=category,
        tags=tags,
        price=price,
        is_active=True
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

async def update_product(db: AsyncSession, db_product: Product, update_data: dict) -> Product:
    """Update a product with provided data dictionary."""
    for key, value in update_data.items():
        if value is not None:
            setattr(db_product, key, value)
    await db.commit()
    await db.refresh(db_product)
    return db_product
