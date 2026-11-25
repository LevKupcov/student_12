import datetime
import json
import os
import tempfile
from collections import Counter

from . import ai as ai_mod
from .normalize import normalize
from .rules import check


def _dedupe(issues):
    seen, out = set(), []
    for i in issues:
        k = (i["topic"], i["field"], i["quote"].lower())
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


def build_report(raw_items, cfg, use_ai=False, source="local"):
    by_id, ai_errors = {}, 0
    for raw in raw_items:
        v = normalize(raw)
        if not v["id"]:
            continue
        issues = check(v)
        if use_ai:
            extra, err = ai_mod.analyze(v, cfg)
            ai_errors += bool(err)
            issues += extra
        by_id[v["id"]] = {"id": v["id"], "url": v["url"], "title": v["title"], "issues": _dedupe(issues)}
    vacs = list(by_id.values())
    c = Counter(i["topic"] for x in vacs for i in x["issues"])
    return {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "source": source, "ai_enabled": use_ai, "ai_errors": ai_errors,
            "stats": {"vacancies": len(vacs), "with_issues": sum(1 for x in vacs if x["issues"]),
                      "issues_total": sum(c.values()), "by_topic": dict(c)},
            "vacancies": vacs}


def save_atomic(report, path):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
