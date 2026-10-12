# Онлайн-деканат

Сервис для проверки студенческих документов. Пользователь загружает фото, скан или PDF документа. Сервис распознаёт текст, раскладывает данные по полям, проверяет, все ли обязательные сведения есть, и отвечает на вопросы по документу и Положению.

Поддерживаемые документы:

- справка об обучении;
- заявление на академический отпуск;
- справка о практике;
- заявление о переводе (пример типа, добавленного через конфиг).

Работает через веб-интерфейс и Telegram-бота. Всё считается локально на CPU, внешние API не используются.

## Ссылки

После запуска сервера:

| Что | Адрес |
|---|---|
| Веб-интерфейс | http://localhost:8000 |
| Swagger (документация API) | http://localhost:8000/api/docs/ |
| OpenAPI-схема | http://localhost:8000/api/schema/ |
| Админка Django | http://localhost:8000/admin/ |

## Структура проекта

```
umirhack/
├── backend/            Django + DRF: API, хранение документов, Swagger
│   ├── dekanat/        настройки и маршруты
│   └── documents/      модели, сериализаторы, представления API
├── core/dekanat_core/  обработка документов (не зависит от Django)
│   ├── io/             загрузка JPG, PNG, PDF
│   ├── preprocess/     поворот, выравнивание, удаление теней
│   ├── ocr/            распознавание текста (PaddleOCR, Tesseract)
│   ├── layout/         сборка текста в строки
│   ├── classify/       определение типа документа
│   ├── extract/        извлечение и нормализация полей
│   ├── marks/          поиск подписи и печати
│   ├── rules/          проверка по Положению
│   └── qa/             ответы на вопросы
├── frontend/           React + Vite + TypeScript + Tailwind
├── bot/                Telegram-бот (aiogram), работает через API
├── config/
│   ├── doc_types/      описание типов документов (YAML)
│   ├── intents.yaml    шаблоны вопросов и ответов
│   └── settings.yaml   пороги OCR и пути
├── data/               материалы организаторов: Положение, документы, эталон, evaluate.py
├── scripts/            запуск на наборе документов, загрузка моделей, туннель
├── docker/             Dockerfile для бэкенда и бота
├── requirements/       зависимости Python
├── docker-compose.yml
├── Makefile            команды для Linux/macOS
└── tasks.ps1           команды для Windows PowerShell
```

## Запуск

### Что нужно

- Python 3.10-3.12 (PaddlePaddle не поддерживает 3.13 и новее)
- Node.js 18 или новее
- Tesseract 5 (необязательно, используется как запасной OCR)

### Локально

```bash
# 1. Виртуальное окружение и зависимости
py -3.12 -m venv .venv            # Linux/macOS: python3.12 -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements/dev.txt

# 2. Модели OCR
python scripts/download_models.py

# 3. Сборка фронтенда
cd frontend
npm install
npm run build
cd ..

# 4. Запуск сервера
cd backend
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

После этого открыть http://localhost:8000.

Короткие команды для Windows: `.\tasks.ps1 venv`, `.\tasks.ps1 models`, `.\tasks.ps1 build-frontend`, `.\tasks.ps1 serve`.
Для Linux/macOS: `make venv models build-frontend backend`.

Фронтенд можно запустить отдельно в режиме разработки: `cd frontend && npm run dev` (порт 5173).

### Telegram-бот

Скопировать `.env.example` в `.env` и указать `BOT_TOKEN`. Затем в отдельном терминале:

```bash
python -m bot
```

Бот обращается к API по адресу из `API_BASE_URL` (по умолчанию `http://localhost:8000`).

Чтобы веб-интерфейс открывался внутри Telegram (Mini App), нужен публичный HTTPS-адрес. Для локального запуска можно поднять туннель:

```bash
python scripts/tunnel_keeper.py
```

Скрипт сам записывает адрес в `.env` и обновляет кнопку меню бота.

### Docker

```bash
docker compose up --build
```

Поднимает бэкенд с собранным фронтендом на порту 8000 и бота. Для бота в `.env` должен быть указан `BOT_TOKEN`.

### Tesseract

- Windows: `winget install UB-Mannheim.TesseractOCR`
- Linux: `apt install tesseract-ocr tesseract-ocr-rus`

Если Tesseract не установлен, сервис работает только на PaddleOCR. Путь к программе можно задать в `config/settings.yaml` (`ocr.tesseract_cmd`) или в переменной `TESSERACT_CMD`.

### Обработка набора документов

```bash
python scripts/predict.py --manifest data/documents.json --questions data/questions.json --base data \
    --input image --out results.json --reference data/reference_results.json
```

