const form = document.getElementById('convert-form');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const uploadArea = document.getElementById('upload-area');
const fileCard = document.getElementById('file-card');
const fileNameEl = document.getElementById('file-name');
const clearFileBtn = document.getElementById('clear-file-btn');
const validateBtn = document.getElementById('validate-btn');
const convertBtn = document.getElementById('convert-btn');
const downloadBtn = document.getElementById('download-btn');
const alertBar = document.getElementById('alert-bar');
const serverStatus = document.getElementById('server-status');
const changesEl = document.getElementById('changes');
const warningsEl = document.getElementById('warnings');
const validationEl = document.getElementById('validation');
const previewEl = document.getElementById('preview');
const brandSearch = document.getElementById('brand-search');
const brandSelect = document.getElementById('cxq-brand');
const daInput = document.getElementById('cxq-da');
const taInput = document.getElementById('cxq-ta');
const buSelect = document.getElementById('cxq-bu');
const functionSelect = document.getElementById('cxq-function');
const cnSelect = document.getElementById('cxq-cn');
const resultSummary = document.getElementById('result-summary');
const summarySuccess = document.getElementById('summary-success');
const summaryError = document.getElementById('summary-error');

const cxqData = JSON.parse(document.getElementById('cxq-data').textContent || '{}');
const cxqRows = cxqData.rows || [];
const allBrands = cxqData.brands || [];

let selectedFile = null;
let outputFilename = 'email_SFMC.html';
let convertedReady = false;

init();

function init() {
  populateSelectOptions(buSelect, cxqData.unique_values?.BU || ['GENERAL MEDICINES', 'SPECIALTY CARE', 'VACCINES'], 'GENERAL MEDICINES');
  populateSelectOptions(functionSelect, cxqData.unique_values?.Function || ['Commercial', 'Medical'], 'Commercial');
  populateSelectOptions(cnSelect, cxqData.unique_values?.CN || ['journey', 'promo'], 'journey');
  renderBrandOptions(allBrands);
  updateUtmRequiredState();
  bindEvents();
  checkServer();
  goToStep(1);
}

function bindEvents() {
  browseBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => handleFileSelection(fileInput.files[0]));
  clearFileBtn.addEventListener('click', clearFile);

  uploadArea.addEventListener('dragover', (event) => {
    event.preventDefault();
    uploadArea.classList.add('dragover');
  });

  uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));

  uploadArea.addEventListener('drop', (event) => {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = event.dataTransfer.files[0];
    handleFileSelection(file);
  });

  brandSearch.addEventListener('input', () => {
    const query = brandSearch.value.trim().toLowerCase();
    const filtered = allBrands.filter((brand) => brand.toLowerCase().includes(query));
    renderBrandOptions(filtered.length ? filtered : allBrands);
  });

  brandSelect.addEventListener('change', applyBrandDefaults);
  cnSelect.addEventListener('change', updateUtmRequiredState);

  document.querySelectorAll('.step-link').forEach((button) => {
    button.addEventListener('click', () => goToStep(Number(button.dataset.step)));
  });

  document.getElementById('back-step-2').addEventListener('click', () => goToStep(1));
  document.getElementById('back-step-3').addEventListener('click', () => goToStep(2));

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  validateBtn.addEventListener('click', () => runAction('/api/validate', 'validate'));
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    runAction('/api/convert', 'convert');
  });
  downloadBtn.addEventListener('click', downloadResult);
}

function populateSelectOptions(select, values, defaultValue) {
  const unique = [...new Set(values.filter(Boolean))];
  select.innerHTML = unique.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
  if (defaultValue && unique.includes(defaultValue)) {
    select.value = defaultValue;
  }
}

function renderBrandOptions(brands) {
  brandSelect.innerHTML = brands
    .map((brand) => `<option value="${escapeHtml(brand)}">${escapeHtml(brand)}</option>`)
    .join('');
  if (brands.length === 1) {
    brandSelect.value = brands[0];
    applyBrandDefaults();
  }
}

