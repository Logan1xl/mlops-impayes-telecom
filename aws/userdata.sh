#!/bin/bash
# Impayes AI — bootstrap EC2 (Amazon Linux 2023, t3.micro)
# MLflow UI :5000 — FastAPI :8000 — nginx :80 (démo statique + proxy /api)
set -euxo pipefail
dnf update -y
dnf install -y python3.11 python3.11-pip git nginx
timedatectl set-timezone Africa/Douala

mkdir -p /opt/impayes && cd /opt/impayes
git clone --branch feature/demo-soutenance --depth 1 https://github.com/Logan1xl/mlops-impayes-telecom.git project
cd project

python3.11 -m venv .venv
.venv/bin/pip install --no-cache-dir --upgrade pip
.venv/bin/pip install --no-cache-dir numpy pandas scipy scikit-learn joblib fastapi uvicorn pydantic pyyaml prometheus-client mlflow

mkdir -p /var/www/demo
cp -R demo/* /var/www/demo/

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
        client_max_body_size 2m;
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
echo "OK $(date -u)" > /var/log/impayes-bootstrap.log
