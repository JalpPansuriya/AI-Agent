import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin, RateLimiter
from app.models.models import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.repositories import product_repo

router = APIRouter(tags=["products"])

@router.get(
    "/products",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List all active products",
    description="Retrieves a list of active products, optionally filtered by category."
)
async def list_products(
    request: Request,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=30, group="products"))
):
    return await product_repo.list_products(db, category=category)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Creates a new product record. Restricted to administrators."
)
async def create_product(
    product_in: ProductCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    return await product_repo.create_product(
        db,
        name=product_in.name,
        description=product_in.description,
        category=product_in.category,
        tags=product_in.tags,
        price=product_in.price
    )


@router.put(
    "/products/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a product",
    description="Updates an existing product record. Restricted to administrators."
)
async def update_product(
    id: uuid.UUID,
    product_in: ProductUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    db_product = await product_repo.get_product_by_id(db, id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return await product_repo.update_product(db, db_product, product_in.model_dump(exclude_unset=True))


@router.delete(
    "/products/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete a product",
    description="Soft deletes a product by setting is_active=False. Restricted to administrators."
)
async def delete_product(
    id: uuid.UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    db_product = await product_repo.get_product_by_id(db, id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    await product_repo.update_product(db, db_product, {"is_active": False})
    return None
