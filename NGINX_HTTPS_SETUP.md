# NGINX + Let's Encrypt HTTPS 설정 가이드

도메인: **pensieve.borihopang.com**
백엔드 서비스: **http://0.0.0.0:8000**

## 사전 준비사항

1. **도메인 DNS 설정 확인**
   - `pensieve.borihopang.com`이 서버의 공인 IP를 가리키는지 확인
   ```bash
   nslookup pensieve.borihopang.com
   ```

2. **서버 방화벽 포트 열기**
   ```bash
   # HTTP (80) - Let's Encrypt 인증용
   sudo ufw allow 80/tcp

   # HTTPS (443) - 실제 서비스용
   sudo ufw allow 443/tcp

   # 방화벽 상태 확인
   sudo ufw status
   ```

---

## 1단계: Nginx 설치

```bash
# 패키지 목록 업데이트
sudo apt update

# nginx 설치
sudo apt install nginx -y

# nginx 시작 및 자동 시작 설정
sudo systemctl start nginx
sudo systemctl enable nginx

# nginx 상태 확인
sudo systemctl status nginx
```

---

## 2단계: Certbot (Let's Encrypt) 설치

```bash
# Certbot과 nginx 플러그인 설치
sudo apt install certbot python3-certbot-nginx -y

# 버전 확인
certbot --version
```

---

## 3단계: Nginx 설정 파일 생성

```bash
# 기존 default 설정 백업
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# 새로운 설정 파일 생성
sudo nano /etc/nginx/sites-available/pensieve.borihopang.com
```

아래 내용을 입력:

```nginx
# HTTP 서버 (Let's Encrypt 인증용)
server {
    listen 80;
    listen [::]:80;
    server_name pensieve.borihopang.com;

    # Let's Encrypt 인증 파일 경로
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # 나머지 모든 요청은 HTTPS로 리다이렉트
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 서버 (실제 서비스)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name pensieve.borihopang.com;

    # SSL 인증서 경로 (certbot이 자동으로 설정)
    # ssl_certificate /etc/letsencrypt/live/pensieve.borihopang.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/pensieve.borihopang.com/privkey.pem;

    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 로그 파일
    access_log /var/log/nginx/pensieve_access.log;
    error_log /var/log/nginx/pensieve_error.log;

    # MCP SSE 엔드포인트 (WebSocket 지원)
    location /sse {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 타임아웃 설정
        proxy_read_timeout 86400;
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }

    # MCP 관련 엔드포인트
    location /mcp {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # REST API 엔드포인트
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 인증 엔드포인트
    location /auth {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 대화 엔드포인트
    location /conversations {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 정적 파일 (대시보드)
    location /static {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # 헬스체크
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }

    # 루트 경로
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 4단계: 설정 파일 활성화

```bash
# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/pensieve.borihopang.com /etc/nginx/sites-enabled/

# 기존 default 설정 비활성화 (선택사항)
sudo rm /etc/nginx/sites-enabled/default

# nginx 설정 테스트
sudo nginx -t

# nginx 재시작
sudo systemctl reload nginx
```

---

## 5단계: SSL 인증서 발급

```bash
# Let's Encrypt SSL 인증서 발급
sudo certbot --nginx -d pensieve.borihopang.com

# 프롬프트 응답:
# 1. 이메일 입력 (인증서 만료 알림용)
# 2. 약관 동의 (Y)
# 3. 뉴스레터 구독 여부 (선택)
# 4. HTTP -> HTTPS 자동 리다이렉트 설정: 2 (Redirect)
```

Certbot이 자동으로:
- SSL 인증서 발급
- nginx 설정 파일 수정 (SSL 경로 추가)
- 자동 갱신 설정

---

## 6단계: 인증서 자동 갱신 확인

```bash
# 자동 갱신 테스트 (실제로 갱신하지 않음)
sudo certbot renew --dry-run

# 자동 갱신 타이머 확인
sudo systemctl status certbot.timer
```

Let's Encrypt 인증서는 **90일**마다 갱신이 필요하며, certbot이 자동으로 갱신합니다.

---

## 7단계: Docker Compose 설정 업데이트

docker-compose.yml의 환경 변수 추가:

```yaml
services:
  api:
    environment:
      - ALLOWED_ORIGINS=https://pensieve.borihopang.com
      - BASE_URL=https://pensieve.borihopang.com
```

---

## 8단계: 테스트

### 1. HTTP → HTTPS 리다이렉트 확인
```bash
curl -I http://pensieve.borihopang.com
# 출력: HTTP/1.1 301 Moved Permanently
# Location: https://pensieve.borihopang.com/
```

### 2. HTTPS 연결 확인
```bash
curl -I https://pensieve.borihopang.com/health
# 출력: HTTP/2 200
```

### 3. MCP SSE 엔드포인트 확인
```bash
curl -N https://pensieve.borihopang.com/sse
```

### 4. SSL 등급 테스트
브라우저에서: https://www.ssllabs.com/ssltest/analyze.html?d=pensieve.borihopang.com

---

## 9단계: Claude Code에서 사용

```bash
claude mcp add --transport sse pensieve https://pensieve.borihopang.com/sse
```

---

## 문제 해결

### 1. 포트 충돌
```bash
# 8000번 포트 사용 중인 프로세스 확인
sudo lsof -i :8000
sudo netstat -tulpn | grep :8000
```

### 2. Nginx 에러 로그 확인
```bash
sudo tail -f /var/log/nginx/pensieve_error.log
```

### 3. SSL 인증서 갱신 실패
```bash
# 수동 갱신 시도
sudo certbot renew --force-renewal

# nginx 재시작
sudo systemctl reload nginx
```

### 4. 방화벽 확인
```bash
# 현재 방화벽 규칙
sudo ufw status verbose

# 포트 다시 열기
sudo ufw allow 'Nginx Full'
```

### 5. Docker 서비스 확인
```bash
# 서비스 상태
cd /path/to/pensieve-mcp/api_server
docker-compose ps

# 로그 확인
docker-compose logs -f api
```

---

## 보안 권장사항

1. **UFW 방화벽 활성화**
   ```bash
   sudo ufw enable
   sudo ufw allow 22/tcp  # SSH
   sudo ufw allow 'Nginx Full'
   ```

2. **MongoDB 외부 접근 차단**
   docker-compose.yml 수정:
   ```yaml
   mongo:
     ports:
       - "127.0.0.1:27017:27017"  # 로컬만 허용
   ```

3. **강력한 JWT_SECRET 설정**
   ```bash
   # 랜덤 시크릿 생성
   openssl rand -hex 32

   # .env 파일에 추가
   echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
   ```

4. **fail2ban 설치** (SSH 브루트포스 방어)
   ```bash
   sudo apt install fail2ban -y
   sudo systemctl enable fail2ban
   ```

---

## 유지보수

### 인증서 수동 갱신
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Nginx 설정 변경 후
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 로그 정리
```bash
# 로그 용량 확인
sudo du -sh /var/log/nginx/

# 로그 정리 (로그로테이션)
sudo logrotate -f /etc/logrotate.d/nginx
```

---

## 완료!

이제 `https://pensieve.borihopang.com`으로 안전하게 접속 가능합니다! 🎉

**Claude Code 사용:**
```bash
claude mcp add --transport sse pensieve https://pensieve.borihopang.com/sse
```
