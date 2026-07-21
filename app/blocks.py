"""SFMC mandatory block templates for Mindbox → SFMC conversion."""

from __future__ import annotations

import html as html_lib
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversionParams:
    """User-supplied values for conversion."""

    data_extension: str = "Akamai_profiles_consents_bounced"
    personalization_mode: str = "de"  # "de" or "manual"
    privacy_url: str = ""
    utm_campaign: str = ""
    cxq_brand: str = ""
    cxq_da: str = ""
    cxq_ta: str = ""
    cxq_bu: str = ""
    cxq_function: str = ""
    cxq_cn: str = ""


CLIENT_ID = "tuedutmcfrbrbaet7gkcgw6xrs2hm3f4"
PRIVACY_CONTENT_BLOCK_ID = "1649"
CXQ_BASE_URL = "https://docsfera.ru/voting/cxq/"
QUALTRICS_CXQ_HOST_RE = r"(?:sanofidigital\.[^/]+|[^/]*qualtrics\.com)"
UNSUBSCRIBE_URL = "https://docsfera.ru/personal/unsubscribe/"


def block1(params: ConversionParams) -> str:
    de = params.data_extension
    return f"""%%[
set @subscriberKey = _subscriberkey
set @AkamaiID = Lookup("{de}","Akamai_uuid","Subscriberkey", @subscriberKey)
set @OneKeyID = Lookup("{de}","WRUM","Subscriberkey", @subscriberKey)
set @utms = concat('&utm_hcpid=', @OneKeyID, '&actid=', @AkamaiID, '&Q_Language=RU')
]%%"""


def block2() -> str:
    return """%%[ SET @utm_campaign = __AdditionalEmailAttribute1 ]%%
%%[ SET @utm_source = __AdditionalEmailAttribute2 ]%%
%%[set @SubscriberKey = _subscriberkey]%%
%%[set @EventDate = GetSendTime()]%%
%%[set @View_Link = view_email_url]%%
%%[set @Email_Id = _emailid]%%
%%[set @Email_Name = emailname_]%%
%%[set @Email_Log = emailaddr]%%
%%[set @rows = LookupRows("ENT.PROD_RUS_Metadata","CampaignCode",@utm_campaign)
set @rowCount = rowcount(@rows)
if @rowCount == 0 then
RaiseError('This campaign Code is not listed', false)
endif]%%
%%[set @rows = LookupRows("ENT.PROD_RUS_Metadata","ExposureCode", @utm_source)
set @rowCount = rowcount(@rows)
if @rowCount == 0 then
RaiseError('This exposure Code is not listed', false)
endif]%%
%%[if empty(__AdditionalEmailAttribute2) OR empty(__AdditionalEmailAttribute1) then
RaiseError('Ops, looks like you missed Campaign code or Exposure Code!', false)
else
set @combinationCount = LookupOrderedRows("ENT.PROD_RUS_Metadata",0,"CampaignCode asc","CampaignCode",@utm_campaign,"ExposureCode", @utm_source)
set @countOfCombo=rowcount(@combinationCount)
if @countOfCombo ==0 then
RaiseError('The combination of campaign code and exposure code entered is incorrect', false)
endif
endif]%%
      <custom name="opencounter" type="tracking">"""


def block3_link() -> str:
    return (
        '<a href="%%view_email_url%%" '
        'style="color:#b9b9b9; text-decoration:underline;" target="_blank">сюда</a>'
    )


def block4_personalization(params: ConversionParams) -> str:
    if params.personalization_mode == "manual":
        return "Здравствуйте, %%=v(@title)=%% %%=v(FirstName)=%% %%=v(Attribute1)=%%!"
    return "Здравствуйте, %%=v(@title)=%% %%=v(FirstName)=%% %%=v(MiddleName)=%%!"


