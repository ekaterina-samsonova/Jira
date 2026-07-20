"""Tests for Mindbox → SFMC converter."""

from pathlib import Path

from app.blocks import ConversionParams, build_cxq_url
from app.converter import convert_mindbox_to_sfmc
from app.validator import validate_sfmc_html

FIXTURE = Path(__file__).parent / "fixtures" / "sample_mindbox.html"


def test_convert_inserts_mandatory_blocks():
    html = FIXTURE.read_text(encoding="utf-8")
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="journey",
    )
    result = convert_mindbox_to_sfmc(html, params)

    assert "set @subscriberKey = _subscriberkey" in result.html
    assert "SET @utm_campaign = __AdditionalEmailAttribute1" in result.html
    assert 'href="%%view_email_url%%"' in result.html
    assert ">сюда</a>" in result.html
    assert "https://mindbox.ru/view-online" not in result.html
    assert "Start--Privacy Link goes here" in result.html
    assert "docsfera.ru/lectures/test-lecture" in result.html
    assert "Политика конфиденциальности" in result.html
    assert 'href="%%=RedirectTo(@UnsubscribeUrl)=%%"' in result.html
    assert "utm_campaign=Campaign_Test_Q2_2026" in result.html
    assert "Здравствуйте, %%=v(@title)=%% %%=v(FirstName)=%% %%=v(MiddleName)=%%!" in result.html
    assert "docsfera.ru/voting/cxq/" in result.html
    assert 'alias="unsubscribe"' in result.html
    assert "${Recipient.FirstName}" not in result.html
    assert "${Recipient.MiddleName}" not in result.html
    assert "${Recipient.Title}" not in result.html


def test_cxq_utm_campaign_omitted_for_promo():
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="promo",
    )
    url = build_cxq_url(params, 1)
    assert "utm_campaign" not in url
    assert "CN=promo" in url


def test_cxq_utm_campaign_included_for_journey():
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="journey",
    )
    url = build_cxq_url(params, 1)
    assert "utm_campaign=Campaign_Test_Q2_2026" in url


def test_digest_button_keeps_markup_with_deeplink():
    html = (Path(__file__).parent / "fixtures" / "digest_mindbox.html").read_text(encoding="utf-8")
    params = ConversionParams(
        utm_campaign="Campaign_CV_Praluent_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="journey",
    )
    result = convert_mindbox_to_sfmc(html, params)

    assert "Смотреть видео ▶" in result.html
    assert 'bgcolor="#8d236d"' in result.html
    assert "font-size: 18px" in result.html
    assert "Start--Privacy Link goes here" in result.html
    assert "RedirectTo(@UnsubscribeUrl)" in result.html
    assert "Здравствуйте, %%=v(@title)=%% %%=v(FirstName)=%% %%=v(MiddleName)=%%!" in result.html
    assert "${Recipient.FirstName}" not in result.html


def test_validate_after_conversion_passes():
    html = FIXTURE.read_text(encoding="utf-8")
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="journey",
    )
    converted = convert_mindbox_to_sfmc(html, params).html
    report = validate_sfmc_html(converted)
    errors = [i for i in report.issues if i.severity == "error"]
    assert not errors
