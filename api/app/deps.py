from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.db import get_supabase


def get_owned_home(
    home_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    response = (
        get_supabase()
        .table("homes")
        .select("*")
        .eq("id", home_id)
        .eq("user_id", user["id"])
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home not found",
        )
    return response.data[0]


def get_owned_appliance(
    appliance_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    response = (
        get_supabase()
        .table("home_appliances")
        .select("*")
        .eq("id", appliance_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found",
        )
    appliance = response.data[0]
    get_owned_home(appliance["home_id"], user)
    return appliance


OwnedHome = Annotated[dict[str, Any], Depends(get_owned_home)]
OwnedAppliance = Annotated[dict[str, Any], Depends(get_owned_appliance)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
