from dubio.config import TimingCfg
from dubio.pipeline.timing import duration_status, find_overlaps
from dubio.project.manifest import SourceSpan, Utterance


def _u(uid, start, end):
    return Utterance(id=uid, speaker="s", source=SourceSpan(text="x", start=start, end=end))


def test_overlap_detected():
    overlaps = find_overlaps([_u("utt_001", 10.0, 13.0), _u("utt_002", 12.5, 14.2)])

    assert overlaps[0].seconds == 0.5 and overlaps[0].a_id == "utt_001"


def test_duration_thresholds():
    cfg = TimingCfg(max_duration_ratio=1.15, warning_duration_ratio=1.05)

    assert duration_status(2.80, 2.80, cfg) == "pass"
    assert duration_status(2.80, 2.80 * 1.10, cfg) == "warning"
    assert duration_status(2.80, 2.80 * 1.20, cfg) == "fail"


def test_nested_overlap_detected():
    overlaps = find_overlaps([
        _u("utt_001", 0.0, 10.0),
        _u("utt_002", 1.0, 2.0),
        _u("utt_003", 3.0, 4.0),
    ])

    assert [(ov.a_id, ov.b_id) for ov in overlaps] == [
        ("utt_001", "utt_002"),
        ("utt_001", "utt_003"),
    ]
