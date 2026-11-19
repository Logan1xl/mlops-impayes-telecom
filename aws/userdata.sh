#!/bin/bash
# =====================================================================
# Impayes AI — bootstrap EC2 (Amazon Linux 2023, t2.micro Free Tier)
# Coller ce script dans "User data" lors de la création de l'instance.
# Ce que ça fait : clone du dépôt → venv → FastAPI :8000 → nginx :80
# (démo statique + proxy /api → uvicorn) → MLflow UI :5000
# =====================================================================
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
dnf update -y
dnf install -y python3.11 git nginx
timedatectl set-timezone Africa/Douala

mkdir -p /opt/impayes && cd /opt/impayes
git clone --branch feature/demo-soutenance --depth 1 https://github.com/Logan1xl/mlops-impayes-telecom.git project
cd project
python3.11 -m venv .venv
.venv/bin/pip install --no-cache-dir --upgrade pip
.venv/bin/pip install --no-cache-dir -r requirements.txt
.venv/bin/pip install --no-cache-dir -e .

# Démo statique copiée dans nginx
mkdir -p /var/www/demo
cp -R demo/index.html demo/assets /var/www/demo/
rmdir /var/www/demo/assets 2>/dev/null || true
mkdir -p /var/www/demo/assets && cp -R demo/assets/* /var/www/demo/assets/

cat > /etc/nginx/conf.d/impayes.conf <<'NGINX'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/demo;
    index index.html;
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 2m;
    }
    location /modele {
        return 200 "impayes-default-risk v1 (logreg)";
        add_header Content-Type text/plain;
    }
}
NGINX

cat > /etc/systemd/system/impayes-api.service <<'SVC'
[Unit]
Description=Impayes AI — FastAPI sur :8000
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/opt/impayes/project
ExecStart=/opt/impayes/project/.venv/bin/python -m uvicorn impayes.api.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

cat > /etc/systemd/system/impayes-mlflow.service <<'SVC'
[Unit]
Description=Impayes AI — MLflow UI sur :5000
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/opt/impayes/project
ExecStart=/opt/impayes/project/.venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow.db --host 0.0.0.0 --port 5000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable --now nginx impayes-api impayes-mlflow
echo "==================================================" > /var/log/impayes-bootstrap.log
echo "Impayes AI — bootstrap terminé $(date -u)" >> /var/log/impayes-bootstrap.log
echo "Démo : http://<IP-PUBLIQUE>/   |   API : http://<IP-PUBLIQUE>/api/health   |   MLflow : http://<IP-PUBLIQUE>:5000" >> /var/log/impayes-bootstrap.log
echo "Vérifier : curl http://127.0.0.1:8000/health && curl http://127.0.0.1:5000/version" >> /var/log/impayes-bootstrap.log
