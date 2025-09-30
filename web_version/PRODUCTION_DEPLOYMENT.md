# Production Deployment Guide

**Deploying Excel Consolidator Pro for 90,000+ Concurrent Users**

This guide follows enterprise best practices for horizontal scaling, performance, security, and reliability.

---

## 🎯 Architecture Overview

### Scalable Architecture for 90k Users

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │  (Nginx/AWS ALB)│
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐      ┌─────▼─────┐    ┌─────▼─────┐
    │  App      │      │  App      │    │  App      │
    │  Server 1 │      │  Server 2 │... │  Server N │
    │  (Flask)  │      │  (Flask)  │    │  (Flask)  │
    └─────┬─────┘      └─────┬─────┘    └─────┬─────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Task Queue     │
                    │  (Celery +      │
                    │   RabbitMQ)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Cache Layer    │
                    │  (Redis)        │
                    └─────────────────┘
```

### Key Components

1. **Load Balancer** - Distributes traffic across app servers
2. **Stateless App Servers** - Flask applications (no local state)
3. **Task Queue** - Celery workers for async processing
4. **Cache Layer** - Redis for sessions and caching
5. **CDN** - CloudFront/Cloudflare for static assets

---

## 🚀 Deployment Steps

### 1. Application Server Setup

#### Install Dependencies

```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3.9 python3-pip nginx redis-server rabbitmq-server

# Python dependencies
cd web_version
pip install -r requirements.txt
pip install gunicorn celery redis flask-limiter
```

#### Configure Gunicorn

Create `gunicorn_config.py`:

```python
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = "excel_consolidator_pro"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/excel_consolidator.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
```

#### Create Systemd Service

Create `/etc/systemd/system/excel-consolidator.service`:

```ini
[Unit]
Description=Excel Consolidator Pro Web Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/excel-consolidator/web_version
Environment="PATH=/var/www/excel-consolidator/venv/bin"
ExecStart=/var/www/excel-consolidator/venv/bin/gunicorn \
    --config gunicorn_config.py \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable excel-consolidator
sudo systemctl start excel-consolidator
```

---

### 2. Celery Worker Setup (Async Processing)

#### Update `app.py` for Celery

```python
from celery import Celery
from flask import Flask
import os

app = Flask(__name__)

