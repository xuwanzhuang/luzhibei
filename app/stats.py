from . import config


def category_of(label: str) -> str:
    low = (label or "").strip().lower()
    if low in config.FIRE_LABELS:
        return "fire"
    if low in config.SMOKE_LABELS:
        return "smoke"
    return "other"


def _empty_counts():
    return {"fire": 0, "smoke": 0, "other": 0, "total": 0}


def counts_from_detections(detections):
    counts = _empty_counts()
    for d in detections:
        cat = d.get("category", "other")
        if cat not in counts:
            cat = "other"
        counts[cat] += 1
        counts["total"] += 1
    return counts


def risk_level(fire, smoke):
    if fire > 0:
        return config.RISK_HIGH
    if smoke > 0:
        return config.RISK_MEDIUM
    return config.RISK_NORMAL


def compute_single(detections):
    counts = counts_from_detections(detections)
    return {"counts": counts, "risk": risk_level(counts["fire"], counts["smoke"])}


class TaskStats:
    def __init__(self):
        self.frames = 0
        self.total = _empty_counts()
        self.peak = _empty_counts()

    def accumulate(self, detections):
        counts = counts_from_detections(detections)
        self.frames += 1
        for key in self.total:
            self.total[key] += counts[key]
            self.peak[key] = max(self.peak[key], counts[key])

    def snapshot(self):
        return {
            "frames": self.frames,
            "total": dict(self.total),
            "peak": dict(self.peak),
            "risk": risk_level(self.total["fire"], self.total["smoke"]),
        }
