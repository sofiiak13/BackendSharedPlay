from fastapi import APIRouter, Body, Query, HTTPException
from Modules import Comment
from firebase_admin import db

import datetime

router = APIRouter(
    prefix="/comment",
    tags=["comments"]
)

# -------------------- COMMENT METHODS --------------------
@router.post("", response_model=Comment)
def create_comment(comment: Comment = Body(...)):
    ref = db.reference(f"Comments")
    new_ref = ref.push()
    new_id = new_ref.key

    comment_dict = comment.model_dump()
    comment_dict["id"] = new_id
    comment_dict["date_created"] = datetime.datetime.now().isoformat()

    new_ref.set(comment_dict)
    song_to_comment(comment_dict["song_id"], new_id)
    return comment_dict


def song_to_comment(song_id: str, comment_id: str):
    ref = db.reference(f"SongToComments/{song_id}")
    ref.update({comment_id: True})
    return "Successful mapping Song to Comment."


@router.get("/{comment_id}", response_model=Comment)
def get_comment(comment_id: str):
    ref = db.reference(f"Comments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found")
    data["id"] = comment_id
    return Comment(**data)

@router.patch("/{comment_id}", response_model=Comment)
def update_comment(
    comment_id: str, 
    updated_text: str = Body(...)
    ):
    com_dict = get_comment(comment_id).model_dump()
    com_dict["text"] = comment_id
    com_dict["edited"] = updated_text
    ref = db.reference(f"Comments/{comment_id}")
    existing = ref.get()

    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    ref.update(com_dict)
    
    updated_data = ref.get()
    return Comment(**updated_data)

@router.delete("/{comment_id}")
def delete_comment(comment_id: str):
    ref = db.reference(f"Comments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found")
    ref.delete()
    remove_comment_map(comment_id)
    return {"message": f"Comment {comment_id} deleted successfully"}

def remove_comment_map(comment_id: str):
    ref = db.reference(f"SongToComments/{comment_id}")
    data = ref.get()
    if not data:
        raise HTTPException(status_code=404, detail="Comment not found in Song to Comments mapping")
    ref.delete()


@router.get("/{song_id}/comments")
def get_all_comments_for(song_id: str):
    ref = db.reference(f"SongToComments/{song_id}")
    data = ref.get()
    all_comments = []
    for comment_id in data:
        try: 
            all_comments.append(get_comment(comment_id))
        except HTTPException:
            print("Comment", comment_id, "not found in mapping. Must have be deleted earlier.")

    print(all_comments)
    ordered_comments = build_threaded_comments(all_comments)

    return ordered_comments


@router.get("/{song_id}/comment/latest")
def get_most_recent_comment_of(song_id: str):
    all_comments = get_all_comments_for(song_id)

    if not all_comments:
        raise HTTPException(status_code=404, detail="No comments found")
    
    latest = max(all_comments, key=lambda cnomment: cnomment.date_created)
    return latest


def build_threaded_comments(comments):
    '''Returns ordered list of comments with a new value of depth added. 
    Depth of each comment is calculated using DFS algorithm'''

    # build {parent: list of children}
    children = {}
    for c in comments:
        parent = c.prev

        if parent is None:
            # This is a top-level comment
            children.setdefault(None, []).append(c)
        else:
            # This is a reply to another comment
            children.setdefault(parent, []).append(c)

    # sort children by date
    for child_list in children.values():
        child_list.sort(key=lambda child: child.date_created)

    print()
    print(children)
    ordered = []

    def dfs(comment, depth):
        comment.depth = depth
        ordered.append(comment)

        # termination condition
        children_of_comment = children.get(comment.id)

        if not children_of_comment:     # None or empty list
            return                      # stop recursion here

        # otherwise process children
        for child in children_of_comment:
            dfs(child, depth + 1)


    for root in children.get(None, []):
        dfs(root, depth=0)

    return ordered
