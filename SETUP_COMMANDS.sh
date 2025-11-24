#!/bin/bash
# Ubuntu 서버에서 실행할 NGINX + Let's Encrypt 설정 명령어

echo "============================================"
echo "Pensieve MCP - NGINX + HTTPS 자동 설정"
echo "도메인: pensieve.borihopang.com"
echo "============================================"

# 1단계: 기본 패키지 설치
echo ""
echo "1단계: Nginx 및 Certbot 설치..."
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y

# 2단계: 방화벽 설정
echo ""
echo "2단계: 방화벽 설정..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status

# 3단계: 초기 Nginx 설정 (SSL 발급 전)
echo ""
echo "3단계: 초기 Nginx 설정..."

sudo tee /etc/nginx/sites-available/pensieve.borihopang.com > /dev/null <<'EOF'
# 초기 설정 - SSL 인증서 발급 전
server {
    listen 80;
    listen [::]:80;
    server_name pensieve.borihopang.com;

    # Let's Encrypt 인증 파일 경로
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # 모든 요청을 백엔드로 프록시
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket/SSE 지원
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 기본 헤더
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE/WebSocket 타임아웃
        proxy_read_timeout 86400;
        proxy_buffering off;
        proxy_cache off;
    }
}
EOF

# 4단계: 설정 활성화
echo ""
echo "4단계: Nginx 설정 활성화..."
sudo ln -sf /etc/nginx/sites-available/pensieve.borihopang.com /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl reload nginx

# 5단계: SSL 인증서 발급
echo ""
echo "5단계: Let's Encrypt SSL 인증서 발급..."
echo "주의: 이메일 입력 및 약관 동의가 필요합니다."

sudo certbot certonly --nginx -d pensieve.borihopang.com

# 6단계: 최종 Nginx 설정 (HTTPS 포함)
echo ""
echo "6단계: 최종 Nginx 설정 (HTTPS)..."

sudo tee /etc/nginx/sites-available/pensieve.borihopang.com > /dev/null <<'EOF'
# HTTP 서버 - HTTPS로 리다이렉트
server {
    listen 80;
    listen [::]:80;
    server_name pensieve.borihopang.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 서버
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name pensieve.borihopang.com;

    ssl_certificate /etc/letsencrypt/live/pensieve.borihopang.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pensieve.borihopang.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    access_log /var/log/nginx/pensieve_access.log;
    error_log /var/log/nginx/pensieve_error.log;

    # 모든 요청을 백엔드로 프록시
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket/SSE 지원
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 기본 헤더
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE/WebSocket 타임아웃
        proxy_read_timeout 86400;
        proxy_buffering off;
        proxy_cache off;
    }
}
EOF

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl reload nginx

# 7단계: 자동 갱신 테스트
echo ""
echo "7단계: 인증서 자동 갱신 테스트..."
sudo certbot renew --dry-run

# 완료
echo ""
echo "============================================"
echo "✅ 설정 완료!"
echo "============================================"
echo ""
echo "테스트 명령어:"
echo "  curl -I http://pensieve.borihopang.com"
echo "  curl -I https://pensieve.borihopang.com/health"
echo ""
echo "Claude Code에서 사용:"
echo "  claude mcp add --transport sse pensieve https://pensieve.borihopang.com/sse"
echo ""
