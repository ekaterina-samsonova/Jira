"""SFMC mandatory block templates for Mindbox → SFMC conversion."""

from __future__ import annotations

from dataclasses import dataclass


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
    cxq_bu: str = "GENERAL MEDICINES"
    cxq_function: str = "Commercial"
    cxq_cn: str = "journey"


CLIENT_ID = "tuedutmcfrbrbaet7gkcgw6xrs2hm3f4"
PRIVACY_CONTENT_BLOCK_ID = "1649"
CXQ_BASE_URL = "https://docsfera.ru/voting/cxq/"
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
    return "Здравствуйте,%%=v(@title)=%% %%=v(FirstName)=%% %%=v(MiddleName)=%%"


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


def build_cxq_url(params: ConversionParams, rating: int) -> str:
    brand = params.cxq_brand.replace(" ", "_").upper()
    da = params.cxq_da.replace(" ", "_").upper()
    ta = params.cxq_ta.replace(" ", "_").upper()
    franchise = da
    bu = params.cxq_bu.replace(" ", "_").upper()
    function = params.cxq_function.replace(" ", "_")
    cn = params.cxq_cn
    campaign = params.utm_campaign
    return (
        f"{CXQ_BASE_URL}?Channel=email&R={rating}&Brand={brand}&DA={da}&TA={ta}"
        f"&Franchise={franchise}&BU={bu}&Function={function}&CN={cn}"
        f"&utm_campaign={campaign}"
    )


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


def block6_unsubscribe() -> str:
    return f"""%%[
            /* The Marketers has to give the complete URL in @RedirectUri*/
            set @RedirectUri='{UNSUBSCRIBE_URL}'
            set @ClientId='{CLIENT_ID}'
            set @Website='https://docsfera.ru'
            ]%%
            %%=ContentBlockbyId("{PRIVACY_CONTENT_BLOCK_ID}")=%%
              <a alias="unsubscribe" href="%%=RedirectTo(@UnsubscribeUrl)=%%\""""


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
BLOCK5_MARKERS = ["docsfera.ru/voting/cxq/", "Channel=email"]
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
