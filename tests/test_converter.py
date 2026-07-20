"""Tests for Mindbox → SFMC converter."""

from pathlib import Path

from app.blocks import ConversionParams
from app.converter import convert_mindbox_to_sfmc
from app.validator import validate_sfmc_html

FIXTURE = Path(__file__).parent / "fixtures" / "sample_mindbox.html"


def test_convert_inserts_mandatory_blocks():
    html = FIXTURE.read_text(encoding="utf-8")
    params = ConversionParams(
        privacy_url="https://docsfera.ru/lectures/test/",
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
    )
    result = convert_mindbox_to_sfmc(html, params)

    assert "set @subscriberKey = _subscriberkey" in result.html
    assert "SET @utm_campaign = __AdditionalEmailAttribute1" in result.html
    assert 'href="%%view_email_url%%"' in result.html
    assert "%%=v(@title)=%%" in result.html
    assert "docsfera.ru/voting/cxq/" in result.html
    assert 'alias="unsubscribe"' in result.html
    assert "${Recipient.FirstName}" not in result.html


def test_validate_after_conversion_passes():
    html = FIXTURE.read_text(encoding="utf-8")
    params = ConversionParams(
        privacy_url="https://docsfera.ru/lectures/test/",
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
    )
    converted = convert_mindbox_to_sfmc(html, params).html
    report = validate_sfmc_html(converted)
    errors = [i for i in report.issues if i.severity == "error"]
    assert not errors
