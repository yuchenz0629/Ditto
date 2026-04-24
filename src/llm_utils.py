import re
from typing import Literal
import anthropic
from anthropic.types import Message, TextBlock

LayoutName = Literal[
    "1-image", "2-image", "3-image", "4-image",
    "2-image-v2", "3-image-v2", "4-image-v2",
]

LAYOUT_BY_COUNT: dict[int, LayoutName] = {
    1: "1-image",
    2: "2-image",
    3: "3-image",
    4: "4-image",
}


def extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        return fenced.group(1).strip()
    obj = re.search(r"\{[\s\S]*\}", text)
    if obj:
        return obj.group().strip()
    return text.strip()


def response_text(resp: Message) -> str:
    return "\n".join(
        block.text
        for block in resp.content
        if isinstance(block, TextBlock)
    )
