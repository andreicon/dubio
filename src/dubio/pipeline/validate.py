from __future__ import annotations

import json

from dubio.validation.duration import check_duration
from dubio.validation.language import check_language
from dubio.validation.loudness import check_loudness
from dubio.validation.overlap import check_overlaps
from dubio.validation.peak import check_peak
from dubio.validation.score import composite_score
from dubio.validation.text import check_text


def _status_by_name(results, name):
    for result in results:
        if result.name == name:
            return result.status
    return None


def validate_utterance(m, utt, asr, config) -> dict:
    results = [
        check_duration(utt, config.timing),
        check_loudness(utt, config.audio.target_lufs),
        check_peak(utt, config.audio.true_peak_db),
    ]
    if utt.tts.file:
        results.append(check_language(utt, asr, expected="ro"))
        results.append(check_text(utt, asr))

    score, raw = composite_score(results, weights=None)
    utt.validation.duration = _status_by_name(results, "duration")
    utt.validation.loudness = _status_by_name(results, "loudness")
    utt.validation.language = _status_by_name(results, "language")
    utt.validation.transcription = _status_by_name(results, "text")
    utt.validation.score = score
    utt.validation.measurements["checks"] = {result.name: result.detail for result in results}

    return {"id": utt.id, "score": score, "checks": raw}


def validate_project(paths, asr, config, utterance_id: str | None = None) -> dict:
    from dubio.project.manifest import Manifest

    manifest = Manifest.load(paths.manifest)
    utterances = [manifest.get_utterance(utterance_id)] if utterance_id else manifest.utterances
    reports = [validate_utterance(manifest, utterance, asr, config) for utterance in utterances]

    overlap_results = check_overlaps(manifest.utterances)
    overlaps = [check.detail for check in overlap_results]
    for utterance in manifest.utterances:
        statuses = [
            result.status
            for result in overlap_results
            if result.detail.get("a") == utterance.id or result.detail.get("b") == utterance.id
        ]
        if "fail" in statuses:
            utterance.validation.overlap = "fail"
        elif "warning" in statuses:
            utterance.validation.overlap = "warning"
        else:
            utterance.validation.overlap = "pass"

    report = {"project": manifest.project.id, "utterances": reports, "overlaps": overlaps}
    paths.validation_dir.mkdir(parents=True, exist_ok=True)
    (paths.validation_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest.save(paths.manifest)
    return report