# Celery configuration
app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery
celery = Celery(
    app.name,
    broker=app.config['CELERY_BROKER_URL'],
    backend=app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

@celery.task(bind=True)
def process_consolidation_async(self, job_id, template_path, source_folder, settings):
    """Async task for file consolidation"""
    from services.consolidator import ExcelConsolidator
    
    try:
        # Update task state
        self.update_state(state='PROCESSING', meta={'current': 0, 'total': 0})
        
        # Create consolidator
        consolidator = ExcelConsolidator(
            template_path=template_path,
            source_folder=source_folder,
            settings=settings,
            progress_callback=lambda c, t, f: self.update_state(
                state='PROCESSING',
                meta={'current': c, 'total': t, 'file': f}
            )
        )
        
        # Run consolidation
        output_path = consolidator.consolidate()
        
        return {
            'status': 'completed',
            'output_path': output_path
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Update consolidate endpoint
@app.route('/api/consolidate', methods=['POST'])
@limiter.limit("10 per hour")  # Rate limiting
def consolidate():
    # ... file upload code ...
    
    # Queue task instead of processing immediately
    task = process_consolidation_async.delay(
        job_id,
        template_path,
        source_folder,
        settings
    )
    
    # Store task ID in Redis
    redis_client.setex(f"job:{job_id}", 3600, task.id)
    
    return jsonify({
        'job_id': job_id,
        'task_id': task.id,
        'message': 'Consolidation queued',
        'total_files': len(source_paths)
    }), 202  # 202 Accepted
```

#### Celery Worker Service

Create `/etc/systemd/system/excel-consolidator-worker.service`:

```ini
[Unit]
Description=Excel Consolidator Celery Worker
After=network.target redis.service rabbitmq-server.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/excel-consolidator/web_version
Environment="PATH=/var/www/excel-consolidator/venv/bin"
ExecStart=/var/www/excel-consolidator/venv/bin/celery -A app.celery worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start workers:

```bash
sudo systemctl enable excel-consolidator-worker
sudo systemctl start excel-consolidator-worker
```

---

### 3. Nginx Load Balancer Configuration

Create `/etc/nginx/sites-available/excel-consolidator`:

```nginx
upstream excel_consolidator_backend {
    least_conn;  # Load balancing method
    
    # Backend servers
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
    # Add more servers as needed
    
    keepalive 64;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/m;

# Cache for static assets
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=static_cache:10m 
                 max_size=1g inactive=60m use_temp_path=off;

server {
    listen 80;
    listen [::]:80;
    server_name excelconsolidator.com www.excelconsolidator.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name excelconsolidator.com www.excelconsolidator.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/excelconsolidator.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/excelconsolidator.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;" always;
    
    # Client body size (100MB for file uploads)
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    
    # Timeouts
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;
    
    # Static files (served from CDN in production)
    location /static/ {
        alias /var/www/excel-consolidator/web_version/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Gzip compression
        gzip on;
        gzip_types text/css application/javascript image/svg+xml;
        gzip_vary on;
    }
    
    # API endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://excel_consolidator_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Upload endpoint (stricter rate limit)
    location /api/consolidate {
        limit_req zone=upload_limit burst=5 nodelay;
        
        proxy_pass http://excel_consolidator_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_request_buffering off;  # Stream uploads
    }
    
    # Main application
    location / {
        proxy_pass http://excel_consolidator_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Caching for HTML
        proxy_cache static_cache;
        proxy_cache_valid 200 10m;
        proxy_cache_bypass $http_pragma $http_authorization;
        add_header X-Cache-Status $upstream_cache_status;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://excel_consolidator_backend;
        access_log off;
    }
    
    # Error pages
    error_page 502 503 504 /50x.html;
    location = /50x.html {
        root /var/www/html;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/excel-consolidator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### 4. Redis Configuration

Edit `/etc/redis/redis.conf`:

```conf
# Network
bind 127.0.0.1
port 6379
protected-mode yes

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_strong_redis_password_here

# Performance
timeout 300
tcp-keepalive 60
```

Restart Redis:

```bash
sudo systemctl restart redis-server
```

---

### 5. Auto-Scaling (AWS Example)

#### Launch Template

```json
{
  "LaunchTemplateName": "excel-consolidator-template",
  "VersionDescription": "v1",
  "LaunchTemplateData": {
    "ImageId": "ami-0c55b159cbfafe1f0",
    "InstanceType": "t3.medium",
    "KeyName": "your-key-pair",
    "SecurityGroupIds": ["sg-xxxxxxxxx"],
    "IamInstanceProfile": {
      "Name": "excel-consolidator-role"
    },
    "UserData": "BASE64_ENCODED_STARTUP_SCRIPT",
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [
        {"Key": "Name", "Value": "excel-consolidator-server"},
        {"Key": "Environment", "Value": "production"}
      ]
    }]
  }
}
```

#### Auto Scaling Group

```json
{
  "AutoScalingGroupName": "excel-consolidator-asg",
  "LaunchTemplate": {
    "LaunchTemplateName": "excel-consolidator-template",
    "Version": "$Latest"
  },
  "MinSize": 3,
  "MaxSize": 20,
  "DesiredCapacity": 3,
  "DefaultCooldown": 300,
  "HealthCheckType": "ELB",
  "HealthCheckGracePeriod": 300,
  "VPCZoneIdentifier": "subnet-xxx,subnet-yyy,subnet-zzz",
  "TargetGroupARNs": ["arn:aws:elasticloadbalancing:..."],
  "Tags": [
    {"Key": "Name", "Value": "excel-consolidator-server"},
    {"Key": "Environment", "Value": "production"}
  ]
}
```

#### Scaling Policies

```bash
# Scale up when CPU > 70% for 5 minutes
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name excel-consolidator-asg \
  --policy-name scale-up \
  --scaling-adjustment 2 \
  --adjustment-type ChangeInCapacity \
  --cooldown 300

# Scale down when CPU < 30% for 5 minutes
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name excel-consolidator-asg \
  --policy-name scale-down \
  --scaling-adjustment -1 \
  --adjustment-type ChangeInCapacity \
  --cooldown 300
```

---

### 6. Monitoring & Alerts

#### Prometheus Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'excel-consolidator'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

#### Grafana Dashboards

Key metrics to monitor:

- **HTTP Request Rate** (requests/second)
- **HTTP Error Rate** (5xx errors %)
- **Response Time** (p50, p95, p99)
- **CPU Usage** (%)
- **Memory Usage** (%)
- **Celery Queue Length** (tasks)
- **Database Connection Pool** (active/idle)
- **Cache Hit Rate** (%)

#### Alert Rules

```yaml
groups:
  - name: excel_consolidator_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High HTTP error rate detected"
          
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          
      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 1000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Large Celery queue backlog"
