"""Детерминированные проверки по структурированным полям и тексту."""
import re

VAGUE_TITLES = {"специалист", "сотрудник", "работник", "менеджер", "помощник", "рабочий", "инженер"}
VAGUE_DUTY = re.compile(r"и\s+др\.?|и\s+прочее|иные\s+обязанност|прочие\s+обязанност|по\s+поручению\s+руководител|выполнение\s+поручений", re.I)
VAGUE_SCHEDULE = re.compile(r"гибк|по\s+договор|свободн|ненормир|сменн", re.I)
CONCRETE_SCHEDULE = re.compile(r"\d\s*/\s*\d|\bс\s*\d{1,2}([:.]\d{2})?\s*(до|-|–|—)\s*\d|\d+\s*час|выходн|понедельник", re.I)
VAGUE_SALARY = re.compile(r"по\s+договор|по\s+результат|по\s+итогам\s+собеседован|обсуждается", re.I)
MONEY = re.compile(r"(\d[\d\s\u00a0]{2,}\d)\s*(?:руб|₽|р\.)", re.I)


def issue(topic, field, quote, kind, problem, rec, by="rules", quote2=None):
    d = {"topic": topic, "field": field, "quote": quote or "", "type": kind,
         "problem": problem, "recommendation": rec, "detected_by": by}
    if quote2 is not None:
        d["quote_2"] = quote2
    return d


