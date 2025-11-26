from fastapi import APIRouter, Body, HTTPException
from Modules import User, UserUpdate
from firebase_admin import db

import datetime

router = APIRouter(
    prefix="/user",
    tags=["users"]
)

# -------------------- USER METHODS --------------------
@router.post("", response_model=User)
def create_user(user: User = Body(...)):
    ref = db.reference("Users")

    # Generate a unique push key using firebase
    new_ref = ref.push()

    # Add the ID into the user object
    user_dict = user.model_dump()   # Pydantic v2
    user_dict["date_joined"] = datetime.datetime.now().isoformat()

    new_ref.set(user_dict)
    return user_dict


@router.get("/{user_id}", response_model=User)
def get_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**data)


@router.patch("/{user_id}", response_model=User)
def patch_user(user_id: str, update: UserUpdate = Body(...)):
    # Only include fields the client actually sent
    update_dict = update.model_dump(exclude_unset=True)

    ref = db.reference(f"Users/{user_id}")
    existing = ref.get()
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "friends" in update_dict and update_dict["friends"]:
        existing_friends = existing.get("friends", [])
        new_friends = update_dict["friends"]
        update_dict["friends"] = list(set(existing_friends + new_friends))

    update_dict["id"] = user_id

    # Update only the provided fields
    ref.update(update_dict)

    updated_data = ref.get()
    return User(**updated_data)


def remove_us_map(user_id: str):
    ref = db.reference(f"UserToPlaylists/{user_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="User not found in User to Playlist mapping")
    ref.delete()


@router.delete("/{user_id}")
def delete_user(user_id: str):
    ref = db.reference(f"Users/{user_id}")

    # Fetch the user first to see if it exists
    data = ref.get()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = ref.delete()
    return {"message": f"User {user_id} deleted successfully"}


# add/remove friend

# add/remove editor