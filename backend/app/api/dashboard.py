from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary() -> dict:
    return {
        "total_revenue": 0,
        "total_orders": 0,
        "average_order_value": 0,
        "message": "Dashboard skeleton is alive",
    }