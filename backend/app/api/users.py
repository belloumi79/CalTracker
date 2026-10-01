"""Private profile, export, and deletion endpoints."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, Database
from app.schemas.auth import MessageResponse
from app.schemas.user import UserProfileRead, UserProfileUpdate
from app.services.meals import list_meals, meal_to_dict

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileRead)
def get_me(user: CurrentUser):
    return user


@router.put("/me", response_model=UserProfileRead)
def update_me(payload: UserProfileUpdate, user: CurrentUser, db: Database):
    list_fields = {
        "goals",
        "dietary_preferences",
        "allergies",
        "intolerances",
        "favorite_foods",
        "avoid_foods",
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "display_name" and value is None:
            continue  # The database column is intentionally non-nullable.
        if field in list_fields and value is None:
            value = []  # null is a convenient way to clear an optional list.
        setattr(user, field, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/export")
def export_me(user: CurrentUser, db: Database):
    """Return an account-owned JSON export for portability and deletion workflows."""

    meals = list_meals(db, user)
    return {
        "profile": UserProfileRead.model_validate(user).model_dump(mode="json"),
        "meals": [meal_to_dict(meal) for meal in meals],
        "export_note": "Export généré à la demande; les valeurs nutritionnelles restent des estimations si indiqué.",
    }


@router.delete("/me", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_me(user: CurrentUser, db: Database):
    db.delete(user)
    db.commit()
    return {"message": "Compte et données associées supprimés."}
