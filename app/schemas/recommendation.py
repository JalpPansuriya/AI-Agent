from typing import List
from pydantic import BaseModel
from app.schemas.product import ProductResponse

class RecommendationResponse(BaseModel):
    products: List[ProductResponse]