```

---

### 7. CDN Configuration (CloudFront)

#### Static Assets Distribution

```json
{
  "DistributionConfig": {
    "CallerReference": "excel-consolidator-static",
    "Comment": "Excel Consolidator static assets",
    "Enabled": true,
    "Origins": [{
      "Id": "S3-excel-consolidator-static",
      "DomainName": "excel-consolidator-static.s3.amazonaws.com",
      "S3OriginConfig": {
        "OriginAccessIdentity": ""
      }
    }],
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3-excel-consolidator-static",
      "ViewerProtocolPolicy": "redirect-to-https",
      "AllowedMethods": ["GET", "HEAD"],
      "CachedMethods": ["GET", "HEAD"],
      "Compress": true,
      "MinTTL": 0,
      "DefaultTTL": 86400,
      "MaxTTL": 31536000
    }
  }
}
```

Update HTML to use CDN:

```html
<link rel="stylesheet" href="https://cdn.excelconsolidator.com/css/style.css">
<script src="https://cdn.excelconsolidator.com/js/main.js"></script>
```

---

### 8. Security Hardening

#### Environment Variables

Create `.env`:

```bash
# Application
FLASK_ENV=production
SECRET_KEY=your_secret_key_here_min_32_chars

# Redis
REDIS_URL=redis://:password@localhost:6379/0

# Celery
CELERY_BROKER_URL=amqp://user:pass@localhost:5672//
CELERY_RESULT_BACKEND=redis://:password@localhost:6379/1

# File Storage
MAX_CONTENT_LENGTH=104857600  # 100MB
UPLOAD_FOLDER=/var/uploads/excel-consolidator
OUTPUT_FOLDER=/var/outputs/excel-consolidator

# Security
ALLOWED_ORIGINS=https://excelconsolidator.com
RATE_LIMIT_ENABLED=true
```

#### Flask-Limiter Setup

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri=os.getenv('REDIS_URL')
)

# Apply to specific routes
@app.route('/api/consolidate', methods=['POST'])
@limiter.limit("10 per hour")
def consolidate():
    # ...
```

---

### 9. Database (Optional - for Job History)

If you decide to add a database for job history:

#### PostgreSQL Setup

```sql
CREATE DATABASE excel_consolidator;

CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    template_filename VARCHAR(255),
    source_file_count INTEGER,
    output_filename VARCHAR(255),
    error_message TEXT
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

#### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    os.getenv('DATABASE_URL'),
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)
```

---

### 10. Backup & Disaster Recovery

#### Automated Backups

```bash
#!/bin/bash
# /usr/local/bin/backup-excel-consolidator.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/excel-consolidator

# Backup Redis
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /etc/nginx /etc/systemd/system/excel-*

# Upload to S3
aws s3 cp $BACKUP_DIR s3://excel-consolidator-backups/$DATE/ --recursive

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -type f -mtime +30 -delete
```

Cron job:

```bash
0 2 * * * /usr/local/bin/backup-excel-consolidator.sh
```

---

## 📊 Performance Testing

### Load Testing with Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class ExcelConsolidatorUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def view_home(self):
        self.client.get("/")
    
    @task(1)
    def upload_and_consolidate(self):
        files = {
            'template': ('template.xlsx', open('test_files/template.xlsx', 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            'sources': ('file1.xlsx', open('test_files/file1.xlsx', 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        
        response = self.client.post("/api/consolidate", files=files)
        
        if response.status_code == 202:
            job_id = response.json()['job_id']
            
            # Poll status
            while True:
                status_response = self.client.get(f"/api/status/{job_id}")
                if status_response.json()['status'] in ['completed', 'error']:
                    break
```

Run load test:

```bash
locust -f locustfile.py --host=https://excelconsolidator.com --users 10000 --spawn-rate 100
```

---

## ✅ Production Checklist

### Pre-Launch
- [ ] SSL/TLS certificates installed
- [ ] Environment variables configured
- [ ] Secret keys generated (min 32 characters)
- [ ] Rate limiting enabled
- [ ] CORS configured
- [ ] Security headers set
- [ ] Error tracking setup (Sentry)
- [ ] Logging configured
- [ ] Monitoring dashboards created
- [ ] Alerts configured
- [ ] Load testing completed
- [ ] Backup system tested
- [ ] Disaster recovery plan documented

### Infrastructure
- [ ] Auto-scaling policies configured
- [ ] Health checks enabled
- [ ] CDN configured for static assets
- [ ] Redis cluster setup
- [ ] Database connection pooling
- [ ] File storage configured
- [ ] Log aggregation setup

### Security
- [ ] Firewall rules configured
- [ ] SSH keys rotated
- [ ] Application firewall (WAF) enabled
- [ ] DDoS protection enabled
- [ ] Secrets stored in vault
- [ ] Audit logging enabled
- [ ] Security scanning automated

### Performance
- [ ] Caching strategy implemented
- [ ] Database queries optimized
- [ ] Static assets minified
- [ ] Images optimized
- [ ] Gzip compression enabled
- [ ] HTTP/2 enabled

---

## 📞 Support

For deployment issues or questions:
- Email: devops@excelconsolidator.com
- Slack: #excel-consolidator-ops
- Documentation: https://docs.excelconsolidator.com

---

**This deployment guide ensures your Excel Consolidator Pro can handle 90,000+ concurrent users with high availability, performance, and security.**

© 2025 Excel Consolidator Pro
