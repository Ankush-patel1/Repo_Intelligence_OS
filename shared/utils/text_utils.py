import re


def truncate_text(text: str, max_length: int = 1000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def slugify(text: str) -> str:
    text = text.lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text
