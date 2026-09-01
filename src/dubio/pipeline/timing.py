from dataclasses import dataclass


@dataclass
class Overlap:
    a_id: str
    b_id: str
    seconds: float


def target_duration(utt) -> float:
    return round(utt.source.end - utt.source.start, 3)


def find_overlaps(utterances) -> list[Overlap]:
    ordered = sorted(utterances, key=lambda utt: utt.source.start)
    overlaps = []
    for index, a in enumerate(ordered):
        for b in ordered[index + 1 :]:
            if b.source.start >= a.source.end:
                break
            seconds = round(min(a.source.end, b.source.end) - b.source.start, 3)
            if seconds > 0 and not (a.overlap_allowed and b.overlap_allowed):
                overlaps.append(Overlap(a.id, b.id, seconds))
    return overlaps


def duration_status(target: float, generated: float, cfg) -> str:
    if generated <= target * cfg.warning_duration_ratio:
        return "pass"
    if generated <= target * cfg.max_duration_ratio:
        return "warning"
    return "fail"
