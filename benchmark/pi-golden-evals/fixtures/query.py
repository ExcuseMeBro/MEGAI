"""Parse application/x-www-form-urlencoded query pairs."""
from urllib.parse import unquote_plus


def parse_query(query: str) -> list[tuple[str, str]]:
    if query.startswith("?"):
        query = query[1:]
    if not query:
        return []
    pairs = []
    for piece in query.split("&"):
        if not piece or "=" not in piece:
            raise ValueError("invalid query pair")
        key, value = piece.split("=", 1)
        pairs.append((unquote_plus(key), unquote_plus(value)))
    return pairs