def block4_privacy(privacy_url: str) -> str:
    return f"""<!-----Start--Privacy Link goes here---- >
                            %%[
                            /* The Marketers has to give the complete URL in @RedirectUri*/
                            set @RedirectUri='{privacy_url}'
                            set @ClientId='{CLIENT_ID}'
                            set @Website='https://docsfera.ru/'
                            ]%%
                            <!-----update link encoding id here ---->
                            %%=ContentBlockbyId("{PRIVACY_CONTENT_BLOCK_ID}")=%%
                            <!-----END---Privacy Link goes here ---->"""


def _cxq_query_param(url: str, name: str) -> str:
    match = re.search(rf"[?&]{re.escape(name)}=([^&\"']+)", url, re.IGNORECASE)
    return match.group(1) if match else ""


_CXQ_MAPPING: dict | None = None


def _load_cxq_mapping() -> dict:
    global _CXQ_MAPPING
    if _CXQ_MAPPING is None:
        path = Path(__file__).parent / "data" / "cxq_mapping.json"
        _CXQ_MAPPING = json.loads(path.read_text(encoding="utf-8"))
    return _CXQ_MAPPING


def _mapping_row_for_brand(brand: str) -> dict[str, str]:
    if not brand:
        return {}
    target = brand.strip().upper()
    for row in _load_cxq_mapping().get("rows", []):
        if str(row.get("Brand", "")).strip().upper() == target:
            return row
    return {}


def _cxq_form_input(params: ConversionParams) -> bool:
    return any([
        params.cxq_brand,
        params.cxq_da,
        params.cxq_ta,
        params.cxq_bu,
        params.cxq_cn,
        params.cxq_function,
    ])


def resolve_cxq_fields(params: ConversionParams) -> dict[str, str]:
    """Resolve CXQ fields from form values and brand mapping table (not from HTML)."""
    row = _mapping_row_for_brand(params.cxq_brand)

    def pick(param_value: str, row_key: str) -> str:
        if param_value:
            return param_value.strip()
        return str(row.get(row_key, "") or "").strip()

    brand = pick(params.cxq_brand, "Brand")
    da = pick(params.cxq_da, "DA")
    ta = pick(params.cxq_ta, "TA")
    bu = pick(params.cxq_bu, "BU")
    function = pick(params.cxq_function, "Function")
    cn = pick(params.cxq_cn, "CN")
    return {
        "brand": brand,
        "da": da,
        "ta": ta,
        "bu": bu,
        "function": function,
        "cn": cn,
    }


def _cxq_token(value: str) -> str:
    return value.replace(" ", "_")


def _docsfera_cxq_defaults(fields: dict[str, str]) -> dict[str, str]:
    result = dict(fields)
    if not result["bu"]:
        result["bu"] = "GENERAL_MEDICINES"
    if not result["function"]:
        result["function"] = "Commercial"
    if not result["cn"]:
        result["cn"] = "journey"
    return result


def _append_utm_campaign(url: str, utm_campaign: str) -> str:
    if not utm_campaign or "utm_campaign=" in url.lower():
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}utm_campaign={utm_campaign}"


def build_qualtrics_cxq_url(params: ConversionParams, rating: int, original_url: str = "") -> str:
    if not original_url:
        return ""

    decoded = html_lib.unescape(original_url)
    base = decoded.split("?", 1)[0]
    country = _cxq_query_param(decoded, "Country") or "RU"
    qlang = _cxq_query_param(decoded, "Q_Language") or "RU"

    if not _cxq_form_input(params):
        return decoded

    fields = _docsfera_cxq_defaults(resolve_cxq_fields(params))
    ta = _cxq_token(fields["ta"])
    bu = _cxq_token(fields["bu"])
    cn = fields["cn"]

    return f"{base}?Country={country}&Q_Language={qlang}&TA={ta}&BU={bu}&CN={cn}&R={rating}"


