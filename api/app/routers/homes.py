from fastapi import APIRouter, HTTPException, status

from app.db import get_supabase
from app.deps import AuthenticatedUser, OwnedHome
from app.schemas import HomeIn, HomeOut, HomePatch

router = APIRouter(prefix="/homes", tags=["homes"])


@router.get("", response_model=list[HomeOut])
def list_homes(user: AuthenticatedUser) -> list[dict]:
    client = get_supabase()
    response = (
        client.table("homes")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    homes = response.data or []
    if not homes:
        return []
    appliance_response = (
        client.table("home_appliances")
        .select("home_id")
        .in_("home_id", [home["id"] for home in homes])
        .execute()
    )
    counts: dict[str, int] = {}
    for appliance in appliance_response.data or []:
        counts[appliance["home_id"]] = counts.get(appliance["home_id"], 0) + 1
    return [{**home, "appliance_count": counts.get(home["id"], 0)} for home in homes]


@router.post("", response_model=HomeOut, status_code=status.HTTP_201_CREATED)
def create_home(payload: HomeIn, user: AuthenticatedUser) -> dict:
    response = (
        get_supabase()
        .table("homes")
        .insert({**payload.model_dump(), "user_id": user["id"]})
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Home could not be created")
    return {**response.data[0], "appliance_count": 0}


@router.get("/{home_id}", response_model=HomeOut)
def get_home(home: OwnedHome) -> dict:
    return {**home, "appliance_count": _appliance_count(home["id"])}


@router.patch("/{home_id}", response_model=HomeOut)
def patch_home(home: OwnedHome, payload: HomePatch) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is None:
        raise HTTPException(status_code=422, detail="Home name cannot be empty")
    if updates:
        response = (
            get_supabase()
            .table("homes")
            .update(updates)
            .eq("id", home["id"])
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Home not found")
        home = response.data[0]
    return {**home, "appliance_count": _appliance_count(home["id"])}


@router.delete("/{home_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_home(home: OwnedHome) -> None:
    get_supabase().table("homes").delete().eq("id", home["id"]).execute()


def _appliance_count(home_id: str) -> int:
    response = (
        get_supabase()
        .table("home_appliances")
        .select("id")
        .eq("home_id", home_id)
        .execute()
    )
    return len(response.data or [])
