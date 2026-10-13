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


def by_label_from_detections(detections):
    result = {}
    for d in detections:
        label = d.get("label")
        if not label:
            continue
        result[label] = result.get(label, 0) + 1
    return result


def alerts_from(by_label):
    alerts = []
    for label, count in by_label.items():
        level = config.ALERT_RULES.get(label)
        if count > 0 and level:
            alerts.append({"label": label, "level": level})
    alerts.sort(key=lambda a: (a["level"] != config.ALERT_ALARM, a["label"]))
    return alerts


def alert_level(by_label):
    alerts = alerts_from(by_label)
    if any(a["level"] == config.ALERT_ALARM for a in alerts):
        return config.ALERT_ALARM
    if alerts:
        return config.ALERT_WARN
    return config.ALERT_NORMAL


def risk_from_labels(by_label):
    level = alert_level(by_label)
    if level == config.ALERT_ALARM:
        return config.RISK_HIGH
    if level == config.ALERT_WARN:
        return config.RISK_MEDIUM
    return config.RISK_NORMAL


def compute_single(detections):
    by_label = by_label_from_detections(detections)
    return {
        "counts": counts_from_detections(detections),
        "by_label": by_label,
        "alerts": alerts_from(by_label),
        "risk": risk_from_labels(by_label),
    }


class TaskStats:
    def __init__(self):
        self.frames = 0
        self.total = _empty_counts()
        self.peak = _empty_counts()
        self.by_label = {}
        self.peak_by_label = {}
        self.current_counts = _empty_counts()
        self.current_by_label = {}

    def accumulate(self, detections):
        counts = counts_from_detections(detections)
        labels = by_label_from_detections(detections)
        self.frames += 1
        self.current_counts = counts
        self.current_by_label = labels
        for key in self.total:
            self.total[key] += counts[key]
            self.peak[key] = max(self.peak[key], counts[key])
        for label, n in labels.items():
            self.by_label[label] = self.by_label.get(label, 0) + n
            self.peak_by_label[label] = max(self.peak_by_label.get(label, 0), n)

    def snapshot(self):
        peak = dict(self.peak)
        peak.update(self.peak_by_label)
        return {
            "frames": self.frames,
            "total": dict(self.total),
            "peak": peak,
            "by_label": dict(self.by_label),
            "alerts": alerts_from(self.by_label),
            "risk": risk_from_labels(self.by_label),
            "current": {
                "counts": dict(self.current_counts),
                "by_label": dict(self.current_by_label),
                "alerts": alerts_from(self.current_by_label),
                "risk": risk_from_labels(self.current_by_label),
            },
        }
