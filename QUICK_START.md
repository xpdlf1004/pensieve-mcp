# Pensieve MCP - 빠른 시작 가이드

## 🚀 서버 실행 (개발자용)

### 1. Docker로 실행 (가장 쉬움)

```bash
cd api_server
docker-compose up -d
```

이제 서버가 `http://localhost:8000`에서 실행됩니다!

### 2. 확인

```bash
curl http://localhost:8000/health
```

응답: `{"message":"Pensieve API","version":"1.0.0","status":"healthy"}`

---

## 👥 사용자 설정 (Claude Code)

### Claude Code 사용자 (추천 ⭐)

**한 줄로 설정 끝:**

```bash
claude mcp add --transport sse pensieve http://localhost:8000/sse
```

**또는 배포된 서버 사용:**

```bash
claude mcp add --transport sse pensieve https://your-server.com/sse
```

### 사용 방법

1. **로그인**:
   ```
   "login 도구를 사용해서 test@example.com / password로 로그인해줘"
   ```

2. **대화 저장**:
   ```
   "지금까지의 대화를 저장해줘"
   ```

3. **대화 목록 보기**:
   ```
   "저장된 대화 목록 보여줘"
   ```

---

## 📝 Claude Desktop 사용자

Claude Desktop은 아직 직접 URL을 지원하지 않습니다.
**npx를 사용하세요:**

### 설정 파일

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pensieve": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/sse"]
    }
  }
}
```

**배포된 서버 사용:**

```json
{
  "mcpServers": {
    "pensieve": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://your-server.com/sse"]
    }
  }
}
```

Claude Desktop 재시작 후 사용 가능합니다!

---

## 🌐 서버 배포

### Railway로 배포 (무료)

```bash
npm i -g @railway/cli
cd api_server
railway login
railway init
railway up
```

### Render로 배포 (무료)

1. GitHub에 푸시
2. [Render.com](https://render.com) 접속
3. "New +" → "Web Service"
4. 리포지토리 선택
5. 배포 완료!

배포 후 URL을 받아서 위 설정의 `http://localhost:8000`을 `https://your-app.railway.app`로 변경하세요.

---

## 🔑 계정 생성

### 방법 1: 웹 대시보드

```
http://localhost:8000/
```

### 방법 2: API 직접 호출

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### 방법 3: Claude에게 시키기

```
"register 도구로 test@example.com / password123 계정 만들어줘"
```

---

## ⚡ 특징

✅ **코드 다운로드 불필요**: 서버 URL만 있으면 됨
✅ **다중 사용자 지원**: 각자 독립된 계정
✅ **보안**: JWT 인증
✅ **쉬운 배포**: Docker, Railway, Render 지원
✅ **Claude Code 최적화**: 한 줄로 설정 완료

---

## 🐛 문제 해결

### "connection refused"
- 서버가 실행 중인지 확인: `docker-compose ps`
- 포트 충돌 확인: `lsof -i :8000`

### "login failed"
- 계정이 있는지 확인
- 비밀번호 6자 이상인지 확인

### SSE 연결 실패
- CORS 설정 확인 (이미 `*` 허용으로 설정됨)
- 방화벽 확인

---

## 📚 더 알아보기

- [전체 사용 가이드](USER_GUIDE.md)
- [배포 가이드](deploy/README.md)
- [API 문서](http://localhost:8000/docs)
