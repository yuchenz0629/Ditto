import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps

BORDER_PX = 10

def _get_haar_cascade_path() -> str:
    cv2_data = getattr(cv2, "data", None)
    if cv2_data is None:
        raise RuntimeError(
            "OpenCV cv2.data is unavailable. Make sure opencv-python is installed."
        )
    haarcascades = getattr(cv2_data, "haarcascades", None)
    if haarcascades is None:
        raise RuntimeError(
            "OpenCV haarcascade path is unavailable. Make sure opencv-python is installed."
        )

    return haarcascades + "haarcascade_frontalface_default.xml"

_face_cascade = cv2.CascadeClassifier(_get_haar_cascade_path())


# Load image, smart-crop to a face-centered region, resize to fit within slot_w * slot_h 
# Maintains the original aspect ratio, add white border, rotate, Returns RGBA PIL Image ready to paste onto the background
def prepare_photo(image_path: Path, slot_w: int, slot_h: int, angle: float) -> Image.Image:
    img = Image.open(image_path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img = _smart_crop(img, slot_w, slot_h)
    img = ImageOps.expand(img, border=BORDER_PX, fill="white")
    img = img.convert("RGBA")
    img = img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    return img


# Crop with respect to the position of the face so that the face and the body are noticeable after the cropped image
def _smart_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    src_ratio = src_w / src_h

    face_cx, face_cy, face_fw, face_fh = _detect_face(img)

    if (
        face_cx is not None
        and face_cy is not None
        and face_fw is not None
        and face_fh is not None
    ):
        crop_h = min(int(face_fh * 5), src_h)
        crop_h = max(crop_h, int(face_fh * 2))

        crop_w = min(int(crop_h * src_ratio), src_w)
        crop_h = min(int(crop_w / src_ratio), src_h)

        cx = face_cx
        cy = face_cy + int(crop_h * 0.25)
    else:
        crop_w = src_w
        crop_h = min(src_h, int(src_w * 1.5))
        cx = src_w // 2
        cy = src_h // 2

    left = max(0, min(cx - crop_w // 2, src_w - crop_w))
    top = max(0, min(cy - crop_h // 2, src_h - crop_h))

    cropped = img.crop((left, top, left + crop_w, top + crop_h))

    scale = min(target_w / cropped.width, target_h / cropped.height)
    new_w = max(1, int(cropped.width * scale))
    new_h = max(1, int(cropped.height * scale))

    return cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)


"""
Return (cx, cy, face_w, face_h) of the best detected face, or (None, None, None, None) if there is none.

Filtering rules applied in order:
1. Face center must be in the upper 55% of the image to reject those in awkward angles.
2. Face height must be >= 4% to reject too small faces.
3. Face center must be within 15-85% of image width to reject edge other false positives.

Select the largest valid face, then the topmost face.
"""
def _detect_face(img: Image.Image) -> tuple[int | None, int | None, int | None, int | None]:
    gray = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=5, minSize=(30, 30)
    )
    if not len(faces):
        return None, None, None, None
    img_h = img.height
    img_w = img.width
    valid = [
        (x, y, w, h) for x, y, w, h in faces
        if (y + h // 2) < img_h * 0.55
        and h >= img_h * 0.04
        and img_w * 0.15 <= (x + w // 2) <= img_w * 0.85
    ]
    if not valid:
        return None, None, None, None
    by_area = sorted(valid, key=lambda f: f[2] * f[3], reverse=True)
    if by_area[0][3] >= img_h * 0.10:
        x, y, w, h = by_area[0]
    else:
        x, y, w, h = min(valid, key=lambda f: f[1] + f[3] // 2)
    return x + w // 2, y + h // 2, w, h