from fastapi import APIRouter, HTTPException, Query

from app.deps import AuthenticatedUser
from app.schemas import ALLOWED_TYPES
from app.services.appliances import get_catalog
from app.services.catalog import search, types_info

router = APIRouter(prefix="/catalog", tags=["catalog"])
TYPE_LABELS = {
    "ac": "Air conditioner",
    "ceiling_fan": "Ceiling fan",
    "pedestal_fan": "Pedestal fan",
    "exhaust_fan": "Exhaust fan",
    "air_cooler": "Air cooler",
    "deep_freezer": "Deep freezer",
    "electric_oven": "Electric oven",
    "water_dispenser": "Water dispenser",
    "electric_kettle": "Electric kettle",
    "washing_machine": "Washing machine",
    "water_pump": "Water pump",
    "desktop_pc": "Desktop computer",
    "led_bulb": "LED bulb",
    "tube_light": "Tube light",
    "phone_charger": "Phone charger",
    "vacuum_cleaner": "Vacuum cleaner",
}


@router.get("/search")
def catalog_search(
    user: AuthenticatedUser,
    q: str = Query(default="", max_length=100),
    type: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    if type is not None and type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported appliance type")
    return search(get_catalog(), q=q, appliance_type=type, limit=limit)


@router.get("/types")
def catalog_types(user: AuthenticatedUser) -> list[dict]:
    return [
        {
            **item,
            "label": TYPE_LABELS.get(
                item["type"], item["type"].replace("_", " ").title()
            ),
        }
        for item in types_info(get_catalog())
    ]
