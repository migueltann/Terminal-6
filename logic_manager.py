"""Checks the AI recommendations against the user's requirements."""

def _normalise(value):
    """Make text easier to compare."""
    return str(value).strip().lower()


def _contains_term(item, term):
    """Check whether a user keyword appears in the recommendation."""

    term = _normalise(term)

    if not term:
        return False

    searchable = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("category", "")),
            str(item.get("description", "")),
            str(item.get("location", "")),
            " ".join(str(tag) for tag in item.get("tags", [])),
        ]
    ).lower()

    return term in searchable