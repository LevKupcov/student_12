import json
import time
import urllib.error
import urllib.request


class FetchError(Exception):
    pass


def _get(url, timeout, retries=3):
    """GET с ретраями: портал «Работа в России» периодически отдаёт HTTP 500 и рвёт соединения."""
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": "transparent-vacancy/0.1", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code < 500:
                break  # 4xx — ретраить бессмысленно
            time.sleep(2 * (attempt + 1))
    raise FetchError(f"{url}: {last}") from last


def fetch_vacancies(cfg):
    """Постранично загружает вакансии. offset — номер страницы (проверено на живом API региона 39).

    Гарантирует минимум min_pages страниц, если объём данных позволяет
    (требование задания: обработать хотя бы две страницы)."""
    items, page = [], 0
    limit, cap, min_pages = cfg["page_size"], cfg["max_vacancies"], cfg.get("min_pages", 2)
    seen = set()
    while len(items) < cap:
        data = _get(f'{cfg["source_url"]}?offset={page}&limit={limit}', cfg["timeout_sec"])
        chunk = (data.get("results") or {}).get("vacancies") or []
        if not chunk:
            break
        for raw in chunk:
            vid = str((raw.get("vacancy") or raw).get("id") or "")
            if vid and vid in seen:
                continue  # один результат на ID вакансии, в т.ч. между страницами
            seen.add(vid)
            items.append(raw)
        page += 1
        if len(chunk) < limit:
            break
        if page >= min_pages and len(items) >= cap:
            break
    if not items:
        raise FetchError("API вернул пустой список вакансий")
    return items[:cap]
