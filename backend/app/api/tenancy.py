from fastapi import APIRouter

from app.tenancy.demo_users import list_demo_users

router = APIRouter()


@router.get("/demo/users")
def get_demo_users() -> dict:
    return {"users": list_demo_users()}