function handleFileSelection(file) {
  if (!file) return;

  if (!/\.html?$/.test(file.name.toLowerCase()) && file.type !== 'text/html') {
    showAlert('Выберите файл с расширением .html или .htm', 'error');
    return;
  }

  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileCard.classList.remove('hidden');
  uploadArea.classList.add('hidden');
  showAlert(`Файл «${file.name}» загружен`, 'success');

  if (!file.name.toLowerCase().includes('mindbox')) {
    showAlert('В названии файла нет «Mindbox». Проверьте, что загружен правильный шаблон.', 'info');
  }

  goToStep(2);
}

function clearFile() {
  selectedFile = null;
  fileInput.value = '';
  fileCard.classList.add('hidden');
  uploadArea.classList.remove('hidden');
  fileNameEl.textContent = '';
  downloadBtn.disabled = true;
  convertedReady = false;
}

function getFormData() {
  const data = new FormData(form);
  if (selectedFile) {
    data.set('file', selectedFile, selectedFile.name);
  }
  return data;
}

function isUtmCampaignRequired() {
  return cnSelect.value.trim().toLowerCase() !== 'promo';
}

function updateUtmRequiredState() {
  const required = isUtmCampaignRequired();
  const field = document.getElementById('field-utm');
  const marker = document.getElementById('utm-required');
  const help = document.getElementById('utm-help');
  marker.hidden = !required;
  field.classList.toggle('optional', !required);
  help.textContent = required
    ? 'Обязательное поле. Подставляется в CXQ-ссылки, если CN не promo.'
    : 'Не используется при CN=promo — можно оставить пустым.';
  if (!required) field.classList.remove('invalid');
}

function validateForm() {
  updateUtmRequiredState();
  if (!selectedFile) {
    showAlert('Сначала загрузите HTML-файл.', 'error');
    goToStep(1);
    return false;
  }

  const utmCampaign = form.utm_campaign.value.trim();
  const brand = form.cxq_brand.value.trim();
  const da = form.cxq_da.value.trim();
  const ta = form.cxq_ta.value.trim();
  const missing = [];
  if (isUtmCampaignRequired() && !utmCampaign) missing.push('utm_campaign');
  if (!brand) missing.push('Brand');
  if (!da) missing.push('DA');
  if (!ta) missing.push('TA');

  if (missing.length) {
    showAlert(`Заполните: ${missing.join(', ')}.`, 'error');
    goToStep(2);
    return false;
  }

  return true;
}

