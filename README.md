# Telegram Margin Bot

## Модуль пошуку рідин Autofun CRM

У боті є окремий каталоговий модуль `telegram_catalog_bot/catalog_search`.
Для роботи кнопки `🔎 Пошук рідин` додайте в `.env` CRM-параметри:

```env
AUTOFUN_BASE_URL=https://cs.autofun.at
AF_IDS_USERNAME=your_af_ids_username
AF_IDS_PASSWORD=your_af_ids_password
CHROME_BIN=/Users/aleksandrbortko/Downloads/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing
CHROMEDRIVER_PATH=/Users/aleksandrbortko/Downloads/chromedriver-mac-arm64/chromedriver
CATALOG_CHROME_PROFILE_DIR=.crm_chrome_profile
CATALOG_DEBUG_DIR=catalog_search_debug
CATALOG_SEARCH_HEADLESS=false
CATALOG_SEARCH_LIMIT=20
```

Перший запуск відкриває CRM через Selenium і логіниться через AF IDS.
Далі сесія браузера перевикористовується через `.crm_chrome_profile`.

## Локальный запуск на Mac

1. Перейдите в папку проекта:

```bash
cd /Users/aleksandrbortko/Telegram_bor_dinamicMargin/telegram_margin_bot
```

2. Создайте виртуальное окружение и установите зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

4. Заполните `.env` реальными значениями:

```env
BOT_TOKEN=your_telegram_bot_token
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/your-main-spreadsheet-id/edit?usp=sharing
GOOGLE_JSON_FILE=service-account.json
SURVEY_SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/your-survey-spreadsheet-id/edit?usp=sharing
```

5. Положите JSON-ключ Google service account в папку проекта. Имя файла должно совпадать с `GOOGLE_JSON_FILE`.

6. Убедитесь, что service account имеет доступ к нужным Google Sheets.

7. Запустите бота:

```bash
python bot.py
```

## Запуск на сервере через systemd

1. Скопируйте проект на сервер, например в `/opt/telegram_margin_bot`.

2. Создайте виртуальное окружение и установите зависимости:

```bash
cd /opt/telegram_margin_bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

3. Создайте `/opt/telegram_margin_bot/.env` и заполните переменные:

```env
BOT_TOKEN=your_telegram_bot_token
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/your-main-spreadsheet-id/edit?usp=sharing
GOOGLE_JSON_FILE=service-account.json
SURVEY_SPREADSHEET_URL=https://docs.google.com/spreadsheets/d/your-survey-spreadsheet-id/edit?usp=sharing
```

4. Положите JSON-ключ Google service account в `/opt/telegram_margin_bot`.

5. Создайте systemd unit `/etc/systemd/system/telegram-margin-bot.service`:

```ini
[Unit]
Description=Telegram Margin Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/telegram_margin_bot
ExecStart=/opt/telegram_margin_bot/.venv/bin/python /opt/telegram_margin_bot/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

6. Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-margin-bot
sudo systemctl start telegram-margin-bot
```

7. Проверьте статус и логи:

```bash
sudo systemctl status telegram-margin-bot
sudo journalctl -u telegram-margin-bot -f
```

## Headless smoke tests для пошуку рідин

Команды запускают Selenium-поиск в фоновом режиме:

```bash
python3 -m telegram_catalog_bot.catalog_search.headless_smoke_tests k2-engine-oil-0w40
python3 -m telegram_catalog_bot.catalog_search.headless_smoke_tests castrol-engine-oil-0w40-1l
python3 -m telegram_catalog_bot.catalog_search.headless_smoke_tests export-silver-castrol-engine-oil-0w40-1l
python3 -m telegram_catalog_bot.catalog_search.headless_smoke_tests article-15f030
```

Все сценарии одной командой:

```bash
python3 -m telegram_catalog_bot.catalog_search.headless_smoke_tests all
```
