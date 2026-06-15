# DjangoBlog — Complete Deployment Guide

This guide walks you through every step: local dev → production VPS → Docker → new instances.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Local Development Setup](#2-local-development-setup)
3. [Environment Configuration](#3-environment-configuration)
4. [Database Setup](#4-database-setup)
5. [Production Deployment (Ubuntu VPS)](#5-production-deployment-ubuntu-vps)
6. [Docker Deployment](#6-docker-deployment)
7. [Deploying a New Instance (Separate Folder)](#7-deploying-a-new-instance-separate-folder)
8. [HTTPS with Let's Encrypt](#8-https-with-lets-encrypt)
9. [Static & Media Files](#9-static--media-files)
10. [Celery Background Tasks](#10-celery-background-tasks)
11. [Environment Variables Reference](#11-environment-variables-reference)
12. [Common Commands Cheat Sheet](#12-common-commands-cheat-sheet)

---

## 1. Project Structure

```
djangoblog/                     ← root project folder
├── blog/                       ← main Django app
│   ├── migrations/
│   ├── templates/blog/
│   │   ├── includes/
│   │   └── tags/
│   ├── templatetags/
│   ├── admin.py
│   ├── api_urls.py
│   ├── api_views.py
│   ├── apps.py
│   ├── context_processors.py
│   ├── feeds.py
│   ├── forms.py
│   ├── models.py
│   ├── serializers.py
│   ├── signals.py
│   ├── sitemaps.py
│   ├── urls.py
│   └── views.py
├── config/                     ← Django project config
│   ├── settings/
│   │   ├── base.py             ← shared settings
│   │   ├── development.py      ← local dev overrides
│   │   └── production.py       ← production overrides
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── img/
├── templates/
│   └── base.html
├── media/                      ← user uploads (git-ignored)
├── staticfiles/                ← collectstatic output (git-ignored)
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── gunicorn.conf.py
├── manage.py
├── nginx.conf
└── DEPLOYMENT.md
```

---

## 2. Local Development Setup

### Prerequisites
- Python 3.11+
- pip & virtualenv (or pipenv/poetry)
- Git

### Step-by-step

```bash
# 1. Clone or create the project folder
git clone https://github.com/yourname/djangoblog.git
cd djangoblog

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -r requirements/development.txt

# 4. Copy and configure .env
cp .env.example .env
# Open .env and set at least SECRET_KEY and DEBUG=True

# 5. Run migrations
python manage.py migrate --settings=config.settings.development

# 6. Create a superuser
python manage.py createsuperuser --settings=config.settings.development

# 7. Load sample data (optional)
python manage.py loaddata fixtures/sample_data.json --settings=config.settings.development

# 8. Collect static files
python manage.py collectstatic --settings=config.settings.development

# 9. Run the dev server
python manage.py runserver --settings=config.settings.development
```

Visit: http://127.0.0.1:8000
Admin: http://127.0.0.1:8000/admin

---

## 3. Environment Configuration

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

**Minimum required for dev:**
```env
DEBUG=True
SECRET_KEY=some-random-secret-key
```

**Minimum required for production:**
```env
DEBUG=False
SECRET_KEY=your-strong-50-char-secret
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:pass@localhost:5432/djangoblog
REDIS_URL=redis://127.0.0.1:6379/1
EMAIL_BACKEND=anymail.backends.sendgrid.EmailBackend
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 4. Database Setup

### SQLite (dev only — default)
No setup required. A `db.sqlite3` file is created automatically.

### PostgreSQL (recommended for production)

```bash
# Install PostgreSQL
sudo apt update && sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE djangoblog;
CREATE USER djangoblog WITH ENCRYPTED PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE djangoblog TO djangoblog;
ALTER DATABASE djangoblog OWNER TO djangoblog;
EOF

# Set in .env
DATABASE_URL=postgres://djangoblog:your_strong_password@localhost:5432/djangoblog
```

### Run migrations
```bash
python manage.py migrate --settings=config.settings.production
```

---

## 5. Production Deployment (Ubuntu VPS)

### 5.1 Server setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv \
    postgresql postgresql-contrib nginx certbot \
    python3-certbot-nginx git redis-server build-essential \
    libpq-dev python3-dev

# Enable Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 5.2 Create a deployment user

```bash
sudo adduser deploy
sudo usermod -aG sudo deploy
su - deploy
```

### 5.3 Clone the project

```bash
# Choose your deployment root — we use /var/www/ for instances
sudo mkdir -p /var/www/djangoblog
sudo chown deploy:deploy /var/www/djangoblog

cd /var/www/djangoblog
git clone https://github.com/yourname/djangoblog.git .
```

### 5.4 Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements/production.txt
```

### 5.5 Configure environment

```bash
cp .env.example .env
nano .env          # fill in all production values
```

### 5.6 Database migration & static files

```bash
# Export settings module
export DJANGO_SETTINGS_MODULE=config.settings.production

# Migrate
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 5.7 Gunicorn systemd service

```bash
sudo nano /etc/systemd/system/djangoblog.service
```

```ini
[Unit]
Description=DjangoBlog Gunicorn Daemon
After=network.target postgresql.service redis.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/var/www/djangoblog
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
EnvironmentFile=/var/www/djangoblog/.env
ExecStart=/var/www/djangoblog/venv/bin/gunicorn \
    config.wsgi:application \
    -c /var/www/djangoblog/gunicorn.conf.py
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable djangoblog
sudo systemctl start djangoblog
sudo systemctl status djangoblog
```

### 5.8 Nginx virtual host

```bash
sudo nano /etc/nginx/sites-available/djangoblog
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/djangoblog/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/djangoblog/media/;
        expires 7d;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/djangoblog.sock;
        # OR if using TCP: proxy_pass http://127.0.0.1:8000;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/djangoblog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. Docker Deployment

Docker is the recommended method for reproducible production deployments.

### Prerequisites
```bash
# Install Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install -y docker-compose-plugin
```

### Deploy with Docker Compose

```bash
# 1. Clone project
git clone https://github.com/yourname/djangoblog.git
cd djangoblog

# 2. Configure environment
cp .env.example .env
nano .env    # set all production values

# 3. Build and start all services
docker compose up -d --build

# 4. Run migrations inside the container
docker compose exec web python manage.py migrate

# 5. Create superuser
docker compose exec web python manage.py createsuperuser

# 6. Collect static files
docker compose exec web python manage.py collectstatic --noinput

# 7. Check logs
docker compose logs -f web
```

### Services started by docker-compose.yml:
| Service | Port  | Role                     |
|---------|-------|--------------------------|
| db      | 5432  | PostgreSQL database      |
| redis   | 6379  | Cache & Celery broker    |
| web     | 8000  | Django + Gunicorn        |
| celery  | —     | Background task worker   |
| nginx   | 80/443| Reverse proxy            |

### Update deployment
```bash
git pull origin main
docker compose up -d --build web
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

---

## 7. Deploying a New Instance (Separate Folder)

This is the correct approach when you want **multiple independent instances** (e.g. staging + production, or multiple clients) on the same server.

### Folder convention
```
/var/www/
├── djangoblog-production/     ← live site
├── djangoblog-staging/        ← staging / QA
├── djangoblog-client-a/       ← separate client install
└── djangoblog-client-b/
```

### Steps to spin up a new instance

```bash
# 1. Choose a unique name for the instance
INSTANCE=djangoblog-staging
PORT=8001              # use a unique port per instance

# 2. Create folder
sudo mkdir -p /var/www/$INSTANCE
sudo chown deploy:deploy /var/www/$INSTANCE
cd /var/www/$INSTANCE

# 3. Clone the codebase
git clone https://github.com/yourname/djangoblog.git .

# 4. Create isolated virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt

# 5. Set up its own .env with UNIQUE values:
#    - Different SECRET_KEY
#    - Different DATABASE_URL (new DB)
#    - Different REDIS_URL (different DB index, e.g. redis://127.0.0.1:6379/2)
cp .env.example .env
nano .env

# 6. Create new PostgreSQL database for this instance
sudo -u postgres psql <<EOF
CREATE DATABASE ${INSTANCE//-/_};
CREATE USER ${INSTANCE//-/_}_user WITH ENCRYPTED PASSWORD 'another_password';
GRANT ALL PRIVILEGES ON DATABASE ${INSTANCE//-/_} TO ${INSTANCE//-/_}_user;
EOF

# 7. Migrate & seed
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# 8. Create a unique gunicorn config for this instance
cat > gunicorn.conf.py <<GUNICORN
bind = "0.0.0.0:${PORT}"
workers = 3
timeout = 120
accesslog = "-"
errorlog = "-"
GUNICORN

# 9. Create a unique systemd service
sudo tee /etc/systemd/system/${INSTANCE}.service > /dev/null <<SERVICE
[Unit]
Description=DjangoBlog — ${INSTANCE}
After=network.target postgresql.service redis.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/var/www/${INSTANCE}
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
EnvironmentFile=/var/www/${INSTANCE}/.env
ExecStart=/var/www/${INSTANCE}/venv/bin/gunicorn \
    config.wsgi:application \
    -c /var/www/${INSTANCE}/gunicorn.conf.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable $INSTANCE
sudo systemctl start $INSTANCE

# 10. Create a unique Nginx vhost
sudo tee /etc/nginx/sites-available/$INSTANCE > /dev/null <<NGINX
server {
    listen 80;
    server_name staging.yourdomain.com;

    location /static/ { alias /var/www/${INSTANCE}/staticfiles/; }
    location /media/  { alias /var/www/${INSTANCE}/media/; }
    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:${PORT};
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/$INSTANCE /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Using Docker for multiple instances

The cleanest approach is a separate `docker-compose.yml` per instance:

```bash
# Production instance
cd /var/www/djangoblog-production
cp .env.example .env   # set production vars
docker compose -p djangoblog-prod up -d --build

# Staging instance — override ports in a separate compose file
cd /var/www/djangoblog-staging
cp .env.example .env   # set staging vars with different DB
cat > docker-compose.override.yml <<EOF
services:
  nginx:
    ports:
      - "8080:80"
  web:
    ports:
      - "8001:8000"
EOF
docker compose -p djangoblog-staging up -d --build
```

The `-p` (project) flag namespaces all containers, volumes and networks so instances never collide.

---

## 8. HTTPS with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is set up automatically; test it:
sudo certbot renew --dry-run

# Verify cron / systemd timer
sudo systemctl status certbot.timer
```

After cert is obtained, Nginx config is updated automatically. Add this to your `.env`:
```env
SECURE_SSL_REDIRECT=True
```

---

## 9. Static & Media Files

### Development
Static files are served automatically by Django's dev server.
Media files are served via `MEDIA_URL`.

### Production
- **Static** → served by Nginx directly from `staticfiles/`
- **Media** → served by Nginx directly from `media/`
- Both are collected by: `python manage.py collectstatic --noinput`

### Optional: AWS S3 for media/static

```env
USE_S3=True
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=my-djangoblog-bucket
```

Enable CORS on your S3 bucket and set the bucket policy to allow public read.

---

## 10. Celery Background Tasks

Celery is used for sending emails asynchronously (newsletter, notifications, etc).

### Start worker (manual)
```bash
source venv/bin/activate
celery -A config worker -l info
```

### Systemd service for Celery
```bash
sudo nano /etc/systemd/system/djangoblog-celery.service
```

```ini
[Unit]
Description=DjangoBlog Celery Worker
After=network.target redis.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/var/www/djangoblog
EnvironmentFile=/var/www/djangoblog/.env
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/var/www/djangoblog/venv/bin/celery \
    -A config worker -l info \
    --logfile=/var/log/celery/djangoblog.log \
    --pidfile=/var/run/celery/djangoblog.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown deploy:deploy /var/log/celery /var/run/celery
sudo systemctl daemon-reload
sudo systemctl enable djangoblog-celery
sudo systemctl start djangoblog-celery
```

---

## 11. Environment Variables Reference

| Variable                 | Required      | Description                               |
|--------------------------|---------------|-------------------------------------------|
| `SECRET_KEY`             | ✅ Always      | Django secret key (50+ chars)             |
| `DEBUG`                  | ✅ Always      | `True` in dev, `False` in prod            |
| `ALLOWED_HOSTS`          | ✅ Production  | Comma-separated domains                   |
| `DATABASE_URL`           | ✅ Production  | postgres://user:pass@host:port/db         |
| `REDIS_URL`              | ✅ Production  | redis://host:6379/db_index                |
| `EMAIL_BACKEND`          | Recommended   | Email backend class                       |
| `EMAIL_HOST_PASSWORD`    | Recommended   | SMTP / SendGrid API key                   |
| `DEFAULT_FROM_EMAIL`     | Recommended   | noreply@yourdomain.com                    |
| `USE_S3`                 | Optional      | `True` to use AWS S3 for files            |
| `AWS_ACCESS_KEY_ID`      | If USE_S3     | AWS credentials                           |
| `AWS_SECRET_ACCESS_KEY`  | If USE_S3     | AWS credentials                           |
| `AWS_STORAGE_BUCKET_NAME`| If USE_S3     | S3 bucket name                            |
| `SENTRY_DSN`             | Optional      | Sentry error tracking DSN                 |
| `SITE_ID`                | Optional      | Django sites framework ID (default 1)     |

---

## 12. Common Commands Cheat Sheet

```bash
# ── Development ──────────────────────────────────────────────────
python manage.py runserver                     # start dev server
python manage.py makemigrations                # create migrations
python manage.py migrate                       # apply migrations
python manage.py createsuperuser               # create admin user
python manage.py shell_plus                    # enhanced shell
python manage.py collectstatic                 # gather static files

# ── Production ───────────────────────────────────────────────────
sudo systemctl start|stop|restart djangoblog   # manage gunicorn
sudo systemctl status djangoblog               # check status
sudo journalctl -u djangoblog -f               # follow logs
sudo nginx -t && sudo systemctl reload nginx   # test & reload nginx

# ── Docker ──────────────────────────────────────────────────────
docker compose up -d --build                   # build & start all
docker compose down                            # stop all
docker compose logs -f web                     # follow web logs
docker compose exec web python manage.py shell # django shell
docker compose exec web python manage.py migrate
docker compose ps                              # list containers

# ── Database ─────────────────────────────────────────────────────
python manage.py dumpdata --indent 2 > backup.json   # export
python manage.py loaddata backup.json                 # import
pg_dump djangoblog > backup_$(date +%Y%m%d).sql      # postgres dump

# ── Git-based deploy update ──────────────────────────────────────
git pull origin main
source venv/bin/activate
pip install -r requirements/production.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart djangoblog
```

---

## .gitignore (recommended)

```gitignore
venv/
__pycache__/
*.py[cod]
.env
db.sqlite3
staticfiles/
media/
*.log
.DS_Store
.coverage
htmlcov/
dist/
build/
*.egg-info/
node_modules/
```
