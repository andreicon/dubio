from dubio.utils.cache import Cache, tts_cache_key
from dubio.utils.hashing import stable_hash


def test_text_change_changes_tts_cache_key():
    base = (
        "fish-s2-pro",
        "s2-pro",
        "voice_bugs",
        "ro",
        "Ce faci?",
        {},
        {"pitch": 2, "speaking_rate": 1.0},
    )
    changed_text = (
        "fish-s2-pro",
        "s2-pro",
        "voice_bugs",
        "ro",
        "Ce naiba faci?",
        {},
        {"pitch": 2, "speaking_rate": 1.0},
    )

    assert tts_cache_key(*base) != tts_cache_key(*changed_text)


def test_unrelated_mapping_order_does_not_change_stable_hash():
    first = stable_hash("a", {"b": 1, "a": 2})
    second = stable_hash("a", {"a": 2, "b": 1})

    assert first == second


def test_cache_path_for_creates_directory_and_returns_path(tmp_path):
    cache = Cache(tmp_path / "tts-cache")

    path = cache.path_for("abc123", "wav")

    assert path == tmp_path / "tts-cache" / "abc123.wav"
    assert path.parent.exists()
    assert cache.has("abc123", "wav") is False
