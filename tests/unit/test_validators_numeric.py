from dubio.config import TimingCfg
from dubio.project.manifest import SourceSpan, TTSInfo, Utterance, Validation
from dubio.validation.duration import check_duration
from dubio.validation.loudness import check_loudness
from dubio.validation.overlap import check_overlaps
from dubio.validation.peak import check_peak


def _u(uid, s, e, dur=None, allow=False):
    u = Utterance(id=uid, speaker="s", source=SourceSpan(text="x", start=s, end=e))
    u.tts = TTSInfo(duration=dur if dur is not None else e - s)
    u.overlap_allowed = allow
    return u


def test_duration_pass():
    assert check_duration(_u("u", 0, 2.8, 2.8), TimingCfg()).status == "pass"


def test_overlap_flags_unmarked_only():
    res = check_overlaps([_u("utt_001", 10, 13), _u("utt_002", 12.5, 14.2)])

    assert len(res) == 1
    assert res[0].status in ("warning", "fail")
    assert res[0].detail == {"a": "utt_001", "b": "utt_002", "seconds": 0.5}


def test_overlap_respects_overlap_allowed():
    res = check_overlaps([_u("utt_001", 10, 13, allow=True), _u("utt_002", 12.5, 14.2, allow=True)])

    assert res == []


def test_loudness_within_tolerance():
    u = _u("u", 0, 1)
    u.validation = Validation(measurements={"loudness": {"integrated_lufs": -16.4}})

    assert check_loudness(u, target_lufs=-16.0, tol=2.0).status == "pass"


def test_peak_fail_when_hot():
    u = _u("u", 0, 1)
    u.validation = Validation(measurements={"loudness": {"true_peak_db": -0.2}})

    assert check_peak(u, ceiling_db=-1.0).status == "fail"
