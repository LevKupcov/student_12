"""ИИ-слой: ищет неоднозначности и противоречия в тексте. OpenAI-совместимый API (Ollama / Groq / OpenRouter...)."""
import json
import os
import re
import urllib.request

TOPICS = {"title", "duties", "requirements", "salary", "schedule", "workplace", "employment"}
FIELDS = {"job-name": "title", "duty": "duty", "requirement.qualification": "requirement_text",
          "term.text": "term_text", "schedule": "schedule", "salary": "salary_text", "employment": "employment"}

SYSTEM = (
    "Ты редактор вакансий. Проверяешь, насколько понятно описаны условия работы для соискателя. "
    "Ищи ТОЛЬКО неоднозначные формулировки и противоречия между полями. Не выдумывай факты, не делай выводов о нарушении закона. "
    "quote ДОЛЖНА быть дословной цитатой из указанного поля. Отвечай строго JSON: "
    '{"issues":[{"topic":"title|duties|requirements|salary|schedule|workplace|employment",'
    '"field":"имя поля","quote":"цитата","quote_2":"вторая цитата только для противоречия или пусто",'
    '"type":"ambiguous|contradiction","problem":"суть","recommendation":"что уточнить"}]}. '
    'Если проблем нет — {"issues":[]}.'
)


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _call(cfg, user_text):
    base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    body = {"model": os.environ.get("LLM_MODEL", "qwen2.5:3b"), "temperature": 0,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text}]}
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + os.environ.get("LLM_API_KEY", "ollama")})
    with urllib.request.urlopen(req, timeout=cfg.get("llm_timeout_sec", 90)) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def _parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)).get("issues", []) if m else []


def validate(items, v):
    """Отбрасывает ответы модели с выдуманными цитатами (антигаллюцинационная проверка)."""
    good = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or it.get("topic") not in TOPICS or it.get("type") not in ("ambiguous", "contradiction"):
            continue
        src = v.get(FIELDS.get(it.get("field"), ""), "")
        q = _norm(it.get("quote"))
        if not q or q not in _norm(src):
            continue
        if it["type"] == "contradiction":
            q2 = _norm(it.get("quote_2"))
            if not q2 or q2 not in _norm(" ".join(str(v.get(k, "")) for k in FIELDS.values())):
                continue
        if not it.get("problem") or not it.get("recommendation"):
            continue
        d = {"topic": it["topic"], "field": it["field"], "quote": it["quote"], "type": it["type"],
             "problem": it["problem"], "recommendation": it["recommendation"], "detected_by": "ai"}
        if it["type"] == "contradiction":
            d["quote_2"] = it["quote_2"]
        good.append(d)
    return good


def analyze(v, cfg):
    payload = {k: v[f] for k, f in FIELDS.items() if v.get(f)}
    last = None
    for _ in range(2):
        try:
            return validate(_parse(_call(cfg, json.dumps(payload, ensure_ascii=False))), v), None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    return [], last
