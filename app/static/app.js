const form = document.getElementById('convert-form');
const fileInput = document.getElementById('file-input');
const fileNameEl = document.getElementById('file-name');
const dropzone = document.getElementById('dropzone');
const validateBtn = document.getElementById('validate-btn');
const downloadBtn = document.getElementById('download-btn');
const changesEl = document.getElementById('changes');
const warningsEl = document.getElementById('warnings');
const validationEl = document.getElementById('validation');
const previewWrap = document.getElementById('preview-wrap');
const previewEl = document.getElementById('preview');
const brandSelect = document.getElementById('cxq-brand');
const daInput = document.getElementById('cxq-da');
const taInput = document.getElementById('cxq-ta');
const buSelect = document.getElementById('cxq-bu');
const functionSelect = document.getElementById('cxq-function');
const cnSelect = document.getElementById('cxq-cn');

let convertedHtml = null;
let outputFilename = 'email_SFMC.html';

function setFileName(name) {
  fileNameEl.textContent = name || 'Файл не выбран';
}

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  setFileName(file ? file.name : '');
  if (file && !file.name.toLowerCase().includes('mindbox')) {
    showWarnings(['Имя файла не содержит «Mindbox» — убедитесь, что загружен правильный шаблон.']);
  }
});

['dragenter', 'dragover'].forEach((eventName) => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropzone.classList.add('drag');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag');
  });
});

dropzone.addEventListener('drop', (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    setFileName(file.name);
  }
});

function getFormData() {
  return new FormData(form);
}

function renderIssues(container, title, issues, className) {
  if (!issues.length) {
    container.classList.add('hidden');
    return;
  }
  container.classList.remove('hidden');
  container.innerHTML = `<h3>${title}</h3>` + issues.map((text) => `<div class="issue ${className}"><div class="message">${escapeHtml(text)}</div></div>`).join('');
}

function renderValidation(report, label) {
  const issues = report.issues || [];
  const status = report.ok ? '✅ Ошибок нет' : '❌ Есть ошибки';
  const html = [`<h3>${label}: ${status}</h3>`];
  if (!issues.length) {
    html.push('<p>Все обязательные блоки найдены.</p>');
  } else {
    html.push(
      issues
        .map(
          (issue) => `
          <div class="issue ${issue.severity}">
            <div class="block">${escapeHtml(issue.block)} · ${issue.severity}</div>
            <div class="message">${escapeHtml(issue.message)}</div>
            ${issue.hint ? `<div class="hint">${escapeHtml(issue.hint)}</div>` : ''}
            ${issue.snippet ? `<div class="snippet"><code>${escapeHtml(issue.snippet)}</code></div>` : ''}
          </div>`
        )
        .join('')
    );
  }
  validationEl.innerHTML = html.join('');
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function showWarnings(items) {
  renderIssues(warningsEl, 'Предупреждения', items, 'warning');
}

function showChanges(items) {
  renderIssues(changesEl, 'Выполненные изменения', items, 'info');
}

async function postForm(url) {
  const file = fileInput.files[0];
  if (!file) {
    alert('Выберите HTML-файл');
    throw new Error('no file');
  }
  const response = await fetch(url, { method: 'POST', body: getFormData() });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Request failed');
  }
  return response.json();
}

validateBtn.addEventListener('click', async () => {
  try {
    const report = await postForm('/api/validate');
    renderValidation(report, 'Проверка');
    changesEl.classList.add('hidden');
    previewWrap.classList.add('hidden');
    downloadBtn.disabled = true;
  } catch (error) {
    if (error.message !== 'no file') alert(error.message);
  }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const data = await postForm('/api/convert');
    convertedHtml = data.html;
    outputFilename = data.output_filename;
    showChanges(data.changes || []);
    showWarnings([...(data.warnings || [])]);
    renderValidation(data.validation_after, 'Проверка после конвертации');
    previewEl.textContent = data.html.slice(0, 12000) + (data.html.length > 12000 ? '\n\n... (обрезано)' : '');
    previewWrap.classList.remove('hidden');
    downloadBtn.disabled = false;
  } catch (error) {
    if (error.message !== 'no file') alert(error.message);
  }
});

downloadBtn.addEventListener('click', async () => {
  const file = fileInput.files[0];
  if (!file) return;
  const response = await fetch('/api/download', { method: 'POST', body: getFormData() });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = outputFilename;
  link.click();
  URL.revokeObjectURL(url);
});

function fillDatalist(id, values) {
  const list = document.getElementById(id);
  list.innerHTML = values.map((value) => `<option value="${escapeHtml(value)}"></option>`).join('');
}

function applyBrandDefaults() {
  const brand = brandSelect.value;
  const rows = (window.CXQ_ROWS || []).filter((row) => row.Brand === brand);
  if (!rows.length) return;
  const row = rows[0];
  daInput.value = row.DA || '';
  taInput.value = row.TA || '';
  if (row.BU) buSelect.value = row.BU;
  if (row.Function) functionSelect.value = row.Function;
  if (row.CN) cnSelect.value = row.CN;

  fillDatalist('da-options', [...new Set(rows.map((r) => r.DA).filter(Boolean))]);
  fillDatalist('ta-options', [...new Set(rows.map((r) => r.TA).filter(Boolean))]);
}

brandSelect.addEventListener('change', applyBrandDefaults);
