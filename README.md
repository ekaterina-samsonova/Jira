# Mindbox → SFMC Email Converter

Веб-инструмент для конвертации HTML-шаблонов email из Mindbox в формат Salesforce Marketing Cloud (SFMC) с проверкой обязательных блоков.

## Самый простой способ — скачать один файл

**Не нужен сервер и терминал.**

1. Скачайте файл [`dist/Mindbox-to-SFMC-Converter.html`](dist/Mindbox-to-SFMC-Converter.html)
2. Сохраните его на компьютер (например, на Рабочий стол)
3. Откройте **двойным кликом** — откроется в браузере (Chrome, Edge, Firefox)
4. Загрузите HTML Mindbox, заполните параметры, нажмите «Конвертировать» и «Скачать SFMC HTML»

> Если скачиваете из GitHub: откройте файл → кнопка **Download raw file** или **Скачать**.

Чтобы пересобрать этот файл после изменений:

```bash
python3 scripts/build_standalone.py
```

## Вариант с сервером (для команды)

## Возможности

- Загрузка HTML-файлов Mindbox (в названии обычно есть «Mindbox»)
- Автоматическая вставка обязательных SFMC-блоков (№1–№6)
- Заполнение CXQ-меток по справочнику из Excel
- Валидация шаблона с указанием, что не так и где смотреть
- Скачивание готового HTML для SFMC

## Быстрый старт

```bash
chmod +x run.sh
./run.sh
```

Или вручную:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Откройте в браузере: http://localhost:8000

## Обязательные блоки SFMC

| Блок | Описание |
|------|----------|
| №1 | AMPscript в начале файла (Lookup DE, utm_hcpid/actid) |
| №2 | Метаданные кампании после `</head>`, opencounter |
| №3 | Ссылка «сюда» на `%%view_email_url%%` |
| №4 | Персонализация + Privacy Link (docsfera.ru) |
| №5 | CXQ-опрос с UTM-метками |
| №6 | Отписка через ContentBlockbyId(1649) |

## Справочные материалы

- `docs/reference/Обязательные блоки для SFMC.docx` — инструкция по блокам
- `docs/reference/CXQ_Email_from Mindbox to SFMC.xlsx` — справочник Brand/DA/TA/BU/Function/CN
- `app/data/cxq_mapping.json` — данные CXQ для выпадающих списков в UI

## API

- `GET /` — веб-интерface
- `GET /api/cxq` — справочник CXQ
- `POST /api/validate` — проверка HTML без конвертации
- `POST /api/convert` — конвертация + отчёт валидации
- `POST /api/download` — скачивание результата

## Примечания

- Визуал и текст ссылок могут отличаться от файла к файлу — инструмент сохраняет структуру, но унифицирует скрипты и токены SFMC.
- Если в блоке №1 указан нестандартный Data Extension, инструмент подсветит это предупреждением.
