#!/usr/bin/env python3
"""
Robokassa API для лендинга promo.21day.club.
Эндпоинты: POST /api/create-payment, POST /api/robokassa/result
"""
import hashlib
import json
import os
import smtplib
import time
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode

from flask import Flask, request, jsonify

app = Flask(__name__)

MERCHANT_LOGIN = os.environ.get("ROBOKASSA_LOGIN", "21dayCLUB")
PASSWORD1 = os.environ.get("ROBOKASSA_PASS1", "")
PASSWORD2 = os.environ.get("ROBOKASSA_PASS2", "")
BASE_URL = os.environ.get("BASE_URL", "https://promo.21day.club")
IS_TEST = os.environ.get("ROBOKASSA_TEST", "1") == "1"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = [x.strip() for x in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if x.strip()]

# Email после оплаты (SMTP)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "info@i-integrator.com")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "21 день с ИИ")

PRICES = {"14": 6500, "21": 8500}
ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def md5_signature(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    """Создаёт URL для редиректа на оплату Robokassa."""
    data = request.get_json() or {}
    plan = data.get("plan", "21")
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")
    origin = (data.get("origin") or "").rstrip("/")
    if origin not in ("https://promo.21day.club", "http://promo.21day.club"):
        origin = BASE_URL

    if plan not in PRICES:
        return jsonify({"error": "Invalid plan"}), 400

    out_sum = PRICES[plan]
    inv_id = int(time.time() * 1000)

    # Shp_ в алфавитном порядке для подписи: email, name, phone, plan
    shp_email = (email or "")[:50]
    shp_name = (name or "")[:50]
    shp_phone = (phone or "")[:30]
    sign_str = f"{MERCHANT_LOGIN}:{out_sum}:{inv_id}:{PASSWORD1}:Shp_email={shp_email}:Shp_name={shp_name}:Shp_phone={shp_phone}:Shp_plan={plan}"
    signature = md5_signature(sign_str)

    params = {
        "MerchantLogin": MERCHANT_LOGIN,
        "OutSum": out_sum,
        "InvId": inv_id,
        "Description": f"Курс 21 день с ИИ — тариф {plan} дней",
        "SignatureValue": signature,
        "Encoding": "utf-8",
        "SuccessURL": f"{origin}/success.html",
        "FailURL": f"{origin}/#pricing",
        "Shp_email": shp_email,
        "Shp_name": shp_name,
        "Shp_phone": shp_phone,
        "Shp_plan": plan,
    }
    if IS_TEST:
        params["IsTest"] = 1

    payment_url = f"{ROBOKASSA_URL}?{urlencode(params)}"
    return jsonify({"paymentUrl": payment_url, "invId": inv_id})


@app.route("/api/robokassa/result", methods=["GET", "POST"])
def robokassa_result():
    """
    Result URL — Robokassa отправляет сюда GET или POST при успешной оплате.
    Проверяем подпись, возвращаем OK{InvId}.
    """
    data = request.args if request.method == "GET" else request.form
    out_sum = data.get("OutSum", "")
    inv_id = data.get("InvId", "")
    signature = data.get("SignatureValue", "")
    shp_email = data.get("Shp_email", "")
    shp_name = data.get("Shp_name", "")
    shp_phone = data.get("Shp_phone", "")
    shp_plan = data.get("Shp_plan", "")

    # Подпись: OutSum:InvId:Password2[:Shp_* в том же порядке, что при создании]
    # Мы передавали Shp_email, Shp_name, Shp_phone, Shp_plan (алфавитный порядок)
    parts = [out_sum, inv_id, PASSWORD2]
    if shp_email:
        parts.append(f"Shp_email={shp_email}")
    if shp_name:
        parts.append(f"Shp_name={shp_name}")
    if shp_phone:
        parts.append(f"Shp_phone={shp_phone}")
    if shp_plan:
        parts.append(f"Shp_plan={shp_plan}")
    sign_str = ":".join(parts)
    expected = md5_signature(sign_str)

    if signature.upper() != expected:
        return "bad sign", 200  # Robokassa требует 200, иначе повторяет

    app.logger.info(f"Payment OK: inv_id={inv_id} email={shp_email} plan={shp_plan} sum={out_sum}")

    # Оповещение в Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS:
        plan_label = "14 дней" if shp_plan == "14" else "21 день"
        out_sum_fmt = str(int(float(out_sum))) if out_sum else "0"
        text = (
            f"💰 Новая оплата!\n\n"
            f"Имя: {shp_name}\n"
            f"Сумма: {out_sum_fmt} ₽\n"
            f"Тариф: {plan_label}\n"
            f"Email: {shp_email}\n"
            f"Телефон: {shp_phone}\n"
            f"Заказ: #{inv_id}"
        )
        _send_telegram(text)

    # Письмо пользователю после оплаты
    if shp_email and SMTP_HOST and SMTP_USER and SMTP_PASS:
        _send_welcome_email(shp_email, shp_name or "Участник")

    return f"OK{inv_id}", 200


def _send_welcome_email(to_email: str, name: str) -> None:
    """Отправляет письмо пользователю после успешной оплаты."""
    subject = "Вы записались на курс «21 день с ИИ»"
    body = f"""Здравствуйте, {name}!

Вы успешно записались на курс «21 день с ИИ». Оплата получена.

В ближайшее время с вами свяжется менеджер для уточнения деталей и предоставления доступа к материалам.

Если у вас есть вопросы — пишите на info@i-integrator.com или в Telegram.

До встречи на курсе!
Команда 21 день с ИИ
"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())
    except Exception as e:
        app.logger.warning(f"Email send failed to {to_email}: {e}")


def _send_telegram(text: str) -> None:
    """Отправляет сообщение всем чатам из TELEGRAM_CHAT_IDS."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            payload = {"chat_id": chat_id, "text": text}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass  # OK
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            app.logger.warning(f"Telegram HTTP {e.code} to {chat_id}: {body}")
        except Exception as e:
            app.logger.warning(f"Telegram send failed to {chat_id}: {e}")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/test-telegram", methods=["GET"])
def test_telegram():
    """Тестовая отправка в Telegram (для проверки)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return jsonify({"error": "Telegram not configured"}), 500
    _send_telegram("🔔 Тест: бот promo.21day.club работает!")
    return jsonify({"ok": True, "chats": TELEGRAM_CHAT_IDS})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
