from fastapi import APIRouter, Body, HTTPException
from Modules import Reaction
from firebase_admin import db

router = APIRouter(
    prefix="/reaction",
    tags=["reactions"]
)


# -------------------- REACTION METHODS --------------------
@router.post("", response_model=Reaction)
def create_reaction(reaction: Reaction = Body(...)):
    ref = db.reference(f"Reactions")
    new_ref = ref.push()
    new_id = new_ref.key

    reaction_dict = reaction.model_dump()
    reaction_dict["id"] = new_id
    new_ref.set(reaction_dict)
    comment_to_reaction(reaction["comment_id"], new_id)
    return reaction_dict

def comment_to_reaction(comment_id: str, reaction_id: str):
    ref = db.reference(f"CommentToReactions/{comment_id}")
    ref.update({reaction_id: True})
    return "Successful mapping Comment to Reactions."


@router.get("/{reaction_id}", response_model=Reaction)
def get_reaction(reaction_id: str):
    ref = db.reference(f"Reactions/{reaction_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Reaction not found")
    data["id"] = reaction_id
    return Reaction(**data)


@router.delete("/{reaction_id}")
def delete_reaction(reaction_id: str):
    ref = db.reference(f"Reactions/{reaction_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Reaction not found")
    ref.delete()
    remove_reaction_map(reaction_id)
    return {"message": f"Reaction {reaction_id} deleted successfully"}


def remove_reaction_map(reaction_id: str):
    ref = db.reference(f"CommentToReactions/{reaction_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Reaction not found in Comment to Reactions mapping")
    ref.delete()


def get_all_reactions_for(comment_id: str):
    ref = db.reference(f"CommentToReactions/{comment_id}")
    data = ref.get()
    all_reactions = []
    for reaction_id in data:
        try: 
            all_reactions.append(get_reaction(reaction_id))
        except HTTPException:
            print("Reaction", reaction_id, "not found in mapping. Must have be deleted earlier.")

    print(all_reactions)

    return all_reactions