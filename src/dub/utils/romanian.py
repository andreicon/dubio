DIACRITICS = set("ăâîșțĂÂÎȘȚ")


def has_diacritics(s: str) -> bool:
    return any(ch in DIACRITICS for ch in s)


def assert_diacritics_preserved(before: str, after: str) -> None:
    missing = {c for c in before if c in DIACRITICS} - set(after)
    if missing:
        raise AssertionError(f"Diacritics stripped: {missing}")
