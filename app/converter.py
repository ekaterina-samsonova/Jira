"""Convert Mindbox HTML email templates to SFMC format."""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from typing import Callable

from app.blocks import (
    ConversionParams,
    QUALTRICS_CXQ_HOST_RE,
    block1,
    block2,
    block4_personalization,
    block4_privacy,
    block6_unsubscribe_script,
    build_cxq_url,
    build_qualtrics_cxq_url,
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
    result = html

    updated, count = re.subn(
        r'\bhref=(["\'])\$\{Message\.AccessibilityLink\}\1',
        'href="%%view_email_url%%"',
        result,
        flags=re.IGNORECASE,
    )
    if count:
        return updated, True

    view_section = re.compile(
        r"(отображается\s+некорректно[\s\S]{0,320}?)(<a\b[^>]*>[\s\S]*?сюда[\s\S]*?</a>)",
        re.IGNORECASE,
    )

    def fix_view_in_context(match: re.Match[str]) -> str:
        nonlocal changed
        prefix = match.group(1)
        anchor = match.group(2)
        if "%%view_email_url%%" in anchor:
            return match.group(0)
        changed = True
        fixed = re.sub(
            r'\bhref=(["\'])[^"\']*\1',
            'href="%%view_email_url%%"',
            anchor,
            count=1,
            flags=re.IGNORECASE,
        )
        return prefix + fixed

    updated, count = view_section.subn(fix_view_in_context, result, count=1)
    if count:
        return updated, True

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
        result,
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
    for pattern, repl in patterns:
        updated_text, hit_count = re.subn(pattern, repl, result, count=1, flags=re.IGNORECASE)
        if hit_count:
            return updated_text, True

    if 'href="%%view_email_url%%"' not in result and re.search(
        r"отображается\s+некорректно", result, re.IGNORECASE
    ):
        updated_text, hit_count = re.subn(
            r"(отображается\s+некорректно[^<]{0,120}?)(?:нажмите\s*)?(?:<a\b[^>]*>[^<]*</a>|сюда|здесь)",
            rf"\1{link}",
            result,
            count=1,
            flags=re.IGNORECASE,
        )
        if hit_count:
            return updated_text, True

    return result, changed


def _extract_privacy_url(html: str) -> str:
    links = _find_docsfera_deeplink_urls(html)
    return links[0] if links else ""


_CXQ_HREF_RE = re.compile(
    r'(<a\b[^>]*\bhref\s*=\s*)(["\'])(https?://docsfera\.ru/voting/cxq/?\?[^"\']*)(\2)',
    re.IGNORECASE,
)
_CXQ_URL_RE = re.compile(
    r"https?://docsfera\.ru/voting/cxq/?\?[^\"'\s<>]+",
    re.IGNORECASE,
)
_QUALTRICS_CXQ_HREF_RE = re.compile(
    rf'(<a\b[^>]*\bhref\s*=\s*)(["\'])(https?://{QUALTRICS_CXQ_HOST_RE}/jfe/form/[^"\']+)(\2)',
    re.IGNORECASE,
)
_QUALTRICS_CXQ_URL_RE = re.compile(
    rf"https?://{QUALTRICS_CXQ_HOST_RE}/jfe/form/[^\"'\s<>]+",
    re.IGNORECASE,
)
_SFMC_GREETING_RE = re.compile(
    r"Здравствуйте,\s*%%=v\(@title\)=%%\s*%%=v\(FirstName\)=%%\s*%%=v\((?:MiddleName|Attribute1)\)=%%\s*!?",
    re.IGNORECASE,
)
_SPLIT_SFMC_GREETING_RE = re.compile(
    r"(<h2\b[^>]*>\s*<strong\b[^>]*>\s*)Здравствуйте,\s*(</strong>\s*</h2>\s*)"
    r"(<h2\b[^>]*>\s*<strong\b[^>]*>\s*)"
    r"%%=v\(@title\)=%%\s*%%=v\(FirstName\)=%%\s*%%=v\((?:MiddleName|Attribute1)\)=%%\s*"
    r"(</strong>\s*</h2>)",
    re.IGNORECASE,
)


def _map_recipient_field(field_name: str, params: ConversionParams) -> str:
    middle_field = "Attribute1" if params.personalization_mode == "manual" else "MiddleName"
    normalized = re.sub(r"[\s_\-]", "", field_name.lower())
    if normalized in {"title", "salutation", "obraschenie", "appeal"}:
        return "%%=v(@title)=%%"
    if normalized in {"firstname", "first", "name", "imya", "getname", "fullname"}:
        return "%%=v(FirstName)=%%"
    if normalized in {"middlename", "middle", "otchestvo", "patronymic", "secondname"}:
        return f"%%=v({middle_field})=%%"
    if normalized in {"lastname", "last", "surname", "familiya", "familyname"}:
        return "%%=v(LastName)=%%"
    return f"%%=v({middle_field})=%%"


def _personalization_replacements(params: ConversionParams) -> list[tuple[str, str | Callable[[re.Match[str]], str]]]:
    middle_field = "Attribute1" if params.personalization_mode == "manual" else "MiddleName"

    def map_recipient(match: re.Match[str]) -> str:
        return _map_recipient_field(match.group(1), params)

    return [
        (r"<span>\s*\$\{\s*Recipient\s*\.\s*Title\s*\}\s*</span>", "%%=v(@title)=%%"),
        (r"\$\{\s*Recipient\s*\.\s*Title\s*\}", "%%=v(@title)=%%"),
        (r"\$\{\s*Recipient\s*\.\s*FirstName\s*\}", "%%=v(FirstName)=%%"),
        (r"\$\{\s*Recipient\s*\.\s*MiddleName\s*\}", f"%%=v({middle_field})=%%"),
        (r"\$\{\s*Recipient\s*\.\s*LastName\s*\}", "%%=v(LastName)=%%"),
        (r"\$\{\s*Recipient\s*\.\s*(\w+)\s*\}", map_recipient),
        (r"%Recipient\.Title%", "%%=v(@title)=%%"),
        (r"%Recipient\.FirstName%", "%%=v(FirstName)=%%"),
        (r"%Recipient\.MiddleName%", f"%%=v({middle_field})=%%"),
        (r"%Recipient\.LastName%", "%%=v(LastName)=%%"),
        (r"(?<![(\w])@Title\b", "%%=v(@title)=%%"),
        (r"(?<![(\w])@FirstName\b", "%%=v(FirstName)=%%"),
        (r"(?<![(\w])@MiddleName\b", f"%%=v({middle_field})=%%"),
        (r"(?<![(\w])@LastName\b", "%%=v(LastName)=%%"),
    ]


_MINDBOX_GENDER_GREETING_RE = re.compile(
    r"@{\s*if\s+Recipient\.IsMale\s*}\s*Уважаемый\s*@{\s*else\s*}\s*Уважаемая\s*@{\s*end\s+if\s*}\s*"
    r"\$\{Recipient\.FirstAndMiddleName\}\s*!",
    re.IGNORECASE,
)


def _merge_split_sfmc_greeting(html: str, greeting: str) -> tuple[str, bool]:
    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{greeting}{match.group(4)}"

    updated, count = _SPLIT_SFMC_GREETING_RE.subn(repl, html)
    return updated, count > 0


def _replace_personalization(html: str, params: ConversionParams) -> tuple[str, bool]:
    result = html_lib.unescape(html)
    greeting = block4_personalization(params)
    changed = False

    merged, ok = _merge_split_sfmc_greeting(result, greeting)
    if ok:
        result = merged
        changed = True

    if _SFMC_GREETING_RE.search(result) and not re.search(r"@{\s*if\s+Recipient\.IsMale\s*}", result, re.IGNORECASE):
        return (result, True) if changed and result != html else (html, False)

    updated, count = re.subn(_MINDBOX_GENDER_GREETING_RE, greeting, result)
    if count:
        result = updated
        changed = True

    token_hits = 0
    for pattern, replacement in _personalization_replacements(params):
        if callable(replacement):
            updated, count = re.subn(pattern, replacement, result, flags=re.IGNORECASE)
        else:
            updated, count = re.subn(pattern, replacement, result, flags=re.IGNORECASE)
        if count:
            token_hits += count
            result = updated

    if token_hits:
        changed = True

    if _SFMC_GREETING_RE.search(result):
        return (result, True) if changed and result != html else (html, False)

    if re.search(r"@{\s*if\s+Recipient\.IsMale\s*}", result, re.IGNORECASE):
        return html, False
    if re.search(r"\$\{\s*Recipient\s*\.", result, re.IGNORECASE):
        return html, False

    if changed and result != html:
        return result, True

    fallback_patterns = [
        r"Здравствуйте(?:(?!!important)[\s\S])*?!(?!\w)",
        r"Добрый\s+день(?:(?!!important)[\s\S])*?!(?!\w)",
        r"Здравствуйте[\s\S]{0,800}?(?=</span>|</p>|</td>|</div>|</tr>|</h[1-6]|$)",
        r"Добрый\s+день[\s\S]{0,800}?(?=</span>|</p>|</td>|</div>|</tr>|</h[1-6]|$)",
        r"Уважаем(?:ый|ая)[\s\S]{0,400}?(?=</span>|</p>|</td>|</div>|</tr>|</h[1-6]|$)",
    ]
    for pattern in fallback_patterns:
        updated, count = re.subn(pattern, greeting, result, count=1, flags=re.IGNORECASE)
        if count and updated != result:
            return updated, True
    return html, False


def _should_apply_content_deeplink(url: str) -> bool:
    normalized = url.rstrip("/")
    lower = normalized.lower()
    if lower in {"https://docsfera.ru", "http://docsfera.ru"}:
        return False
    if any(token in lower for token in ("voting/cxq", "personal/unsubscribe", "unsubscribe")):
        return False
    if "/upload/" in lower or lower.endswith(".pdf"):
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


def _extract_cxq_rating(url: str) -> int:
    decoded = html_lib.unescape(url)
    match = re.search(r"(?:[?&]|&amp;)R=(\d)", decoded, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        return max(1, min(7, value))
    return 1


def _replace_cxq_block(html: str, params: ConversionParams) -> tuple[str, bool]:
    if not re.search(r"docsfera\.ru/voting/cxq", html, re.IGNORECASE):
        return html, False

    count = 0

    def replace_href(match: re.Match[str]) -> str:
        nonlocal count
        original = html_lib.unescape(match.group(3))
        rating = _extract_cxq_rating(original)
        new_url = build_cxq_url(params, rating, original_url=original) or original
        if new_url != original:
            count += 1
        return f"{match.group(1)}{match.group(2)}{new_url}{match.group(4)}"

    result = _CXQ_HREF_RE.sub(replace_href, html)

    if count == 0:
        def replace_bare(match: re.Match[str]) -> str:
            nonlocal count
            original = html_lib.unescape(match.group(0))
            rating = _extract_cxq_rating(original)
            new_url = build_cxq_url(params, rating, original_url=original)
            if new_url != original:
                count += 1
            return new_url

        result = _CXQ_URL_RE.sub(replace_bare, result)

    return result, count > 0


def _replace_qualtrics_cxq_block(html: str, params: ConversionParams) -> tuple[str, bool]:
    if not re.search(rf"{QUALTRICS_CXQ_HOST_RE}/jfe/form", html, re.IGNORECASE):
        return html, False

    count = 0

    def replace_href(match: re.Match[str]) -> str:
        nonlocal count
        original = html_lib.unescape(match.group(3))
        rating = _extract_cxq_rating(original)
        new_url = build_qualtrics_cxq_url(params, rating, original_url=original)
        if new_url and new_url != original:
            count += 1
        return f"{match.group(1)}{match.group(2)}{new_url or original}{match.group(4)}"

    result = _QUALTRICS_CXQ_HREF_RE.sub(replace_href, html)

    if count == 0:
        def replace_bare(match: re.Match[str]) -> str:
            nonlocal count
            original = html_lib.unescape(match.group(0))
            rating = _extract_cxq_rating(original)
            new_url = build_qualtrics_cxq_url(params, rating, original_url=original)
            if new_url and new_url != original:
                count += 1
            return new_url or original

        result = _QUALTRICS_CXQ_URL_RE.sub(replace_bare, result)

    return result, count > 0


def _replace_cxq_links(html: str, params: ConversionParams) -> tuple[str, bool]:
    uses_docsfera = bool(re.search(r"docsfera\.ru/voting/cxq", html, re.IGNORECASE))
    uses_qualtrics = bool(re.search(rf"{QUALTRICS_CXQ_HOST_RE}/jfe/form", html, re.IGNORECASE))

    result = html
    changed = False

    if uses_docsfera:
        result, ok = _replace_cxq_block(result, params)
        changed = changed or ok

    if uses_qualtrics:
        result, ok = _replace_qualtrics_cxq_block(result, params)
        changed = changed or ok

    return result, changed


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
    if 'alias="unsubscribe"' in anchor.lower() and "ContentBlockbyId" in anchor:
        return anchor
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
        if "RedirectTo(@UnsubscribeUrl)" in anchor:
            window = result[max(0, match.start() - 800): match.start()]
            if "ContentBlockbyId" in window:
                fixed = _ensure_unsubscribe_alias(anchor)
                if fixed != anchor:
                    result = result[: match.start()] + fixed + result[match.end() :]
                    count += 1
                continue
        if "RedirectTo(@UnsubscribeUrl)" in anchor and "ContentBlockbyId" in result[max(0, match.start() - 400): match.start()]:
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

    if "set @subscriberKey = _subscriberkey" in result and "SET @utm_campaign = __AdditionalEmailAttribute1" in result:
        warnings.append(
            "Файл уже содержит блоки SFMC (№1 и №2). Загрузите исходный Mindbox HTML, а не готовый SFMC."
        )
    elif "ContentBlockbyId(\"1649\")" in result and _SFMC_GREETING_RE.search(result):
        warnings.append(
            "Файл частично уже содержит SFMC-разметку (персонализация/отписка). Конвертер доведёт блоки до финального вида."
        )

    before = result
    result, ok = _replace_personalization(result, params)
    if ok and result != before:
        changes.append(f"Обновлена персонализация (режим: {params.personalization_mode})")
    elif not ok:
        warnings.append("Блок №4: не найдено приветствие для замены персонализации")

    before = result
    result, ok = _replace_view_in_browser(result)
    if ok and result != before:
        changes.append("Обновлена ссылка «сюда» (блок №3) — href без изменения вёрстки")
    elif not ok:
        warnings.append("Блок №3: не найден текст про некорректное отображение письма")

    result, strip_warnings = _strip_mindbox_artifacts(result)
    warnings.extend(strip_warnings)
    result = re.sub(
        r'<custom\s+name="opencounter"\s+type="tracking"\s*/?>',
        "",
        result,
        count=1,
        flags=re.IGNORECASE,
    )

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

    result, deeplink_count = _apply_all_docsfera_deeplinks(result)
    if deeplink_count:
        changes.append(
            f"Добавлен deeplink ContentBlock 1649 к {deeplink_count} ссылкам docsfera.ru "
            "(разметка и стили сохранены)"
        )
    else:
        warnings.append("Блок №4 (deeplink): ссылки docsfera.ru для обёртки не найдены")

    has_cxq = bool(
        re.search(rf"docsfera\.ru/voting/cxq|{QUALTRICS_CXQ_HOST_RE}/jfe/form", result, re.IGNORECASE)
    )
    if has_cxq:
        uses_docsfera = bool(re.search(r"docsfera\.ru/voting/cxq", result, re.IGNORECASE))
        if uses_docsfera:
            cn_values = re.findall(r"[?&]CN=([^\"'&\s<>]+)", result, re.IGNORECASE)
            needs_utm = any(v.lower() not in ("promo", "") for v in cn_values)
            if needs_utm and not params.utm_campaign and "utm_campaign=" not in result.lower():
                warnings.append(
                    "Блок №5: в docsfera CXQ может понадобиться utm_campaign (CN не promo). "
                    "Заполните utm_campaign, если нужно переопределить ссылки."
                )
        before = result
        result, ok = _replace_cxq_links(result, params)
        if ok and result != before:
            changes.append("Обновлены href в CXQ-ссылках (блок №5) — вёрстка сохранена")
        elif any([
            params.cxq_brand,
            params.cxq_da,
            params.cxq_ta,
            params.cxq_bu,
            params.cxq_cn,
            params.cxq_function,
            params.utm_campaign,
        ]):
            warnings.append("Блок №5: CXQ-ссылки не изменились — проверьте параметры формы")

    result, ok = _replace_unsubscribe(result)
    if ok:
        changes.append("Обновлен блок отписки (блок №6) — разметка ссылки сохранена")

    if params.data_extension != "Akamai_profiles_consents_bounced":
        warnings.append(
            f"Используется нестандартный источник данных: {params.data_extension}. "
            "Проверьте Lookup в блоке №1."
        )

    return ConversionResult(html=result, warnings=warnings, changes=changes)
