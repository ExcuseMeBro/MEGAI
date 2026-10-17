from urllib.parse import unquote_plus


def parse_query(query):
    """Decode query fields, collecting values for each key in encounter order."""
    result = {}
    if query.startswith('?'):
        query = query[1:]
    for field in query.split('&'):
        if not field:
            continue
        key, _, value = field.partition('=')
        key = unquote_plus(key)
        value = unquote_plus(value)
        result.setdefault(key, []).append(value)
    return result
