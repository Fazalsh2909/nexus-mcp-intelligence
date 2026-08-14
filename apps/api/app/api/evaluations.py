from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import User
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/")
async def list_evaluations(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    return {"evaluations": [], "message": "Evaluation suite ready"}


@router.post("/run")
async def run_evaluation(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    return {"status": "started", "message": "Evaluation run initiated"}
