"""Convert Mindbox HTML email templates to SFMC format."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.blocks import (
    ConversionParams,
    block1,
    block2,
    block4_personalization,
    block4_privacy,
    block6_unsubscribe_script,
    build_cxq_url,
)


@dataclass
class ConversionResult:
    html: str
    warnings: list[str]
    changes: list[str]


_DOCSFERA_ANCHOR_RE = re.compile(
    r'(<a\b[^>]*\bhref=)(["\'])(https?://docsfera\.ru/[^"\']+)\2([^>]*>)([\s\S]*?</a>)',
    re.IGNORECASE,
)

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
    changed = False

    def fix_view_link(match: re.Match[str]) -> str:
        nonlocal changed
        anchor = match.group(0)
        if "%%view_email_url%%" in anchor:
            return anchor
        changed = True
        return re.sub(
            r'\bhref=(["\'])[^"\']*\1',
            'href="%%view_email_url%%"',
            anchor,
            count=1,
            flags=re.IGNORECASE,
        )

    updated, count = re.subn(
        r"<a\b[^>]*>[\s\S]*?сюда[\s\S]*?</a>",
        fix_view_link,
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    if count:
        return updated, True

    link = '<a href="%%view_email_url%%" target="_blank">сюда</a>'
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
    result = html
    for pattern, repl in patterns:
        updated_text, hit_count = re.subn(pattern, repl, result, count=1, flags=re.IGNORECASE)
        if hit_count:
            return updated_text, True

    if 'href="%%view_email_url%%"' not in html and re.search(
        r"отображается\s+некорректно", html, re.IGNORECASE
    ):
        updated_text, hit_count = re.subn(
            r"(отображается\s+некорректно[^<]{0,120}?)(?:нажмите\s*)?(?:<a\b[^>]*>[^<]*</a>|сюда|здесь)",
            rf"\1{link}",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        if hit_count:
            return updated_text, True

    return html, changed


def _extract_privacy_url(html: str) -> str:
    links = _find_docsfera_deeplink_urls(html)
    return links[0] if links else ""


def _personalization_field_map(params: ConversionParams) -> list[tuple[str, str]]:
    middle_field = "Attribute1" if params.personalization_mode == "manual" else "MiddleName"
    return [
        (r"<span>\s*\$\{Recipient\.Title\}\s*</span>", "%%=v(@title)=%%"),
        (r"\$\{Recipient\.Title\}", "%%=v(@title)=%%"),
        (r"\$\{Recipient\.FirstName\}", "%%=v(FirstName)=%%"),
        (r"\$\{Recipient\.MiddleName\}", f"%%=v({middle_field})=%%"),
        (r"\$\{Recipient\.LastName\}", "%%=v(LastName)=%%"),
        (r"%Recipient\.Title%", "%%=v(@title)=%%"),
        (r"%Recipient\.FirstName%", "%%=v(FirstName)=%%"),
        (r"%Recipient\.MiddleName%", f"%%=v({middle_field})=%%"),
        (r"%Recipient\.LastName%", "%%=v(LastName)=%%"),
    ]


def _replace_personalization(html: str, params: ConversionParams) -> tuple[str, bool]:
    result = html
    token_hits = 0
    for pattern, replacement in _personalization_field_map(params):
        updated, count = re.subn(pattern, replacement, result, flags=re.IGNORECASE)
        if count:
            token_hits += count
            result = updated

    if token_hits:
        return result, True

    greeting = block4_personalization(params)
    for pattern in (r"Здравствуйте[\s\S]*?!", r"Добрый\s+день[\s\S]*?!"):
        updated, count = re.subn(pattern, greeting, result, count=1, flags=re.IGNORECASE)
        if count:
            return updated, True
    return html, False


def _should_apply_content_deeplink(url: str) -> bool:
    normalized = url.rstrip("/")
    lower = normalized.lower()
    if lower in {"https://docsfera.ru", "http://docsfera.ru"}:
        return False
    if any(token in lower for token in ("voting/cxq", "personal/unsubscribe", "unsubscribe")):
        return False
    return True


def _find_docsfera_deeplink_urls(html: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _DOCSFERA_ANCHOR_RE.finditer(html):
        url = match.group(3).rstrip("/")
        if not _should_apply_content_deeplink(url):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _wrap_anchor_with_deeplink(
    match: re.Match[str],
    redirect_url: str,
    *,
    alias: str = "",
) -> str:
    if "RedirectTo(@UnsubscribeUrl)" in match.group(0):
        return match.group(0)

    open_tag = match.group(4)
    if alias and 'alias="' not in open_tag.lower():
        open_tag = re.sub(r"^<a\b", f'<a alias="{alias}"', open_tag, count=1, flags=re.IGNORECASE)

    open_part = (
        f"{match.group(1)}{match.group(2)}%%=RedirectTo(@UnsubscribeUrl)=%%"
        f"{match.group(2)}{open_tag}"
    )
    return f"{block4_privacy(redirect_url.rstrip('/'))}\n{open_part}{match.group(5)}"


def _apply_all_docsfera_deeplinks(html: str) -> tuple[str, int]:
    result = html
    count = 0

    if "Start--Privacy Link goes here" in result:
        urls = _find_docsfera_deeplink_urls(result)
        if urls:
            block = block4_privacy(urls[0])
            updated = re.sub(
                r"<!-----Start--Privacy Link goes here[\s\S]*?<!-----END---Privacy Link goes here ---->",
                block,
                result,
                count=1,
                flags=re.IGNORECASE,
            )
            if updated != result:
                result = updated
                count += 1

    matches = list(_DOCSFERA_ANCHOR_RE.finditer(result))
    for match in reversed(matches):
        url = match.group(3).rstrip("/")
        if not _should_apply_content_deeplink(url):
            continue
        if "RedirectTo(@UnsubscribeUrl)" in match.group(0):
            continue
        replacement = _wrap_anchor_with_deeplink(match, url)
        result = result[: match.start()] + replacement + result[match.end() :]
        count += 1

    return result, count


def _replace_cxq_block(html: str, params: ConversionParams) -> tuple[str, bool]:
    if "docsfera.ru/voting/cxq" not in html.lower():
        return html, False

    updated = re.sub(
        r"https?://docsfera\.ru/voting/cxq/\?[^\"'\s<>]+",
        lambda match: build_cxq_url(params, _extract_cxq_rating(match.group(0))),
        html,
    )
    return updated, updated != html


def _extract_cxq_rating(url: str) -> int:
    match = re.search(r"[?&]R=(\d)", url, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        return max(1, min(7, value))
    return 1


def _ensure_unsubscribe_alias(anchor: str) -> str:
    if 'alias="unsubscribe"' in anchor.lower():
        return anchor
    if re.search(r"\balias\s*=", anchor, re.IGNORECASE):
        return re.sub(
            r'\balias=(["\'])[^"\']*\1',
            'alias="unsubscribe"',
            anchor,
            count=1,
            flags=re.IGNORECASE,
        )
    return re.sub(r"^<a\b", '<a alias="unsubscribe"', anchor, count=1, flags=re.IGNORECASE)


def _replace_href_with_redirect(anchor: str) -> str:
    return re.sub(
        r'\bhref=(["\'])[^"\']*\1',
        'href="%%=RedirectTo(@UnsubscribeUrl)=%%"',
        anchor,
        count=1,
        flags=re.IGNORECASE,
    )


def _wrap_unsubscribe_anchor(anchor: str) -> str:
    if "RedirectTo(@UnsubscribeUrl)" in anchor:
        return _ensure_unsubscribe_alias(anchor)
    wrapped = _ensure_unsubscribe_alias(_replace_href_with_redirect(anchor))
    return f"{block6_unsubscribe_script()}\n{wrapped}"


def _replace_unsubscribe(html: str) -> tuple[str, bool]:
    anchor_re = re.compile(r"(<a\b[^>]*>)([\s\S]*?</a>)", re.IGNORECASE)
    result = html
    count = 0

    for match in reversed(list(anchor_re.finditer(result))):
        anchor = match.group(0)
        href_match = re.search(r'\bhref=(["\'])([^"\']*)\1', anchor, re.IGNORECASE)
        href = href_match.group(2).lower() if href_match else ""
        inner = match.group(2).lower()
        is_unsub = any(token in href for token in ("unsubscribe", "otpis")) or "отпис" in inner
        if not is_unsub:
            continue
        replacement = _wrap_unsubscribe_anchor(anchor)
        if replacement != anchor:
            result = result[: match.start()] + replacement + result[match.end() :]
            count += 1

    if count:
        return result, True

    if "</body>" in result.lower():
        fallback = (
            f"{block6_unsubscribe_script()}\n"
            '<a alias="unsubscribe" href="%%=RedirectTo(@UnsubscribeUrl)=%%">сюда.</a>'
        )
        updated = re.sub(r"</body>", fallback + "\n</body>", result, count=1, flags=re.IGNORECASE)
        return updated, True
    return (
        result
        + f'\n{block6_unsubscribe_script()}\n<a alias="unsubscribe" href="%%=RedirectTo(@UnsubscribeUrl)=%%">сюда.</a>',
        True,
    )


def _strip_mindbox_artifacts(html: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    patterns = [
        (r"<!--\s*Mindbox[\s\S]*?-->", "Removed Mindbox HTML comment"),
        (r"<script[^>]*mindbox[^>]*>[\s\S]*?</script>", "Removed Mindbox script"),
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

    result, ok = _replace_personalization(result, params)
    if ok:
        changes.append(f"Обновлена персонализация (режим: {params.personalization_mode})")
    else:
        warnings.append("Блок №4: не найдено приветствие для замены персонализации")

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
        changes.append("Обновлена ссылка «сюда» (блок №3) — href без изменения вёрстки")
    else:
        warnings.append("Блок №3: не найден текст про некорректное отображение письма")

    result, deeplink_count = _apply_all_docsfera_deeplinks(result)
    if deeplink_count:
        changes.append(
            f"Добавлен deeplink ContentBlock 1649 к {deeplink_count} ссылкам docsfera.ru "
            "(разметка и стили сохранены)"
        )
    else:
        warnings.append("Блок №4 (deeplink): ссылки docsfera.ru для обёртки не найдены")

    if params.cxq_brand:
        if params.cxq_cn.lower() != "promo" and not params.utm_campaign:
            warnings.append("Блок №5: utm_campaign обязателен для CXQ, когда CN не promo")
        result, ok = _replace_cxq_block(result, params)
        if ok:
            changes.append("Обновлены href в CXQ-ссылках (блок №5) — вёрстка сохранена")
        else:
            warnings.append("Блок №5: CXQ-ссылки не найдены — проверьте вручную")
    else:
        warnings.append("Блок №5: укажите Brand для генерации CXQ-ссылок")

    result, ok = _replace_unsubscribe(result)
    if ok:
        changes.append("Обновлен блок отписки (блок №6) — разметка ссылки сохранена")

    if params.data_extension != "Akamai_profiles_consents_bounced":
        warnings.append(
            f"Используется нестандартный источник данных: {params.data_extension}. "
            "Проверьте Lookup в блоке №1."
        )

    return ConversionResult(html=result, warnings=warnings, changes=changes)
