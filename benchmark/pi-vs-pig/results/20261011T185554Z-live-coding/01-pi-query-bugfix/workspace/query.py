from urllib.parse import unquote_plus


def parse_query(query):
    """Parse a raw query string into decoded keys and ordered value lists."""
    if query.startswith('?'):
        query = query[1:]
    result = {}
    for field in query.split('&'):
        if not field:
            continue
        key, _, value = field.partition('=')
        key = unquote_plus(key)
        value = unquote_plus(value)
        result.setdefault(key, []).append(value)
    return result
