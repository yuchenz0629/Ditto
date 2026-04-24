from __future__ import annotations
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, field_validator

class BackgroundMeta(BaseModel):
    name: str
    file: str
    gender: list[str]
    vibe: str
    color_tone: str

class ParsedInput(BaseModel):
    user_id: str
    user_dir: str
    name: str
    gender: str
    ethnicity: str
    image_paths: list[str]
    backgrounds: list[BackgroundMeta]

class SelectedImage(BaseModel):
    index: int
    filename: str
    role: Literal["hero", "body", "lifestyle", "group"]
    position: int          # 1 = lowest importance; hero = highest

class RejectedImage(BaseModel):
    index: int
    filename: str
    reason: str

class AvailableImage(BaseModel):
    index: int
    filename: str

class AnalysisResult(BaseModel):
    selected_images: list[SelectedImage]
    rejected_images: list[RejectedImage]
    background: str
    layout: Literal["1-image", "2-image", "3-image", "4-image"]
    @field_validator("layout", mode="after")
    @classmethod
    def derive_layout_from_count(cls, v, info):
        selected = info.data.get("selected_images", [])
        return f"{len(selected)}-image"

class PosterState(BaseModel):
    user: str
    user_dir: str
    name: str
    gender: str
    selected_images: list[SelectedImage]
    available_images: list[AvailableImage]
    rejected_images: list[RejectedImage]
    background: str
    layout: Literal[
        "1-image", "2-image", "3-image", "4-image",
        "2-image-v2", "3-image-v2", "4-image-v2",
    ]
    hero_scale: float = Field(default=1.0, ge=0.7, le=1.3)

# Edit commands
class SwapImageCommand(BaseModel):
    action: Literal["swap_image"]
    target_position: int
    new_image_index: int
    reason: str

class RemoveImageCommand(BaseModel):
    action: Literal["remove_image"]
    target_position: int
    reason: str

class ChangeBackgroundCommand(BaseModel):
    action: Literal["change_background"]
    new_background: str
    reason: str

class AdjustLayoutCommand(BaseModel):
    action: Literal["adjust_layout"]
    new_layout: Literal[
        "1-image", 
        "2-image", 
        "3-image", 
        "4-image",
        "2-image-v2", 
        "3-image-v2", 
        "4-image-v2",
    ]
    reason: str

class ResizePhotoCommand(BaseModel):
    action: Literal["resize_photo"]
    scale: float = Field(gt=0, le=2.0)   # 1.1 = 10% bigger, 0.9 = 10% smaller
    reason: str

EditCommand = Annotated[
    Union[SwapImageCommand, RemoveImageCommand, ChangeBackgroundCommand, AdjustLayoutCommand, ResizePhotoCommand],
    Field(discriminator="action"),
]
