"""Приводит вакансию из ответа API к плоской структуре."""
import html
import re


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>|</p>|</li>", "\n", str(text), flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t\u00a0]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def normalize(raw):
    v = raw.get("vacancy", raw)
    req = v.get("requirement") or {}
    term = v.get("term") or {}
    addrs = (v.get("addresses") or {}).get("address") or []
    if isinstance(addrs, dict):
        addrs = [addrs]
    return {
        "id": str(v.get("id") or ""),
        "url": v.get("vac_url") or v.get("url") or "",
        "title": strip_html(v.get("job-name")),
        "duty": strip_html(v.get("duty")),
        "requirement_text": strip_html(req.get("qualification")),
        "requirement_education": req.get("education") or "",
        "requirement_experience": req.get("experience"),
        "requirement_any": any([req.get("qualification"), req.get("education"), req.get("experience")]),
        "salary_text": strip_html(v.get("salary")),
        "salary_min": _num(v.get("salary_min")),
        "salary_max": _num(v.get("salary_max")),
        "schedule": strip_html(v.get("schedule")),
        "shift": strip_html(" ".join(s.get("name", "") if isinstance(s, dict) else str(s) for s in (v.get("shift") or []))),
        "employment": strip_html(v.get("employment")),
        "term_text": strip_html(term.get("text")),
        "addresses": [strip_html(a.get("location")) for a in addrs if a.get("location")],
        "company": (v.get("company") or {}).get("name") or "",
    }
