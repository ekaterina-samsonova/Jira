"""Tests for Mindbox → SFMC converter."""

from pathlib import Path

from app.blocks import ConversionParams, build_cxq_url
from app.converter import convert_mindbox_to_sfmc, _replace_cxq_block
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
    assert "%%=v(@title)=%%" in result.html
    assert "%%=v(FirstName)=%%" in result.html
    assert "%%=v(MiddleName)=%%" in result.html
    assert "%%=v(%%=v(@title)=%%)=%%" not in result.html
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
    assert "%%=v(@title)=%%" in result.html
    assert "%%=v(FirstName)=%%" in result.html
    assert "%%=v(MiddleName)=%%" in result.html
    assert "%%=v(%%=v(@title)=%%)=%%" not in result.html
    assert "${Recipient.FirstName}" not in result.html


def test_multiple_cta_links_keep_visuals():
    html = """<!DOCTYPE html><html><head></head><body>
    <a href="https://docsfera.ru/lectures/alpha/" style="color:red;font-size:20px">CTA Alpha</a>
    <table><tr><td bgcolor="#111"><a href="https://docsfera.ru/lectures/beta/" class="btn">CTA Beta</a></td></tr></table>
    <a href="https://docsfera.ru/lectures/alpha/" style="color:blue">CTA Alpha copy</a>
    <p>Насколько информация в письме соответствовала вашим потребностям?</p>
    <a class="score-link" href="https://docsfera.ru/voting/cxq/?R=1">1</a>
    <a href="https://docsfera.ru/personal/unsubscribe/">отписаться</a>
    </body></html>"""
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="journey",
    )
    result = convert_mindbox_to_sfmc(html, params)

    assert result.html.count("RedirectTo(@UnsubscribeUrl)") >= 3
    assert 'style="color:red;font-size:20px"' in result.html
    assert 'class="btn"' in result.html
    assert 'style="color:blue"' in result.html
    assert "CTA Alpha" in result.html
    assert "CTA Beta" in result.html
    assert 'class="score-link"' in result.html
    assert "Brand=PRALUENT" in result.html


def test_view_online_preserves_anchor_markup():
    html = """<!DOCTYPE html><html><head></head><body>
    <span>Если данное письмо отображается некорректно, нажмите
    <a href="https://mindbox.example/view" style="color:#8e136d;" target="_blank"><span>сюда</span></a>.</span>
    </body></html>"""
    result = convert_mindbox_to_sfmc(html, ConversionParams()).html
    assert 'href="%%view_email_url%%"' in result
    assert 'style="color:#8e136d;"' in result
    assert "<span>сюда</span>" in result


def test_cxq_without_slash_before_query():
    html = '<a href="https://docsfera.ru/voting/cxq?R=3&Brand=OLD">3</a>'
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
    )
    result, ok = _replace_cxq_block(html, params)
    assert ok
    assert "Brand=PRALUENT" in result
    assert "Brand=OLD" not in result


def test_cxq_with_html_entities():
    html = '<a href="https://docsfera.ru/voting/cxq/?Channel=email&amp;R=4&amp;Brand=OLD">4</a>'
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
    )
    result, ok = _replace_cxq_block(html, params)
    assert ok
    assert "R=4" in result
    assert "Brand=PRALUENT" in result


def test_personalization_mindbox_variants():
    from app.converter import _replace_personalization

    params = ConversionParams()
    cases = [
        ("Здравствуйте, ${ recipient.firstName }!", "%%=v(FirstName)=%%"),
        ("Здравствуйте, @Title @FirstName @MiddleName!", "%%=v(@title)=%%"),
        ("Здравствуйте, ${Recipient.CustomField}!", "%%=v(MiddleName)=%%"),
    ]
    for source, expected in cases:
        out, ok = _replace_personalization(source, params)
        assert ok, source
        assert expected in out, source


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


def test_digest_immuno_gender_greeting_and_cxq():
    html = (
        Path(__file__).parent / "fixtures" / "Digest_immuno_14_2026_mindbox_8d26.html"
    ).read_text(encoding="utf-8")
    params = ConversionParams(
        cxq_brand="DUPIXENT",
        cxq_da="CHRONIC_RHINOSINUSITIS_WITH_NASAL_POLYPS(CRSwNP)",
        cxq_ta="IMMUNOLOGY",
        cxq_bu="SPECIALTY_CARE",
        cxq_cn="promo",
    )
    result = convert_mindbox_to_sfmc(html, params).html

    assert "Здравствуйте, %%=v(@title)=%% %%=v(FirstName)=%% %%=v(MiddleName)=%%!" in result
    assert "Recipient.IsMale" not in result
    assert '${Recipient.FirstAndMiddleName}' not in result
    assert 'href="https://docsfera.ru/upload/ohlp/open-no-index/ohlp-dupilumab-2026.pdf"' in result
    assert "Function=Commercial&CN=promo" in result
    assert "Function=Medical&CN=promo" in result
    assert "utm_campaign" not in result.split("voting/cxq", 1)[1][:800]
    assert 'alias="unsubscribe" href="%%=RedirectTo(@UnsubscribeUrl)=%%"' in result


def test_digest_onco_research_deeplinks_and_cxq_casing():
    html = (
        Path(__file__).parent / "fixtures" / "Digest_onco_16_2026_mindbox_daa7.html"
    ).read_text(encoding="utf-8")
    params = ConversionParams(
        cxq_brand="REZTIREG",
        cxq_da="chronic_GVHD",
        cxq_ta="TRANSPLANT",
        cxq_bu="SPECIALTY_CARE",
        cxq_cn="promo",
    )
    result = convert_mindbox_to_sfmc(html, params).html

    assert "Здравствуйте, %%=v(@title)=%%" in result
    assert "DA=chronic_GVHD" in result
    assert "Franchise=TRANSPLANT" in result
    assert result.count("RedirectTo(@UnsubscribeUrl)") >= 2
    assert "research/novosti_8_go_mezhdunarodnogo_simpoziuma" in result
    assert "research/shkola_aktualnye_voprosy_transplantatsii" in result


def test_cxq_franchise_fallback_from_form_params():
    params = ConversionParams(
        utm_campaign="Campaign_Test_Q2_2026",
        cxq_brand="PRALUENT",
        cxq_da="DYSLIPIDEMIA",
        cxq_ta="CARDIOLOGY",
        cxq_cn="journey",
    )
    url = build_cxq_url(params, 1, original_url="https://docsfera.ru/voting/cxq/?R=1")
    assert "Franchise=PRALUENT" in url
    assert "Brand=PRALUENT" in url
