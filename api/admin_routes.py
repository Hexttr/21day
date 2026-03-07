"""Маршруты админки: авторизация, контент, рефералы."""
import json
import os
from functools import wraps

from flask import Blueprint, request, jsonify, session, render_template
from werkzeug.security import check_password_hash

from admin_db import init_db, add_referral, delete_referral, list_referrals, referral_exists, list_payments

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Хеш пароля (хранится в env или используется дефолтный)
ADMIN_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "scrypt:32768:8:1$SG7x8k0C6z6cnVqo$f1e74db6a9941f66b0498d2481794337e921b5fb646ba4f63fdd5d0f6d56c4a18e60ed7ed6383359cac33621b00476070a2e239cd147313152d74e04366b5c94")

CONTENT_PATH = os.path.join(os.path.dirname(__file__), "content.json")


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapped


@admin_bp.route("/", methods=["GET"])
def admin_page():
    return render_template("admin.html")


@admin_bp.route("/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    password = data.get("password", "")
    if check_password_hash(ADMIN_HASH, password):
        session["admin_logged_in"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "Invalid password"}), 401


@admin_bp.route("/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"ok": True})


@admin_bp.route("/content", methods=["GET"])
@login_required
def get_content():
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@admin_bp.route("/content", methods=["PUT", "POST"])
@login_required
def save_content():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    with open(CONTENT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True})


@admin_bp.route("/referrals", methods=["GET"])
@login_required
def get_referrals():
    init_db()
    return jsonify({"referrals": list_referrals()})


@admin_bp.route("/referrals", methods=["POST"])
@login_required
def create_referral():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().lower()
    if not code or len(code) < 2:
        return jsonify({"error": "Code too short"}), 400
    if add_referral(code):
        return jsonify({"ok": True, "code": code})
    return jsonify({"error": "Code already exists"}), 409


@admin_bp.route("/referrals/<code>", methods=["DELETE"])
@login_required
def remove_referral(code):
    if delete_referral(code):
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404


@admin_bp.route("/payments", methods=["GET"])
@login_required
def get_payments():
    init_db()
    return jsonify({"payments": list_payments()})