def build_cxq_url(params: ConversionParams, rating: int, original_url: str = "") -> str:
    if original_url:
        decoded = html_lib.unescape(original_url)
        original_cn = _cxq_query_param(decoded, "CN")
        utm_add = (
            params.utm_campaign
            and (params.cxq_cn or original_cn or "").lower() != "promo"
            and "utm_campaign" not in decoded.lower()
        )

        if not _cxq_form_input(params):
            if utm_add:
                return _append_utm_campaign(decoded, params.utm_campaign)
            return decoded

        fields = _docsfera_cxq_defaults(resolve_cxq_fields(params))
        brand = _cxq_token(fields["brand"])
        da = _cxq_token(fields["da"])
        ta = _cxq_token(fields["ta"])
        bu = _cxq_token(fields["bu"])
        function = _cxq_token(fields["function"])
        cn = fields["cn"]
        franchise = brand or da

        url = (
            f"{CXQ_BASE_URL}?Channel=email&R={rating}&Brand={brand}&DA={da}&TA={ta}"
            f"&Franchise={franchise}&BU={bu}&Function={function}&CN={cn}"
        )
        if cn.lower() != "promo" and params.utm_campaign:
            url += f"&utm_campaign={params.utm_campaign}"
        return url

    if not _cxq_form_input(params):
        return ""

    fields = _docsfera_cxq_defaults(resolve_cxq_fields(params))
    if not fields["brand"] or not fields["da"] or not fields["ta"]:
        return ""

    brand = _cxq_token(fields["brand"])
    da = _cxq_token(fields["da"])
    ta = _cxq_token(fields["ta"])
    bu = _cxq_token(fields["bu"])
    function = _cxq_token(fields["function"])
    cn = fields["cn"]
    franchise = brand or da
    url = (
        f"{CXQ_BASE_URL}?Channel=email&R={rating}&Brand={brand}&DA={da}&TA={ta}"
        f"&Franchise={franchise}&BU={bu}&Function={function}&CN={cn}"
    )
    if cn.lower() != "promo" and params.utm_campaign:
        url += f"&utm_campaign={params.utm_campaign}"
    return url


def block5_cxq(params: ConversionParams) -> str:
    links = []
    for rating in range(1, 8):
        url = build_cxq_url(params, rating)
        links.append(
            f'<a href="{url}" target="_blank" style="text-decoration:none;">{rating}</a>'
        )
    return (
        "<!-- CXQ block: Насколько информация в письме соответствовала вашим потребностям? -->\n"
        + "\n".join(links)
    )


def block6_unsubscribe_script() -> str:
    return f"""%%[
            /* The Marketers has to give the complete URL in @RedirectUri*/
            set @RedirectUri='{UNSUBSCRIBE_URL}'
            set @ClientId='{CLIENT_ID}'
            set @Website='https://docsfera.ru'
            ]%%
            %%=ContentBlockbyId("{PRIVACY_CONTENT_BLOCK_ID}")=%%"""


def block6_unsubscribe() -> str:
    return (
        block6_unsubscribe_script()
        + '\n<a alias="unsubscribe" href="%%=RedirectTo(@UnsubscribeUrl)=%%"'
    )


# Markers used by validator
BLOCK1_MARKERS = ["set @subscriberKey = _subscriberkey", "set @AkamaiID = Lookup"]
BLOCK2_MARKERS = [
    "SET @utm_campaign = __AdditionalEmailAttribute1",
    "SET @utm_source = __AdditionalEmailAttribute2",
    '<custom name="opencounter" type="tracking">',
]
BLOCK3_MARKERS = ['href="%%view_email_url%%"', ">сюда</a>"]
BLOCK4_PERSONALIZATION_MARKERS = ["%%=v(@title)=%%", "%%=v(FirstName)=%%"]
BLOCK4_PRIVACY_MARKERS = ["Start--Privacy Link goes here", 'ContentBlockbyId("1649")']
BLOCK5_MARKERS = ["docsfera.ru/voting/cxq/", "qualtrics.com/jfe/form", "sanofidigital"]
BLOCK6_MARKERS = [
    "docsfera.ru/personal/unsubscribe/",
    'alias="unsubscribe"',
    "RedirectTo(@UnsubscribeUrl)",
]

MINDBOX_PATTERNS = [
    r"\$\{[^}]+\}",
    r"%%\[.*Mindbox.*\]%%",
    r"mindbox",
    r"Recipient\.",
    r"Email\.Message",
]
