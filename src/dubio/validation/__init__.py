from dataclasses import dataclass, field


@dataclass
class CheckResult:
    name: str
    status: str
    score: float
    detail: dict = field(default_factory=dict)
