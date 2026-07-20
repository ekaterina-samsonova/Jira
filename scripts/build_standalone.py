#!/usr/bin/env python3
"""Build standalone offline HTML converter."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CXQ_PATH = ROOT / "app" / "data" / "cxq_mapping.json"
OUT_PATH = ROOT / "dist" / "Mindbox-to-SFMC-Converter.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mindbox → SFMC Converter</title>
  <style>
    :root {{
      --bg:#eef2f8; --surface:#fff; --text:#0f172a; --muted:#64748b; --line:#dbe3ef;
      --primary:#2563eb; --success:#059669; --warning:#d97706; --error:#dc2626;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Segoe UI,Inter,sans-serif; background:var(--bg); color:var(--text); }}
    .wrap {{ max-width:1100px; margin:0 auto; padding:24px; }}
    .hero {{ background:linear-gradient(135deg,#0f172a,#1e3a8a); color:#fff; border-radius:16px; padding:24px; margin-bottom:20px; }}
    .hero h1 {{ margin:0 0 8px; font-size:28px; }}
    .hero p {{ margin:0; color:#cbd5e1; }}
    .badge {{ display:inline-block; background:#22c55e; color:#052e16; font-size:12px; font-weight:700; padding:4px 10px; border-radius:999px; margin-bottom:10px; }}
    .card {{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:20px; margin-bottom:16px; }}
    .card h2 {{ margin:0 0 8px; font-size:20px; }}
    .card p {{ margin:0 0 16px; color:var(--muted); }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    label {{ display:flex; flex-direction:column; gap:6px; font-size:14px; font-weight:600; }}
    label small {{ font-weight:400; color:var(--muted); }}
    input, select {{ padding:10px 12px; border:1px solid var(--line); border-radius:10px; font:inherit; }}
    .wide {{ grid-column:1/-1; }}
    .upload {{ border:2px dashed #c7d2e4; border-radius:14px; padding:28px; text-align:center; background:#f8fafc; }}
    .upload.drag {{ border-color:var(--primary); background:#eff6ff; }}
    .file-info {{ margin-top:12px; padding:12px; background:#f8fafc; border-radius:10px; font-weight:600; word-break:break-all; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }}
    .btn {{ border:none; border-radius:10px; padding:11px 16px; font:inherit; font-weight:700; cursor:pointer; }}
    .btn-primary {{ background:var(--primary); color:#fff; }}
    .btn-secondary {{ background:#e2e8f0; }}
    .btn-success {{ background:var(--success); color:#fff; }}
    .btn:disabled {{ opacity:.55; cursor:not-allowed; }}
    .alert {{ padding:12px 14px; border-radius:10px; margin-bottom:16px; font-weight:600; }}
    .alert.hidden {{ display:none; }}
    .alert.error {{ background:#fee2e2; color:#991b1b; }}
    .alert.success {{ background:#dcfce7; color:#166534; }}
    .alert.info {{ background:#dbeafe; color:#1e40af; }}
    .issue {{ border-left:4px solid var(--muted); background:#fff; padding:10px 12px; border-radius:8px; margin-bottom:8px; }}
    .issue.error {{ border-color:var(--error); }}
    .issue.warning {{ border-color:var(--warning); }}
    .issue.info {{ border-color:var(--primary); }}
    .issue .meta {{ font-size:11px; color:var(--muted); text-transform:uppercase; }}
    .issue .msg {{ font-weight:700; margin-top:4px; }}
    .issue .hint, .issue .snippet {{ font-size:13px; color:var(--muted); margin-top:4px; }}
    pre {{ white-space:pre-wrap; word-break:break-word; max-height:360px; overflow:auto; background:#111827; color:#f8fafc; padding:14px; border-radius:10px; font-size:12px; }}
    @media (max-width:800px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="badge">Работает без сервера</div>
      <h1>Mindbox → SFMC Converter</h1>
      <p>Сохраните этот файл на компьютер и откройте двойным кликом в браузере. Сервер и терминал не нужны.</p>
    </div>

    <div id="alert" class="alert hidden"></div>

    <div class="card">
      <h2>1. Загрузите HTML Mindbox</h2>
      <p>Выберите файл .html с «Mindbox» в названии.</p>
      <div class="upload" id="upload">
        <p><b>Перетащите файл сюда</b> или нажмите кнопку ниже</p>
        <input type="file" id="file-input" accept=".html,.htm,text/html" hidden>
        <div class="actions" style="justify-content:center;">
          <button type="button" class="btn btn-secondary" id="browse-btn">Выбрать файл</button>
        </div>
        <div class="file-info hidden" id="file-info"></div>
      </div>
    </div>

    <div class="card">
      <h2>2. Параметры</h2>
      <div class="grid">
        <label>Data Extension (блок №1)
          <input id="data_extension" value="Akamai_profiles_consents_bounced">
        </label>
        <label>Режим персонализации
          <select id="personalization_mode">
            <option value="de">DE Akamai — MiddleName</option>
            <option value="manual">Ручная выгрузка — Attribute1</option>
          </select>
        </label>
        <label>Privacy URL
          <input id="privacy_url" placeholder="https://docsfera.ru/lectures/...">
        </label>
        <label>utm_campaign *
          <input id="utm_campaign" placeholder="Campaign_CV_Praluent_Q2_2026">
        </label>
        <label class="wide">Поиск Brand
          <input id="brand_search" placeholder="Начните вводить бренд...">
        </label>
        <label>Brand *
          <select id="cxq_brand" size="6"></select>
        </label>
        <label>DA *
          <input id="cxq_da" list="da-list">
          <datalist id="da-list"></datalist>
        </label>
        <label>TA *
          <input id="cxq_ta" list="ta-list">
          <datalist id="ta-list"></datalist>
        </label>
        <label>BU
          <select id="cxq_bu"></select>
        </label>
        <label>Function
          <select id="cxq_function"></select>
        </label>
        <label>CN
          <select id="cxq_cn"></select>
        </label>
      </div>
      <div class="actions">
        <button type="button" class="btn btn-secondary" id="validate-btn">Только проверить</button>
        <button type="button" class="btn btn-primary" id="convert-btn">Конвертировать</button>
        <button type="button" class="btn btn-success" id="download-btn" disabled>Скачать SFMC HTML</button>
      </div>
    </div>

    <div class="card">
      <h2>3. Результат</h2>
      <div id="changes"></div>
      <div id="warnings"></div>
      <div id="validation"><p style="color:var(--muted);">Результаты появятся после проверки или конвертации.</p></div>
      <details id="preview-wrap" style="margin-top:12px;" hidden>
        <summary>Показать HTML-код</summary>
        <pre id="preview"></pre>
      </details>
    </div>
  </div>

  <script>
    const CXQ = __CXQ_JSON__;

    const CLIENT_ID = "tuedutmcfrbrbaet7gkcgw6xrs2hm3f4";
    const PRIVACY_CONTENT_BLOCK_ID = "1649";
    const CXQ_BASE_URL = "https://docsfera.ru/voting/cxq/";
    const UNSUBSCRIBE_URL = "https://docsfera.ru/personal/unsubscribe/";

    let selectedFile = null;
    let convertedHtml = null;
    let outputFilename = "email_SFMC.html";

    const els = {{
      alert: document.getElementById("alert"),
      upload: document.getElementById("upload"),
      fileInput: document.getElementById("file-input"),
      browseBtn: document.getElementById("browse-btn"),
      fileInfo: document.getElementById("file-info"),
      brandSearch: document.getElementById("brand_search"),
      brandSelect: document.getElementById("cxq_brand"),
      changes: document.getElementById("changes"),
      warnings: document.getElementById("warnings"),
      validation: document.getElementById("validation"),
      previewWrap: document.getElementById("preview-wrap"),
      preview: document.getElementById("preview"),
      downloadBtn: document.getElementById("download-btn"),
    }};

    function getParams() {{
      return {{
        data_extension: document.getElementById("data_extension").value.trim(),
        personalization_mode: document.getElementById("personalization_mode").value,
        privacy_url: document.getElementById("privacy_url").value.trim(),
        utm_campaign: document.getElementById("utm_campaign").value.trim(),
        cxq_brand: document.getElementById("cxq_brand").value.trim(),
        cxq_da: document.getElementById("cxq_da").value.trim(),
        cxq_ta: document.getElementById("cxq_ta").value.trim(),
        cxq_bu: document.getElementById("cxq_bu").value.trim() || "GENERAL MEDICINES",
        cxq_function: document.getElementById("cxq_function").value.trim() || "Commercial",
        cxq_cn: document.getElementById("cxq_cn").value.trim() || "journey",
      }};
    }}

    function block1(p) {{
      return `%%[\\nset @subscriberKey = _subscriberkey\\nset @AkamaiID = Lookup("${{p.data_extension}}","Akamai_uuid","Subscriberkey", @subscriberKey)\\nset @OneKeyID = Lookup("${{p.data_extension}}","WRUM","Subscriberkey", @subscriberKey)\\nset @utms = concat('&utm_hcpid=', @OneKeyID, '&actid=', @AkamaiID, '&Q_Language=RU')\\n]%%`;
    }}

    function block2() {{
      return `%%[ SET @utm_campaign = __AdditionalEmailAttribute1 ]%%\\n%%[ SET @utm_source = __AdditionalEmailAttribute2 ]%%\\n%%[set @SubscriberKey = _subscriberkey]%%\\n%%[set @EventDate = GetSendTime()]%%\\n%%[set @View_Link = view_email_url]%%\\n%%[set @Email_Id = _emailid]%%\\n%%[set @Email_Name = emailname_]%%\\n%%[set @Email_Log = emailaddr]%%\\n%%[set @rows = LookupRows("ENT.PROD_RUS_Metadata","CampaignCode",@utm_campaign)\\nset @rowCount = rowcount(@rows)\\nif @rowCount == 0 then\\nRaiseError('This campaign Code is not listed', false)\\nendif]%%\\n%%[set @rows = LookupRows("ENT.PROD_RUS_Metadata","ExposureCode", @utm_source)\\nset @rowCount = rowcount(@rows)\\nif @rowCount == 0 then\\nRaiseError('This exposure Code is not listed', false)\\nendif]%%\\n%%[if empty(__AdditionalEmailAttribute2) OR empty(__AdditionalEmailAttribute1) then\\nRaiseError('Ops, looks like you missed Campaign code or Exposure Code!', false)\\nelse\\nset @combinationCount = LookupOrderedRows("ENT.PROD_RUS_Metadata",0,"CampaignCode asc","CampaignCode",@utm_campaign,"ExposureCode", @utm_source)\\nset @countOfCombo=rowcount(@combinationCount)\\nif @countOfCombo ==0 then\\nRaiseError('The combination of campaign code and exposure code entered is incorrect', false)\\nendif\\nendif]%%\\n      <custom name="opencounter" type="tracking">`;
    }}

    function block3Link() {{
      return '<a href="%%view_email_url%%" style="color:#b9b9b9; text-decoration:underline;" target="_blank">сюда</a>';
    }}

    function block4Personalization(p) {{
      return p.personalization_mode === "manual"
        ? "Здравствуйте, %%=v(@title)=%% %%=v(FirstName)=%% %%=v(Attribute1)=%%!"
        : "Здравствуйте,%%=v(@title)=%% %%=v(FirstName)=%% %%=v(MiddleName)=%%";
    }}

    function block4Privacy(url) {{
      return `<!-----Start--Privacy Link goes here---- >\\n%%[\\nset @RedirectUri='${{url}}'\\nset @ClientId='${{CLIENT_ID}}'\\nset @Website='https://docsfera.ru/'\\n]%%\\n%%=ContentBlockbyId("${{PRIVACY_CONTENT_BLOCK_ID}}")=%%\\n<!-----END---Privacy Link goes here ---->`;
    }}

    function buildCxqUrl(p, rating) {{
      const enc = (v) => encodeURIComponent(String(v).replace(/ /g, "_").toUpperCase());
      return `${{CXQ_BASE_URL}}?Channel=email&R=${{rating}}&Brand=${{enc(p.cxq_brand)}}&DA=${{enc(p.cxq_da)}}&TA=${{enc(p.cxq_ta)}}&Franchise=${{enc(p.cxq_da)}}&BU=${{enc(p.cxq_bu)}}&Function=${{encodeURIComponent(p.cxq_function.replace(/ /g, "_"))}}&CN=${{encodeURIComponent(p.cxq_cn)}}&utm_campaign=${{encodeURIComponent(p.utm_campaign)}}`;
    }}

    function block5Cxq(p) {{
      return "<!-- CXQ block -->\\n" + Array.from({{length:7}}, (_, i) => {{
        const r = i + 1;
        return `<a href="${{buildCxqUrl(p, r)}}" target="_blank" style="text-decoration:none;">${{r}}</a>`;
      }}).join("\\n");
    }}

    function block6Unsubscribe() {{
      return `%%[\\nset @RedirectUri='${{UNSUBSCRIBE_URL}}'\\nset @ClientId='${{CLIENT_ID}}'\\nset @Website='https://docsfera.ru'\\n]%%\\n%%=ContentBlockbyId("${{PRIVACY_CONTENT_BLOCK_ID}}")=%%\\n<a alias="unsubscribe" href="%%=RedirectTo(@UnsubscribeUrl)=%%"`;
    }}

    function insertBeforeDoctype(html, snippet) {{
      const m = html.match(/(<!DOCTYPE|<html)/i);
      if (!m) return snippet + "\\n" + html;
      return html.slice(0, m.index) + snippet + "\\n" + html.slice(m.index);
    }}

    function insertAfterHead(html, snippet) {{
      const m = html.match(/<\\/head>/i);
      if (!m) return html;
      const idx = m.index + m[0].length;
      return html.slice(0, idx) + "\\n" + snippet + "\\n" + html.slice(idx);
    }}

    function convertMindboxToSfmc(html, p) {{
      const warnings = [];
      const changes = [];
      let result = html;

      result = result.replace(/<!--\\s*Mindbox[\\s\\S]*?-->/gi, "");
      result = result.replace(/<script[^>]*mindbox[^>]*>[\\s\\S]*?<\\/script>/gi, "");
      result = result.replace(/\\$\\{{Recipient\\.[^}}]+\\}}/gi, "");
      result = result.replace(/\\$\\{{Message\\.[^}}]+\\}}/gi, "");

      if (!result.includes("set @subscriberKey = _subscriberkey")) {{
        result = insertBeforeDoctype(result, block1(p));
        changes.push(`Добавлен блок №1 (DE: ${{p.data_extension}})`);
      }}

      if (!result.includes("SET @utm_campaign = __AdditionalEmailAttribute1")) {{
        const updated = insertAfterHead(result, block2());
        if (updated === result) warnings.push("Не найден </head> — блок №2 не вставлен");
        else {{ result = updated; changes.push("Добавлен блок №2"); }}
      }}

      const link = block3Link();
      let m;
      if ((m = result.match(/(Если данное письмо отображается некорректно[^<]*)(?:нажмите\\s+)?(сюда)/i))) {{
        result = result.replace(m[0], m[1] + link);
        changes.push("Обновлена ссылка «сюда» (блок №3)");
      }} else {{
        warnings.push("Блок №3: не найден текст про некорректное отображение");
      }}

      const greeting = block4Personalization(p);
      const persPatterns = [/Здравствуйте[^!<\\n]{{0,120}}!?/i, /Добрый\\s+день[^!<\\n]{{0,120}}!?/i, /\\$\\{{Recipient\\.[^}}]+\\}}/i, /\\{\\{[^}}]+\\}\\}/];
      let replacedPers = false;
      for (const rx of persPatterns) {{
        if (rx.test(result)) {{ result = result.replace(rx, greeting); replacedPers = true; break; }}
      }}
      if (replacedPers) changes.push("Обновлена персонализация (блок №4)");
      else warnings.push("Блок №4: не найдено приветствие");

      if (p.privacy_url) {{
        if (result.includes("Start--Privacy Link goes here")) {{
          result = result.replace(/<!-----Start--Privacy Link goes here[\\s\\S]*?<!-----END---Privacy Link goes here ---->/i, block4Privacy(p.privacy_url));
        }} else if (/<\\/body>/i.test(result)) {{
          result = result.replace(/<\\/body>/i, block4Privacy(p.privacy_url) + "\\n</body>");
        }} else {{
          result += "\\n" + block4Privacy(p.privacy_url);
        }}
        changes.push("Обновлен Privacy Link");
      }}

      if (p.utm_campaign && p.cxq_brand) {{
        const cxqBlock = block5Cxq(p);
        const section = /(Насколько\\s+информация\\s+в\\s+письме\\s+соответствовала\\s+вашим\\s+потребностям\\?)[\\s\\S]{{0,4000}}?(?=<\\/td>|<\\/tr>|<\\/table>|<\\/body>|$)/i;
        if (section.test(result)) {{
          result = result.replace(section, `$1\\n${{cxqBlock}}`);
          changes.push("Обновлен CXQ-блок (блок №5)");
        }} else {{
          warnings.push("Блок №5: CXQ-секция не найдена");
        }}
      }} else {{
        warnings.push("Блок №5: укажите utm_campaign и Brand");
      }}

      const unsub = block6Unsubscribe();
      if (/<a[^>]*отпис[^>]*>[\\s\\S]*?<\\/a>/i.test(result)) {{
        result = result.replace(/<a[^>]*отпис[^>]*>[\\s\\S]*?<\\/a>/i, unsub);
      }} else if (/<\\/body>/i.test(result)) {{
        result = result.replace(/<\\/body>/i, unsub + "\\n</body>");
      }} else {{
        result += "\\n" + unsub;
      }}
      changes.push("Обновлен блок отписки (блок №6)");

      if (p.data_extension !== "Akamai_profiles_consents_bounced") {{
        warnings.push(`Нестандартный DE: ${{p.data_extension}} — проверьте блок №1`);
      }}

      return {{ html: result, warnings, changes }};
    }}

    function validateSfmcHtml(html) {{
      const issues = [];
      const add = (block, severity, message, hint="", snippet="") => {{
        issues.push({{ block, severity, message, hint, snippet }});
      }};

      const req = (block, markers) => {{
        const missing = markers.filter((m) => !html.includes(m));
        if (missing.length) add(block, "error", `Отсутствуют элементы: ${{missing.slice(0,3).join(", ")}}`, `Проверьте ${{block}}`);
      }};

      req("Блок №1", ["set @subscriberKey = _subscriberkey", "set @AkamaiID = Lookup"]);
      req("Блок №2", ["SET @utm_campaign = __AdditionalEmailAttribute1", "SET @utm_source = __AdditionalEmailAttribute2", '<custom name="opencounter" type="tracking">']);
      req("Блок №3", ['href="%%view_email_url%%"', ">сюда</a>"]);
      req("Блок №4", ["%%=v(@title)=%%", "%%=v(FirstName)=%%"]);
      req("Блок №6", ["docsfera.ru/personal/unsubscribe/", 'alias="unsubscribe"', "RedirectTo(@UnsubscribeUrl)"]);

      if (!html.includes("docsfera.ru/voting/cxq/")) add("Блок №5", "error", "CXQ-блок не найден", "Добавьте ссылки docsfera.ru/voting/cxq/");
      else {{
        const urls = html.match(/https?:\\/\\/docsfera\\.ru\\/voting\\/cxq\\/\\?[^"'\\s<>]+/gi) || [];
        const ratings = new Set();
        urls.forEach((url) => {{
          const rm = url.match(/[?&]R=(\\d)/i);
          if (rm) ratings.add(Number(rm[1]));
        }});
        if (ratings.size < 7) add("Блок №5", "warning", `Найдено оценок R: ${{[...ratings].sort()}} — нужно 7`, "Каждая кнопка R=1..7");
      }}

      const body = (html.match(/<body[^>]*>([\\s\\S]*)<\\/body>/i) || [])[1] || html;
      if (/\\$\\{{[^}}]*\\}}|Recipient\\.|Email\\.Message/i.test(body)) {{
        add("Mindbox", "error", "Остались Mindbox-токены", "Замените на SFMC AMPscript");
      }}

      const ok = !issues.some((i) => i.severity === "error");
      return {{ ok, issues }};
    }}

    function showAlert(text, type="info") {{
      els.alert.textContent = text;
      els.alert.className = `alert ${{type}}`;
    }}

    function renderList(el, title, items, cls) {{
      if (!items.length) {{ el.innerHTML = ""; return; }}
      el.innerHTML = `<h3>${{title}}</h3>` + items.map((t) => `<div class="issue ${{cls}}"><div class="msg">${{escapeHtml(t)}}</div></div>`).join("");
    }}

    function renderValidation(report, label) {{
      if (!report.issues.length) {{
        els.validation.innerHTML = `<h3>${{label}}: без ошибок</h3><p style="color:var(--muted)">Все обязательные блоки на месте.</p>`;
        return;
      }}
      els.validation.innerHTML = `<h3>${{label}}: ${{report.ok ? "есть предупреждения" : "есть ошибки"}}</h3>` +
        report.issues.map((i) => `<div class="issue ${{i.severity}}"><div class="meta">${{escapeHtml(i.block)}} · ${{i.severity}}</div><div class="msg">${{escapeHtml(i.message)}}</div>${{i.hint ? `<div class="hint">${{escapeHtml(i.hint)}}</div>` : ""}}${{i.snippet ? `<div class="snippet"><code>${{escapeHtml(i.snippet)}}</code></div>` : ""}}</div>`).join("");
    }}

    function escapeHtml(v) {{
      return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
    }}

    function validateForm() {{
      if (!selectedFile) {{ showAlert("Сначала выберите HTML-файл", "error"); return false; }}
      const p = getParams();
      if (!p.utm_campaign || !p.cxq_brand || !p.cxq_da || !p.cxq_ta) {{
        showAlert("Заполните utm_campaign, Brand, DA и TA", "error");
        return false;
      }}
      return true;
    }}

    async function readSelectedFile() {{
      return await selectedFile.text();
    }}

    function populateSelect(id, values, fallback) {{
      const el = document.getElementById(id);
      const unique = [...new Set((values || []).filter(Boolean))];
      if (!unique.length && fallback) unique.push(fallback);
      el.innerHTML = unique.map((v) => `<option value="${{escapeHtml(v)}}">${{escapeHtml(v)}}</option>`).join("");
      if (fallback && unique.includes(fallback)) el.value = fallback;
    }}

    function renderBrands(list) {{
      els.brandSelect.innerHTML = list.map((b) => `<option value="${{escapeHtml(b)}}">${{escapeHtml(b)}}</option>`).join("");
    }}

    function applyBrandDefaults() {{
      const brand = els.brandSelect.value;
      const rows = CXQ.rows.filter((r) => r.Brand === brand);
      if (!rows.length) return;
      const row = rows[0];
      document.getElementById("cxq_da").value = row.DA || "";
      document.getElementById("cxq_ta").value = row.TA || "";
      if (row.BU) document.getElementById("cxq_bu").value = row.BU;
      if (row.Function) document.getElementById("cxq_function").value = row.Function;
      if (row.CN) document.getElementById("cxq_cn").value = row.CN;
      const das = [...new Set(rows.map((r) => r.DA).filter(Boolean))];
      const tas = [...new Set(rows.map((r) => r.TA).filter(Boolean))];
      document.getElementById("da-list").innerHTML = das.map((v) => `<option value="${{escapeHtml(v)}}"></option>`).join("");
      document.getElementById("ta-list").innerHTML = tas.map((v) => `<option value="${{escapeHtml(v)}}"></option>`).join("");
    }}

    function setFile(file) {{
      if (!file) return;
      selectedFile = file;
      els.fileInfo.textContent = "Выбран: " + file.name;
      els.fileInfo.classList.remove("hidden");
      if (!file.name.toLowerCase().includes("mindbox")) showAlert("В названии нет Mindbox — проверьте файл", "info");
      else showAlert("Файл загружен", "success");
      outputFilename = file.name.replace(/mindbox/i, "SFMC").replace(/\\.html?$/i, "") + "_SFMC.html";
    }}

    els.browseBtn.onclick = () => els.fileInput.click();
    els.fileInput.onchange = () => setFile(els.fileInput.files[0]);
    els.upload.ondragover = (e) => {{ e.preventDefault(); els.upload.classList.add("drag"); }};
    els.upload.ondragleave = () => els.upload.classList.remove("drag");
    els.upload.ondrop = (e) => {{ e.preventDefault(); els.upload.classList.remove("drag"); setFile(e.dataTransfer.files[0]); }};
    els.brandSearch.oninput = () => {{
      const q = els.brandSearch.value.trim().toLowerCase();
      const filtered = CXQ.brands.filter((b) => b.toLowerCase().includes(q));
      renderBrands(filtered.length ? filtered : CXQ.brands);
    }};
    els.brandSelect.onchange = applyBrandDefaults;

    document.getElementById("validate-btn").onclick = async () => {{
      if (!selectedFile) return showAlert("Выберите файл", "error");
      const html = await readSelectedFile();
      renderValidation(validateSfmcHtml(html), "Проверка");
      showAlert("Проверка завершена", "info");
    }};

    document.getElementById("convert-btn").onclick = async () => {{
      if (!validateForm()) return;
      const html = await readSelectedFile();
      const p = getParams();
      const result = convertMindboxToSfmc(html, p);
      convertedHtml = result.html;
      renderList(els.changes, "Изменения", result.changes, "info");
      renderList(els.warnings, "Предупреждения", result.warnings, "warning");
      renderValidation(validateSfmcHtml(result.html), "Проверка после конвертации");
      els.preview.textContent = result.html.slice(0, 12000);
      els.previewWrap.hidden = false;
      els.downloadBtn.disabled = false;
      showAlert(result.warnings.length ? "Конвертация завершена, проверьте предупреждения" : "Конвертация успешна", "success");
    }};

    document.getElementById("download-btn").onclick = () => {{
      if (!convertedHtml) return;
      const blob = new Blob([convertedHtml], {{ type: "text/html;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = outputFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showAlert("Файл скачан: " + outputFilename, "success");
    }};

    populateSelect("cxq_bu", CXQ.unique_values?.BU, "GENERAL MEDICINES");
    populateSelect("cxq_function", CXQ.unique_values?.Function, "Commercial");
    populateSelect("cxq_cn", CXQ.unique_values?.CN, "journey");
    renderBrands(CXQ.brands || []);
  </script>
</body>
</html>
"""


def main() -> None:
    cxq = json.loads(CXQ_PATH.read_text(encoding="utf-8"))
    cxq_json = json.dumps(cxq, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__CXQ_JSON__", cxq_json)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Built {OUT_PATH} ({OUT_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
