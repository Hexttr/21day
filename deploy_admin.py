#!/usr/bin/env python3
"""
Деплой админки на сервер.
Только promo.21day.club — НЕ трогает 21day.club и navoradio.com.
"""
import os
import paramiko
from pathlib import Path

HOST = "195.133.63.34"
USER = "root"
PASSWORD = os.environ.get("DEPLOY_PASSWORD", "hdp-k.PD6u8K7U")
ROOT = Path(__file__).parent
API_DIR = "/opt/21day-api"

# Опционально: задайте в env для production
FLASK_SECRET = os.environ.get("FLASK_SECRET_KEY", "21day-promo-admin-" + os.urandom(8).hex())
PASS1 = os.environ.get("ROBOKASSA_PASS1")
PASS2 = os.environ.get("ROBOKASSA_PASS2")


def run(ssh, cmd, check=True):
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    if check and code != 0:
        raise RuntimeError(f"Failed: {cmd}\n{err or out}")
    return out, err, code


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

    sftp = ssh.open_sftp()

    print("1. Uploading API files (admin, content)...")
    sftp.put(str(ROOT / "api" / "robokassa.py"), f"{API_DIR}/robokassa.py")
    sftp.put(str(ROOT / "api" / "requirements.txt"), f"{API_DIR}/requirements.txt")
    sftp.put(str(ROOT / "api" / "admin_db.py"), f"{API_DIR}/admin_db.py")
    sftp.put(str(ROOT / "api" / "admin_routes.py"), f"{API_DIR}/admin_routes.py")
    sftp.put(str(ROOT / "api" / "content.json"), f"{API_DIR}/content.json")
    run(ssh, f"mkdir -p {API_DIR}/templates")
    sftp.put(str(ROOT / "api" / "templates" / "admin.html"), f"{API_DIR}/templates/admin.html")
    sftp.close()

    print("2. Installing dependencies (werkzeug)...")
    run(ssh, f"cd {API_DIR} && venv/bin/pip install -q -r requirements.txt")

    print("3. Updating systemd service (FLASK_SECRET_KEY)...")
    _, out, _ = ssh.exec_command("cat /etc/systemd/system/21day-api.service")
    service_content = out.read().decode()
    if "FLASK_SECRET_KEY" not in service_content:
        env_line = f'Environment="FLASK_SECRET_KEY={FLASK_SECRET}"'
        # Добавить после любого Environment= или перед ExecStart
        if "Environment=" in service_content:
            last_env_end = service_content.rfind("Environment=")
            line_end = service_content.find("\n", last_env_end)
            if line_end == -1:
                line_end = len(service_content)
            service_content = service_content[:line_end] + "\n" + env_line + service_content[line_end:]
        else:
            service_content = service_content.replace("ExecStart=", env_line + "\nExecStart=")
        with ssh.open_sftp().file("/etc/systemd/system/21day-api.service", "w") as f:
            f.write(service_content)
        run(ssh, "systemctl daemon-reload")
    run(ssh, "systemctl restart 21day-api")

    print("4. Updating nginx (ТОЛЬКО promo21day — promo.21day.club)...")
    _, out, _ = ssh.exec_command("cat /etc/nginx/sites-available/promo21day 2>/dev/null || echo 'FILE_NOT_FOUND'")
    promo_config = out.read().decode()
    # Заменить location /admin на location ^~ /admin (приоритет над location /)
    if "location /admin" in promo_config and "location ^~ /admin" not in promo_config:
        promo_config = promo_config.replace("location /admin {", "location ^~ /admin {")

    # Убрать дубликат location /admin если есть
    def count_admin():
        return promo_config.count("location /admin") + promo_config.count("location ^~ /admin")
    while count_admin() > 1:
        idx = promo_config.find("location /admin")
        if idx == -1:
            idx = promo_config.find("location ^~ /admin")
        idx2 = promo_config.find("location /admin", idx + 5)
        if idx2 == -1:
            idx2 = promo_config.find("location ^~ /admin", idx + 5)
        if idx2 == -1:
            break
        end = promo_config.find("    }\n", idx2)
        if end != -1:
            promo_config = promo_config[:idx2] + promo_config[end + 5:]
        else:
            break

    # Убрать дубликат location /api если есть (от предыдущего деплоя)
    if promo_config.count("location /api") > 1:
        idx = promo_config.find("location /api")
        idx2 = promo_config.find("location /api", idx + 5)
        if idx2 != -1:
            end = promo_config.find("    }\n", idx2)
            if end != -1:
                promo_config = promo_config[:idx2] + promo_config[end + 5:]

    dupes_removed = False
    if promo_config.count("location /admin") + promo_config.count("location ^~ /admin") > 1:
        dupes_removed = True
    if promo_config.count("location /api") > 1:
        dupes_removed = True

    if "FILE_NOT_FOUND" in promo_config or "server_name promo.21day.club" not in promo_config:
        print("   Пропуск: promo21day не найден или не для promo.21day.club")
    else:
        need_api = "location /api" not in promo_config
        need_admin = "location /admin" not in promo_config and "location ^~ /admin" not in promo_config
        if need_admin:
            admin_block = """
    location ^~ /admin {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""
            # Вставить /admin: после location /api } или перед location /
            if "location /api" in promo_config:
                promo_config = promo_config.replace(
                    "proxy_set_header X-Forwarded-Proto $scheme;\n    }\n",
                    "proxy_set_header X-Forwarded-Proto $scheme;\n    }\n" + admin_block,
                    1
                )
            else:
                api_block = """
    location /api {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ^~ /admin {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""
                for anchor in ["location / {", "add_header X-Frame-Options", "add_header Strict-Transport-Security"]:
                    if anchor in promo_config:
                        promo_config = promo_config.replace(f"    {anchor}", api_block + f"    {anchor}")
                        break
        elif need_api:
            api_block = """
    location /api {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""
            for anchor in ["location / {", "add_header X-Frame-Options", "add_header Strict-Transport-Security"]:
                if anchor in promo_config:
                    promo_config = promo_config.replace(f"    {anchor}", api_block + f"    {anchor}")
                    break
            with ssh.open_sftp().file("/etc/nginx/sites-available/promo21day", "w") as f:
                f.write(promo_config)
            run(ssh, "nginx -t && systemctl reload nginx")
            print("   nginx обновлён и перезагружен")
        else:
            print("   /api и /admin уже настроены")

        if need_admin or need_api or dupes_removed:
            with ssh.open_sftp().file("/etc/nginx/sites-available/promo21day", "w") as f:
                f.write(promo_config)
            run(ssh, "nginx -t && systemctl reload nginx")
            print("   nginx обновлён и перезагружен")

    print("5. Uploading static files (promo.21day.club)...")
    sftp = ssh.open_sftp()
    sftp.put(str(ROOT / "index.html"), "/var/www/promo.21day.club/index.html")
    sftp.put(str(ROOT / "script.js"), "/var/www/promo.21day.club/script.js")
    sftp.close()
    run(ssh, "chown -R www-data:www-data /var/www/promo.21day.club")

    ssh.close()
    print("Done! Админка: https://promo.21day.club/admin/")
    print("(21day.club и navoradio.com не изменялись)")


if __name__ == "__main__":
    main()