Результат сохраняется в `results.json`. С параметром `--reference` скрипт сразу считает метрики через `data/evaluate.py`.

## API

Базовый адрес: `/api/v1`. Полное описание с примерами запросов есть в Swagger: http://localhost:8000/api/docs/

### Справочники

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | состояние сервиса и OCR-движков |
| GET | `/doc-types` | список типов документов и их полей |
| GET | `/rules` | текст Положения по разделам и пунктам |

### Документы

| Метод | Путь | Описание |
|---|---|---|
| POST | `/documents` | загрузить документ |
| GET | `/documents/{id}` | получить результат обработки |
| PATCH | `/documents/{id}` | сменить тип документа |
| DELETE | `/documents/{id}` | удалить документ |
| POST | `/documents/{id}/ask` | задать вопрос по документу |
| POST | `/documents/{id}/check` | проверить комплектность |
| GET | `/documents/{id}/ocr` | распознанный текст |
| GET | `/documents/{id}/boxes` | координаты найденных полей |
| GET | `/documents/{id}/image` | изображение документа |
| GET | `/documents/{id}/annotated.png` | изображение с выделенными полями |
| GET | `/documents/{id}/fields/{key}/crop.png` | фрагмент изображения с одним полем |
| GET | `/documents/{id}/export.json` | результат в формате `results.json` |

### Загрузка документа

`POST /api/v1/documents`, тело `multipart/form-data`:

| Поле | Обязательное | Описание |
|---|---|---|
| `file` | да | JPG, PNG или PDF (одна страница) |
| `doc_type` | нет | ключ типа документа или `auto` (по умолчанию) |
| `question` | нет | вопрос, ответ на который нужно получить сразу |
| `check` | нет | `true`, чтобы сразу проверить комплектность |
| `async` | нет | `1`, чтобы получить ответ сразу, не дожидаясь обработки |

Ответы:

- `201` - документ обработан, в ответе результат;
- `202` - документ принят в обработку (при `async=1`), результат нужно запрашивать через `GET /documents/{id}`, пока `status` равен `processing`;
- `422` - файл не удалось обработать.

Пример:

```bash
curl -F "file=@data/documents/open-001.png" -F "doc_type=auto" \
     -F "question=Кто принимает окончательное решение?" \
     http://localhost:8000/api/v1/documents
```

### Вопрос по документу

`POST /api/v1/documents/{id}/ask`

```json
{ "question": "Какая дата выдачи справки?" }
```

Ответ:

```json
{
  "question": "Какая дата выдачи справки?",
  "answerable": true,
  "value": "2024-03-15",
  "answer": "Дата выдачи: 2024-03-15.",
  "sources": ["field:issue_date"],
  "intent": "field",
  "field_key": "issue_date"
}
```

`sources` содержит ссылки на поля документа (`field:...`) и пункты Положения (`rule:X.Y`). Если ответа нет ни в документе, ни в Положении, `answerable` будет `false`, а `sources` пустым.

### Смена типа документа

`PATCH /api/v1/documents/{id}`

```json
{ "doc_type": "study_certificate" }
```

Поля извлекаются заново по уже распознанному тексту, повторный OCR не выполняется.

### Изображение

`GET /api/v1/documents/{id}/image?variant=...`

| `variant` | Что возвращает |
|---|---|
| `preview` | уменьшенное выровненное изображение (по умолчанию) |
| `normalized` | выровненное изображение в полном размере |
| `original` | исходный файл |
| `original_preview` | уменьшенный исходный снимок |

## Как добавить новый тип документа

Создать YAML-файл в `config/doc_types/` и перезапустить сервер. Новый тип появится в API, веб-интерфейсе и боте. Пример:

```yaml
key: transfer_application
title: Заявление о переводе
detect: {title_keywords: ["заявление о переводе"], label_keywords: ["текущий вуз", "желаемое направление"]}
complete_message_rules: ["4.1", "4.2"]
fields:
  - {key: current_university, label: Текущий вуз, type: text, rule: "4.1"}
  - {key: target_program, label: Желаемое направление, type: text, rule: "4.1"}
  - {key: application_date, label: Дата заявления, type: date, rule: "4.1"}
  - {key: signature_present, label: Подпись студента, type: signature, anchor: "подпись студента", rule: "4.2"}
```

Доступные типы полей: `text`, `person_name`, `date`, `int`, `enum`, `doc_number`, `group`, `signature`, `seal`.

## Ограничения

- Проверяется только наличие сведений, подписи и печати. Подлинность документа не проверяется.
- Обрабатывается одна страница. Многостраничные PDF не принимаются.
- Рукописный текст не распознаётся.
- Окончательное решение по документу принимает сотрудник деканата.
