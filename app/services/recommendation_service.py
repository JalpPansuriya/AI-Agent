import json
import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.models import Message
from app.repositories import product_repo
from app.services.ai_service import call_openai

async def get_recommendations(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> List[dict]:
    """
    Orchestrate generating contextual product recommendations based on recent chat history.
    """
    try:
        # 1. Load last 5 user messages from this session
        stmt = (
            select(Message)
            .where(Message.session_id == session_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        user_messages = list(result.scalars().all())
        user_messages.reverse()  # Keep chronological order
        
        user_contents = [m.content for m in user_messages]
        if not user_contents:
            # No user messages in history yet, return fallback recommendations
            return await product_repo.get_recent_products(db, limit=5)
            
        # 2. Build extraction prompt
        prompt = (
            "Extract the top 3 product categories, tags, or specific product names the user is interested in from these recent chat messages.\n"
            f"Messages:\n{json.dumps(user_contents)}\n\n"
            "Return ONLY a valid JSON object of the form: {\"interests\": [\"cat1\", \"cat2\", \"product_name\"]}"
        )
        
        # 3. Call OpenAI
        reply_content, _ = await call_openai([{"role": "user", "content": prompt}])
        
        # Clean reply in case of markdown wrappers (e.g. ```json ... ```)
        cleaned = reply_content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            
        # 4. Parse interests
        data = json.loads(cleaned)
        interests = data.get("interests", [])
        
        if interests:
            # 5. Query products table
            products = await product_repo.get_products_by_interests(db, interests, limit=5)
            if products:
                return products
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        
    # Fallback to recent products on empty results or exceptions
    return await product_repo.get_recent_products(db, limit=5)