async function runAction(url, mode) {
  if (!validateForm()) return;

  setLoading(true);
  hideAlert();

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: getFormData(),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Ошибка сервера (${response.status})`);
    }

    const data = await response.json();

    if (mode === 'validate') {
      renderValidation(data, 'Проверка файла');
      resultSummary.classList.add('hidden');
      downloadBtn.disabled = true;
      showAlert('Проверка завершена.', 'info');
    } else {
      outputFilename = data.output_filename || 'email_SFMC.html';
      renderValidation(data.validation_after, 'Проверка после конвертации');
      renderList(changesEl, 'Выполненные изменения', data.changes || [], 'info');
      renderList(warningsEl, 'Предупреждения', [...(data.warnings || [])], 'warning');
      previewEl.textContent = data.html || '';
      downloadBtn.disabled = !data.html;
      convertedReady = Boolean(data.html);

      resultSummary.classList.remove('hidden');
      summarySuccess.classList.toggle('hidden', !data.validation_after?.ok);
      summaryError.classList.toggle('hidden', Boolean(data.validation_after?.ok));

      showAlert(
        data.validation_after?.ok
          ? 'Конвертация завершена. Можно скачивать файл.'
          : 'Конвертация выполнена, но остались ошибки — проверьте вкладку «Проверка».',
        data.validation_after?.ok ? 'success' : 'error'
      );
    }

    goToStep(3);
    switchTab('validation');
  } catch (error) {
    showAlert(`Не удалось выполнить операцию: ${error.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

async function downloadResult() {
  if (!selectedFile || !convertedReady) return;

  setLoading(true);
  try {
    const response = await fetch('/api/download', {
      method: 'POST',
      body: getFormData(),
    });

    if (!response.ok) {
      throw new Error(`Ошибка скачивания (${response.status})`);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = outputFilename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showAlert(`Файл «${outputFilename}» скачан.`, 'success');
  } catch (error) {
    showAlert(error.message, 'error');
  } finally {
    setLoading(false);
  }
}

function renderValidation(report, label) {
  const issues = report?.issues || [];
  validationEl.classList.remove('empty-state');

  if (!issues.length) {
    validationEl.innerHTML = `<h3>${escapeHtml(label)}</h3><p class="empty-state">Ошибок не найдено. Все обязательные блоки на месте.</p>`;
    return;
  }

  const status = report.ok ? 'Без критичных ошибок' : 'Нужно исправить';
  validationEl.innerHTML =
    `<h3>${escapeHtml(label)}: ${status}</h3>` +
    issues
      .map(
        (issue) => `
        <div class="issue ${escapeHtml(issue.severity)}">
          <div class="block">${escapeHtml(issue.block)} · ${escapeHtml(issue.severity)}</div>
          <div class="message">${escapeHtml(issue.message)}</div>
          ${issue.hint ? `<div class="hint">${escapeHtml(issue.hint)}</div>` : ''}
          ${issue.snippet ? `<div class="snippet"><code>${escapeHtml(issue.snippet)}</code></div>` : ''}
        </div>`
      )
      .join('');
}

function renderList(container, title, items, className) {
  container.classList.remove('hidden', 'empty-state');
  if (!items.length) {
    container.innerHTML = `<p class="empty-state">${escapeHtml(title)}: нет данных.</p>`;
    return;
  }

  container.innerHTML =
    `<h3>${escapeHtml(title)}</h3>` +
    items
      .map((item) => `<div class="issue ${className}"><div class="message">${escapeHtml(item)}</div></div>`)
      .join('');
}

function applyBrandDefaults() {
  const brand = brandSelect.value;
  const rows = cxqRows.filter((row) => row.Brand === brand);
  if (!rows.length) return;

  const row = rows[0];
  daInput.value = row.DA || '';
  taInput.value = row.TA || '';
  if (row.BU) buSelect.value = row.BU;
  if (row.Function) functionSelect.value = row.Function;
  if (row.CN) cnSelect.value = row.CN;
  updateUtmRequiredState();

  fillDatalist('da-options', [...new Set(rows.map((row) => row.DA).filter(Boolean))]);
  fillDatalist('ta-options', [...new Set(rows.map((row) => row.TA).filter(Boolean))]);
}

function fillDatalist(id, values) {
  const list = document.getElementById(id);
  list.innerHTML = values.map((value) => `<option value="${escapeHtml(value)}"></option>`).join('');
}

function goToStep(step) {
  document.querySelectorAll('.step-panel').forEach((panel) => {
    panel.classList.toggle('active', Number(panel.dataset.stepPanel) === step);
  });
  document.querySelectorAll('.step-link').forEach((button) => {
    button.classList.toggle('active', Number(button.dataset.step) === step);
  });
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.tab === name);
  });
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `tab-${name}`);
  });
}

function setLoading(isLoading) {
  convertBtn.disabled = isLoading;
  validateBtn.disabled = isLoading;
  downloadBtn.disabled = isLoading || !convertedReady;
  convertBtn.querySelector('.btn-spinner').classList.toggle('hidden', !isLoading);
}

function showAlert(message, type = 'info') {
  alertBar.textContent = message;
  alertBar.className = `alert ${type}`;
}

function hideAlert() {
  alertBar.className = 'alert hidden';
}

async function checkServer() {
  try {
    const response = await fetch('/api/cxq');
    if (!response.ok) throw new Error('bad status');
    serverStatus.textContent = 'Сервер работает';
    serverStatus.className = 'server-status ok';
  } catch (error) {
    serverStatus.textContent = 'Сервер недоступен. Запустите: uvicorn app.main:app --host 0.0.0.0 --port 8000';
    serverStatus.className = 'server-status error';
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