def check(v):
    out = []
    blob = " ".join([v["duty"], v["requirement_text"], v["term_text"]])

    t = v["title"]
    if not t:
        out.append(issue("title", "job-name", "", "missing", "Не указано название должности.", "Укажите точное название должности."))
    elif t.strip().lower() in VAGUE_TITLES or len(t) < 4:
        out.append(issue("title", "job-name", t, "ambiguous", "Название слишком общее: непонятно направление работы.",
                         "Уточните профиль (например, «менеджер по закупкам», «инженер-сметчик»)."))

    d = v["duty"]
    if len(d) < 3:
        out.append(issue("duties", "duty", "", "missing", "Не описаны должностные обязанности.",
                         "Перечислите основные задачи и результат, который ожидается от сотрудника."))
    else:
        m = VAGUE_DUTY.search(d)
        if m:
            out.append(issue("duties", "duty", m.group(0), "ambiguous",
                             "Расплывчатая формулировка: непонятен объём и состав обязанностей.",
                             "Замените общую фразу конкретным перечнем задач или укажите, какие именно поручения имеются в виду."))
        elif len(d) < 40:
            out.append(issue("duties", "duty", d, "ambiguous", "Обязанности описаны слишком кратко.",
                             "Добавьте 3–5 основных задач с указанием участка работы."))

    if not v["requirement_any"]:
        out.append(issue("requirements", "requirement", "", "missing", "Не указаны требования к кандидату.",
                         "Укажите необходимое образование, опыт (в годах) и обязательные навыки или допуски."))

    lo, hi, st = v["salary_min"], v["salary_max"], v["salary_text"]
    if lo == 0 and hi == 0:
        if VAGUE_SALARY.search(st):
            out.append(issue("salary", "salary", st, "ambiguous", "Оплата «по договорённости» не даёт ориентира соискателю.",
                             "Укажите хотя бы вилку (от и до) или оклад и состав выплат (премии, надбавки)."))
        else:
            out.append(issue("salary", "salary", "", "missing", "Не указан размер оплаты.",
                             "Укажите оклад или диапазон и из каких выплат складывается доход."))
    else:
        if lo and hi and lo > hi:
            out.append(issue("salary", "salary_min/salary_max", str(lo), "contradiction",
                             "Нижняя граница оплаты больше верхней.", "Проверьте и исправьте границы вилки.", quote2=str(hi)))
        for m in MONEY.finditer(blob):
            val = int(re.sub(r"\D", "", m.group(1)))
            if val >= 5000 and ((hi and val > hi) or (lo and val < lo)):
                out.append(issue("salary", "duty", m.group(0), "contradiction",
                                 f"Сумма в описании не совпадает со структурированным полем оплаты ({lo or '—'}–{hi or '—'}).",
                                 "Приведите описание и поле оплаты к одному значению либо объясните разницу (например, оклад и премия).",
                                 quote2=st or f"{lo}–{hi}"))
                break

    sch = " ".join(x for x in [v["schedule"], v.get("shift", "")] if x)
    concrete = bool(CONCRETE_SCHEDULE.search(" ".join([sch, blob])))
    if not v["schedule"] and not v.get("shift"):
        out.append(issue("schedule", "schedule", "", "missing", "Не указан график работы.",
                         "Укажите режим: дни недели, время начала и окончания, наличие смен."))
    elif sch:
        m = VAGUE_SCHEDULE.search(sch + " " + blob)
        if m and not concrete:
            out.append(issue("schedule", "schedule", m.group(0), "ambiguous",
                             "Формулировка графика не отвечает на вопрос, в какие дни и часы нужно работать.",
                             "Уточните рабочие дни, длительность смены и порядок чередования (например, 2/2 с 8:00 до 20:00)."))
        if re.search(r"полный\s+рабочий\s+день|5\s*/\s*2", sch, re.I):
            m2 = re.search(r"сменн\w*\s+график|\b2\s*/\s*2\b|вахтов\w+|неполн\w+\s+(?:рабочий\s+)?(?:день|занятост)", blob, re.I)
            if m2:
                out.append(issue("schedule", "schedule", sch, "contradiction",
                                 "График в структурированном поле не совпадает с описанием.",
                                 "Определите, какой график действует на самом деле, и исправьте второе значение.",
                                 quote2=m2.group(0)))

    e = v["employment"]
    if not e:
        out.append(issue("employment", "employment", "", "missing", "Не указан тип занятости.",
                         "Укажите: полная/частичная занятость, постоянная работа или срочный договор."))
    else:
        if re.search(r"полная", e, re.I):
            m = re.search(r"частичн\w+\s+занятост|0[,.]5\s*ставк|совместительств", blob, re.I)
            if m:
                out.append(issue("employment", "employment", e, "contradiction",
                                 "Тип занятости противоречит описанию.", "Уточните, полная или частичная занятость предлагается.",
                                 quote2=m.group(0)))
        if re.search(r"врем|сезон|срочн", e, re.I) and not re.search(r"\d", v["term_text"] + blob):
            out.append(issue("employment", "employment", e, "ambiguous", "Не указан срок временной работы.",
                             "Укажите срок договора или период сезонной работы."))

    a = v["addresses"]
    if not a:
        out.append(issue("workplace", "addresses", "", "missing", "Не указано место работы.",
                         "Укажите населённый пункт и адрес (или район, если работа разъездная)."))
    else:
        loc = a[0]
        if len(loc) < 25 and not re.search(r"ул|улиц|просп|пер\.|шоссе|д\.|дом|\d", loc, re.I):
            out.append(issue("workplace", "addresses.address.location", loc, "ambiguous",
                             "Указан только населённый пункт/регион, без точного адреса.",
                             "Добавьте улицу и номер дома либо объясните, почему адрес не фиксирован."))
        m = re.search(r"\bразъездн\w+|\bкомандировк\w+|\bудал[её]нн\w+|\bна\s+объектах\b", blob, re.I)
        if m and len(loc) < 25 and not re.search(r"ул|улиц|просп|пер\.|шоссе|д\.|дом|\d", loc, re.I):
            out.append(issue("workplace", "duty", m.group(0), "ambiguous",
                             "Из описания неясно, где фактически выполняется работа и как часто нужны выезды.",
                             "Укажите места работы или маршруты, долю выездов и компенсацию расходов."))
    return out
