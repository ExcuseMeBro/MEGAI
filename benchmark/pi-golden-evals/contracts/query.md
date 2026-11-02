# Public task: query parser

Implement `query.parse_query(query: str) -> list[tuple[str, str]]` with Python's
standard library only. Input is an application/x-www-form-urlencoded query string
with an optional single leading `?`. Empty input, including `?`, returns `[]`.
Split on literal `&`, then the first literal `=`; retain duplicate keys, order,
and empty keys/values. Reject an empty pair or a pair without `=` with
`ValueError`. Decode `+` as a space and `%HH` escapes into strict UTF-8, in
both keys and values. Reject any invalid percent escape or invalid UTF-8 with
`ValueError` (never replace malformed input). Do not mutate input, change the
function name or add dependencies.

Examples: `a=1&a=2` → `[("a", "1"), ("a", "2")]`;
`?x=a+b&y=%C3%A9` → `[("x", "a b"), ("y", "é")]`.
