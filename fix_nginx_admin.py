#!/usr/bin/env python3
"""
Принудительно добавляет location ^~ /admin в nginx для promo.21day.club.
Запуск: python fix_nginx_admin.py
"""
import paramiko
import os

HOST = "195.133.63.34"
USER = "root"
PASSWORD = os.environ.get("DEPLOY_PASSWORD", "hdp-k.PD6u8K7U")

ADMIN_BLOCK = '''
    location ^~ /admin {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
'''


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

    print("Читаю /etc/nginx/sites-available/promo21day...")
    _, out, _ = ssh.exec_command("cat /etc/nginx/sites-available/promo21day")
    config = out.read().decode()

    if "server_name promo.21day.club" not in config:
        print("Файл не для promo.21day.club, пропуск")
        ssh.close()
        return

    # Удалить ВСЕ блоки location /admin и location ^~ /admin
    while True:
        idx = config.find("location /admin")
        if idx == -1:
            idx = config.find("location ^~ /admin")
        if idx == -1:
            break
        brace = config.find("{", idx)
        if brace == -1:
            break
        depth = 1
        pos = brace + 1
        while depth > 0 and pos < len(config):
            if config[pos] == "{":
                depth += 1
            elif config[pos] == "}":
                depth -= 1
            pos += 1
        block_start = config.rfind("\n", 0, idx)
        if block_start >= 0:
            block_start += 1
        else:
            block_start = 0
        config = config[:block_start] + config[pos:].lstrip()

    # Добавить блок ПЕРЕД "location /" (в server block с root)
    if "location ^~ /admin" not in config:
        for anchor in ["location / {", "location /{"]:
            if anchor in config:
                config = config.replace(anchor, ADMIN_BLOCK.strip() + "\n\n    " + anchor)
                break
        else:
            for anchor in ["add_header X-Frame-Options", "add_header Strict-Transport-Security"]:
                if anchor in config:
                    config = config.replace("    " + anchor, ADMIN_BLOCK.strip() + "\n\n    " + anchor)
                    break

    with ssh.open_sftp().file("/etc/nginx/sites-available/promo21day", "w") as f:
        f.write(config)

    print("Проверка nginx...")
    run(ssh, "nginx -t")
    print("Перезагрузка nginx...")
    run(ssh, "systemctl reload nginx")

    ssh.close()
    print("Готово. Проверьте: https://promo.21day.club/admin/")


if __name__ == "__main__":
    main()
