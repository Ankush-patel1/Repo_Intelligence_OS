from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_non_empty(value: str | None) -> bool:
    if value is None:
        return False
    return len(value.strip()) > 0
