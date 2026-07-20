"""Convert Mindbox HTML email templates to SFMC format."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.blocks import (
    ConversionParams,
    block1,
    block2,
    block3_link,
    block4_personalization,
    block4_privacy,
    block5_cxq,
    block6_unsubscribe,
    build_cxq_url,
)


@dataclass
class ConversionResult:
    html: str
    warnings: list[str]
    changes: list[str]


def _insert_before_doctype(html: str, snippet: str) -> tuple[str, bool]:
    match = re.search(r"(<!DOCTYPE|<html)", html, re.IGNORECASE)
    if match:
        idx = match.start()
        return html[:idx] + snippet + "\n" + html[idx:], True
    return snippet + "\n" + html, True


def _insert_after_head(html: str, snippet: str) -> tuple[str, bool]:
    match = re.search(r"</head>", html, re.IGNORECASE)
    if not match:
        return html, False
    idx = match.end()
    return html[:idx] + "\n" + snippet + "\n" + html[idx:], True


def _replace_view_in_browser(html: str) -> tuple[str, bool]:
    link = block3_link()
    changed = False
    result = html

    # Always normalize anchors with link text «сюда» to the SFMC view-online URL.
    updated, count = re.subn(
        r'<a\b[^>]*href=(["\'])[^"\']*\1[^>]*>\s*сюда\s*</a>',
        link,
        result,
        flags=re.IGNORECASE,
    )
    if count:
        result = updated
        changed = True

    patterns = [
        (
            r"(Если[^<]{0,180}отображается\s+некорректно[^<]*?)(?:нажмите\s*)?(?:<a\b[^>]*>[^<]*</a>|сюда|здесь)",
            rf"\1{link}",
        ),
        (
            r"(Если\s+(?:данное\s+)?письмо[^<]{0,180}отображается\s+некорректно[^<]*?)(<a\b[^>]*>[^<]*</a>|сюда|здесь)",
            rf"\1{link}",
        ),
    ]
    for pattern, repl in patterns:
        updated, count = re.subn(pattern, repl, result, count=1, flags=re.IGNORECASE)
        if count:
            result = updated
            changed = True
            break

    if 'href="%%view_email_url%%"' not in result and re.search(
        r"отображается\s+некорректно", result, re.IGNORECASE
    ):
        updated, count = re.subn(
            r"(отображается\s+некорректно[^<]{0,120}?)(?:нажмите\s*)?(?:<a\b[^>]*>[^<]*</a>|сюда|здесь)",
            rf"\1{link}",
            result,
            count=1,
            flags=re.IGNORECASE,
        )
        if count:
            result = updated
            changed = True

    return result, changed


def _extract_privacy_url(html: str) -> str:
    links = re.findall(r"https?://docsfera\.ru/[^\s\"'<>]+", html, re.IGNORECASE)
    candidates: list[tuple[int, str]] = []
    for url in links:
        lower = url.lower()
        if any(token in lower for token in ("unsubscribe", "voting/cxq", "/personal/unsubscribe")):
            continue
        score = 0
        if any(token in lower for token in ("lectures", "lecture", "policy", "politic", "privacy", "confiden")):
            score += 2
        candidates.append((score, url.rstrip("/")))

    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], len(item[1])))
    return candidates[0][1]


def _replace_personalization(html: str, params: ConversionParams) -> tuple[str, bool]:
    greeting = block4_personalization(params)
    patterns = [
        r"Здравствуйте[^!<\n]{0,120}!?",
        r"Добрый\s+день[^!<\n]{0,120}!?",
        r"\$\{Recipient\.[^}]+\}",
        r"%%=v\(@FirstName\)=%%",
        r"\{\{[^}]+\}\}",
    ]
    for pattern in patterns:
        updated, count = re.subn(pattern, greeting, html, count=1, flags=re.IGNORECASE)
        if count:
            return updated, True
    return html, False


def _replace_or_insert_privacy(html: str, privacy_url: str = "") -> tuple[str, bool]:
    chosen = privacy_url.strip() or _extract_privacy_url(html)
    if not chosen:
        return html, False

    block = block4_privacy(chosen)
    if "Start--Privacy Link goes here" in html:
        updated = re.sub(
            r"<!-----Start--Privacy Link goes here[\s\S]*?<!-----END---Privacy Link goes here ---->",
            block,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        return updated, updated != html

    escaped = re.escape(chosen.rstrip("/"))
    anchor_pattern = rf'<a\b[^>]*href=["\']{escaped}/?["\'][^>]*>[\s\S]*?</a>'
    if re.search(anchor_pattern, html, re.IGNORECASE):
        updated = re.sub(anchor_pattern, block, html, count=1, flags=re.IGNORECASE)
        return updated, True

    footer_match = re.search(r"(<td[^>]*>[\s\S]{0,200}политик)", html, re.IGNORECASE)
    if footer_match:
        idx = footer_match.start()
        return html[:idx] + block + "\n" + html[idx:], True
    if "</body>" in html.lower():
        return re.sub(r"</body>", block + "\n</body>", html, count=1, flags=re.IGNORECASE), True
    return html + "\n" + block, True


def _replace_cxq_block(html: str, params: ConversionParams) -> tuple[str, bool]:
    cxq_block = block5_cxq(params)
    section_pattern = (
        r"(Насколько\s+информация\s+в\s+письме\s+соответствовала\s+вашим\s+потребностям\?)"
        r"[\s\S]{0,4000}?(?=</td>|</tr>|</table>|</body>|$)"
    )
    if re.search(section_pattern, html, re.IGNORECASE):
        def replacer(match: re.Match[str]) -> str:
            return match.group(1) + "\n" + cxq_block

        updated = re.sub(section_pattern, replacer, html, count=1, flags=re.IGNORECASE)
        return updated, updated != html

    if "docsfera.ru/voting/cxq" in html:
        updated = re.sub(
            r"https?://docsfera\.ru/voting/cxq/\?[^\"'\s<>]+",
            lambda m: build_cxq_url(params, _extract_cxq_rating(m.group(0))),
            html,
        )
        return updated, updated != html

    return html, False


def _extract_cxq_rating(url: str) -> int:
    match = re.search(r"[?&]R=(\d)", url, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        return max(1, min(7, value))
    return 1


def _replace_unsubscribe(html: str) -> tuple[str, bool]:
    block = block6_unsubscribe()
    if 'alias="unsubscribe"' in html and "RedirectTo(@UnsubscribeUrl)" in html:
        updated = re.sub(
            r"%%\[[\s\S]*?set @RedirectUri='https://docsfera\.ru/personal/unsubscribe/'[\s\S]*?"
            r"%%=ContentBlockbyId\(\"1649\"\)=%%[\s\S]*?"
            r'<a alias="unsubscribe" href="%%=RedirectTo\(@UnsubscribeUrl\)=%%[^>]*>',
            block,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        if updated != html:
            return updated, True
        return html, True

    patterns = [
        r"<a[^>]*отпис[^>]*>[\s\S]*?</a>",
        r"https?://[^\"'\s<>]*unsubscribe[^\"'\s<>]*",
        r"\$\{[^}]*unsubscribe[^}]*\}",
    ]
    for pattern in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            updated = re.sub(pattern, block, html, count=1, flags=re.IGNORECASE)
            if updated != html:
                return updated, True

    if "</body>" in html.lower():
        updated = re.sub(r"</body>", block + "\n</body>", html, count=1, flags=re.IGNORECASE)
        return updated, True
    return html + "\n" + block, True


def _strip_mindbox_artifacts(html: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    patterns = [
        (r"<!--\s*Mindbox[\s\S]*?-->", "Removed Mindbox HTML comment"),
        (r"<script[^>]*mindbox[^>]*>[\s\S]*?</script>", "Removed Mindbox script"),
        (r"\$\{Recipient\.[^}]+\}", "Removed Mindbox Recipient token"),
        (r"\$\{Message\.[^}]+\}", "Removed Mindbox Message token"),
    ]
    updated = html
    for pattern, message in patterns:
        new_html, count = re.subn(pattern, "", updated, flags=re.IGNORECASE)
        if count:
            warnings.append(f"{message} ({count} шт.)")
            updated = new_html
    return updated, warnings


def convert_mindbox_to_sfmc(html: str, params: ConversionParams) -> ConversionResult:
    """Apply SFMC mandatory blocks and replace Mindbox-specific fragments."""
    warnings: list[str] = []
    changes: list[str] = []
    result = html

    result, strip_warnings = _strip_mindbox_artifacts(result)
    warnings.extend(strip_warnings)

    if "set @subscriberKey = _subscriberkey" not in result:
        snippet = block1(params)
        result, ok = _insert_before_doctype(result, snippet)
        if ok:
            changes.append(f"Добавлен блок №1 (DE: {params.data_extension})")
        else:
            warnings.append("Не удалось вставить блок №1 перед DOCTYPE")

    if "SET @utm_campaign = __AdditionalEmailAttribute1" not in result:
        snippet = block2()
        result, ok = _insert_after_head(result, snippet)
        if ok:
            changes.append("Добавлен блок №2 (метаданные кампании и opencounter)")
        else:
            warnings.append("Не найден </head> — блок №2 не вставлен")

    result, ok = _replace_view_in_browser(result)
    if ok:
        changes.append("Обновлена ссылка «сюда» (блок №3)")
    else:
        warnings.append("Блок №3: не найден текст про некорректное отображение письма")

    result, ok = _replace_personalization(result, params)
    if ok:
        changes.append(f"Обновлена персонализация (режим: {params.personalization_mode})")
    else:
        warnings.append("Блок №4: не найдено приветствие для замены персонализации")

    result, ok = _replace_or_insert_privacy(result, params.privacy_url)
    if ok:
        privacy_source = params.privacy_url.strip() or _extract_privacy_url(html)
        changes.append(f"Обновлен блок Privacy Link (docsfera.ru: {privacy_source})")
    else:
        warnings.append("Блок №4 (Privacy): ссылка docsfera.ru не найдена в исходном HTML")

    if params.cxq_brand:
        if params.cxq_cn.lower() != "promo" and not params.utm_campaign:
            warnings.append("Блок №5: utm_campaign обязателен для CXQ, когда CN не promo")
        result, ok = _replace_cxq_block(result, params)
        if ok:
            changes.append("Обновлен CXQ-блок (блок №5) с UTM-метками")
        else:
            warnings.append("Блок №5: CXQ-секция не найдена — проверьте вручную")
    else:
        warnings.append("Блок №5: укажите Brand для генерации CXQ-ссылок")

    result, ok = _replace_unsubscribe(result)
    if ok:
        changes.append("Обновлен блок отписки (блок №6)")

    if params.data_extension != "Akamai_profiles_consents_bounced":
        warnings.append(
            f"Используется нестандартный источник данных: {params.data_extension}. "
            "Проверьте Lookup в блоке №1."
        )

    return ConversionResult(html=result, warnings=warnings, changes=changes)
