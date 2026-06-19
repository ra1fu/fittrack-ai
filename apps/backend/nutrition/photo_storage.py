import uuid
from pathlib import Path

from django.core.files.storage import default_storage


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def build_food_photo_key(*, user_id, content_type: str) -> str:
    extension = CONTENT_TYPE_EXTENSIONS[content_type]

    return str(
        Path("nutrition")
        / "photo-recognitions"
        / str(user_id)
        / f"{uuid.uuid4()}{extension}"
    )


def save_food_photo(*, image_file, image_key: str) -> str:
    return default_storage.save(image_key, image_file)


def delete_food_photo(*, image_key: str) -> None:
    if default_storage.exists(image_key):
        default_storage.delete(image_key)
