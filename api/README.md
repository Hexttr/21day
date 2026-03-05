# Robokassa API для promo.21day.club

## Локальный запуск

```bash
cd api
pip install -r requirements.txt
export ROBOKASSA_PASS1="ваш_тестовый_пароль_1"
export ROBOKASSA_PASS2="ваш_тестовый_пароль_2"
export ROBOKASSA_TEST=1
python robokassa.py
```

API будет на http://127.0.0.1:5001

## Настройки в личном кабинете Robokassa

1. **Result URL:** `https://promo.21day.club/api/robokassa/result`
2. **Success URL:** `https://promo.21day.club/success.html`
3. **Fail URL:** `https://promo.21day.club/#pricing`
4. **Алгоритм хэша:** MD5
5. **Тестовые пароли** — уже прописаны в настройках магазина

## Email после оплаты

Чтобы пользователю приходило письмо после успешной оплаты, добавьте SMTP-переменные в systemd:

```bash
SMTP_HOST=smtp.yandex.ru  # или smtp.gmail.com, smtp.mail.ru
SMTP_PORT=587
SMTP_USER=info@i-integrator.com
SMTP_PASS=пароль_приложения
EMAIL_FROM=info@i-integrator.com
EMAIL_FROM_NAME=21 день с ИИ
```

**Примеры SMTP:**
- **Yandex:** smtp.yandex.ru:587, нужен пароль приложения
- **Gmail:** smtp.gmail.com:587, нужен пароль приложения (2FA)
- **Mail.ru:** smtp.mail.ru:587

## Переход в боевой режим

Когда магазин активирован:
- Замените тестовые пароли на рабочие (Пароль #1 и Пароль #2)
- Установите `ROBOKASSA_TEST=0` или уберите переменную
- Обновите ROBOKASSA_PASS1 и ROBOKASSA_PASS2 на сервере
