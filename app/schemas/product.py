import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default=[])
    price: float = Field(..., gt=0.0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    tags: Optional[List[str]] = None
    price: Optional[float] = Field(None, gt=0.0)
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: uuid.UUID
    is_active: bool

    model_config = {
        "from_attributes": True
    }
