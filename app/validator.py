"""Validate SFMC HTML email templates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from app.blocks import (
    BLOCK1_MARKERS,
    BLOCK2_MARKERS,
    BLOCK3_MARKERS,
    BLOCK4_PERSONALIZATION_MARKERS,
    BLOCK4_PRIVACY_MARKERS,
    BLOCK5_MARKERS,
    BLOCK6_MARKERS,
    MINDBOX_PATTERNS,
)


@dataclass
class ValidationIssue:
    block: str
    severity: str  # error | warning | info
    message: str
    hint: str = ""
    snippet: str = ""


@dataclass
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(
        self,
        block: str,
        severity: str,
        message: str,
        hint: str = "",
        snippet: str = "",
    ) -> None:
        self.issues.append(
            ValidationIssue(
                block=block,
                severity=severity,
                message=message,
                hint=hint,
                snippet=snippet,
            )
        )
        if severity == "error":
            self.ok = False


def _find_snippet(html: str, needle: str, radius: int = 80) -> str:
    idx = html.lower().find(needle.lower())
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(html), idx + len(needle) + radius)
    snippet = html[start:end].replace("\n", " ")
    return snippet[:200] + ("..." if len(snippet) > 200 else "")


def _check_markers(
    report: ValidationReport,
    html: str,
    block_name: str,
    markers: list[str],
    *,
    required: bool = True,
) -> None:
    missing = [m for m in markers if m not in html]
    if missing and required:
        report.add(
            block_name,
            "error",
            f"Отсутствуют обязательные элементы: {', '.join(missing[:3])}",
            hint=f"Смотрите инструкцию — {block_name}",
            snippet=_find_snippet(html, missing[0]) if missing else "",
        )
    elif missing:
        report.add(
            block_name,
            "warning",
            f"Частично отсутствуют элементы: {', '.join(missing[:3])}",
            hint=f"Проверьте {block_name}",
        )


def _validate_block1(report: ValidationReport, html: str) -> None:
    _check_markers(report, html, "Блок №1", BLOCK1_MARKERS)
    match = re.search(r'Lookup\("([^"]+)"', html)
    if match:
        source = match.group(1)
        if source != "Akamai_profiles_consents_bounced":
            report.add(
                "Блок №1",
                "warning",
                f"Источник данных Lookup: «{source}» (не стандартный Akamai_profiles_consents_bounced)",
                hint="Убедитесь, что DE указан правильно для этой рассылки",
                snippet=_find_snippet(html, f'Lookup("{source}"'),
            )


def _validate_block2(report: ValidationReport, html: str) -> None:
    _check_markers(report, html, "Блок №2", BLOCK2_MARKERS)
    head_end = html.lower().find("</head>")
    campaign_pos = html.find("SET @utm_campaign")
    if head_end != -1 and campaign_pos != -1 and campaign_pos < head_end:
        report.add(
            "Блок №2",
            "warning",
            "Блок №2 находится внутри <head>, рекомендуется размещать после </head>",
            hint="Переместите AMPscript-блок сразу после </head>",
        )


def _validate_block3(report: ValidationReport, html: str) -> None:
    _check_markers(report, html, "Блок №3", BLOCK3_MARKERS)
    if "отображается некорректно" not in html.lower():
        report.add(
            "Блок №3",
            "warning",
            "Не найден текст «Если данное письмо отображается некорректно...»",
            hint="Добавьте preheader/view-online текст с ссылкой на %%view_email_url%%",
        )


def _validate_block4(report: ValidationReport, html: str) -> None:
    _check_markers(report, html, "Блок №4 (персонализация)", BLOCK4_PERSONALIZATION_MARKERS)
    if "Attribute1" in html and "MiddleName" not in html:
        report.add(
            "Блок №4",
            "info",
            "Используется ручная выгрузка (Attribute1)",
            hint="Для DE Akamai используйте MiddleName вместо Attribute1",
        )
    _check_markers(report, html, "Блок №4 (Privacy)", BLOCK4_PRIVACY_MARKERS, required=False)
    if "docsfera.ru" in html.lower() and "Start--Privacy Link goes here" not in html:
        report.add(
            "Блок №4 (Privacy)",
            "warning",
            "Есть ссылки docsfera.ru, но блок Privacy Link не найден",
            hint="Оберните privacy-ссылки в ContentBlockbyId(1649)",
        )


def _validate_cxq_url(report: ValidationReport, url: str) -> None:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    required = ["Channel", "R", "Brand", "DA", "TA", "Franchise", "BU", "Function", "CN", "utm_campaign"]
    missing = [p for p in required if p not in params or not params[p][0]]
    if missing:
        report.add(
            "Блок №5 (CXQ)",
            "error",
            f"В CXQ-ссылке отсутствуют параметры: {', '.join(missing)}",
            hint="Заполните параметры CXQ по таблице Excel",
            snippet=url[:200],
        )
    if params.get("Channel", [""])[0].lower() != "email":
        report.add(
            "Блок №5 (CXQ)",
            "error",
            "Channel должен быть email",
            snippet=url[:200],
        )
    rating = params.get("R", [""])[0]
    if rating and (not rating.isdigit() or not (1 <= int(rating) <= 7)):
        report.add(
            "Блок №5 (CXQ)",
            "error",
            f"Параметр R должен быть от 1 до 7, сейчас: {rating}",
            snippet=url[:200],
        )


def _validate_block5(report: ValidationReport, html: str) -> None:
    if not any(marker in html for marker in BLOCK5_MARKERS):
        report.add(
            "Блок №5 (CXQ)",
            "error",
            "CXQ-блок не найден",
            hint="Добавьте секцию «Насколько информация...» со ссылками docsfera.ru/voting/cxq/",
        )
        return

    urls = re.findall(r"https?://docsfera\.ru/voting/cxq/\?[^\"'\s<>]+", html, re.IGNORECASE)
    if not urls:
        report.add(
            "Блок №5 (CXQ)",
            "error",
            "Ссылки CXQ не найдены",
            hint="Проверьте href в кнопках оценки 1–7",
        )
        return

    ratings = set()
    for url in urls:
        _validate_cxq_url(report, url)
        match = re.search(r"[?&]R=(\d)", url, re.IGNORECASE)
        if match:
            ratings.add(int(match.group(1)))

    if len(ratings) < 7:
        report.add(
            "Блок №5 (CXQ)",
            "warning",
            f"Найдено оценок R: {sorted(ratings)} — ожидается 7 ссылок (R=1..7)",
            hint="Каждая кнопка должна иметь свой параметр R",
        )


def _validate_block6(report: ValidationReport, html: str) -> None:
    _check_markers(report, html, "Блок №6 (отписка)", BLOCK6_MARKERS)


def _validate_mindbox_leftovers(report: ValidationReport, html: str) -> None:
    body_match = re.search(r"<body[^>]*>([\s\S]*)</body>", html, re.IGNORECASE)
    check_area = body_match.group(1) if body_match else html

    for pattern in MINDBOX_PATTERNS:
        if pattern.lower() == "mindbox":
            # Ignore filename/title mentions; flag only token-like Mindbox usage.
            if not re.search(r"\$\{[^}]*\}|Recipient\.|Email\.Message|%%\[[^\]]*Mindbox", check_area, re.IGNORECASE):
                continue
        matches = re.findall(pattern, check_area, re.IGNORECASE)
        if matches:
            sample = matches[0] if isinstance(matches[0], str) else matches[0][0]
            report.add(
                "Mindbox",
                "error",
                f"Обнаружены Mindbox-артефакты: {sample[:80]}",
                hint="Замените Mindbox-токены на SFMC AMPscript",
                snippet=_find_snippet(html, sample[:40]),
            )


def validate_sfmc_html(html: str, *, is_mindbox_source: bool = False) -> ValidationReport:
    """Run all SFMC validation checks."""
    report = ValidationReport(ok=True)

    if not html.strip():
        report.add("Общее", "error", "HTML пустой")
        return report

    _validate_block1(report, html)
    _validate_block2(report, html)
    _validate_block3(report, html)
    _validate_block4(report, html)
    _validate_block5(report, html)
    _validate_block6(report, html)
    _validate_mindbox_leftovers(report, html)

    if is_mindbox_source and report.ok:
        report.add(
            "Общее",
            "info",
            "Файл распознан как Mindbox — выполните конвертацию перед отправкой в SFMC",
        )

    return report
