# Pensieve MCP - 간단한 클라우드 아키텍처

## 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph Clients["AI Clients"]
        Claude[Claude Desktop]
        ChatGPT[ChatGPT]
        Browser[Web Browser]
    end

    subgraph Server["Cloud Server"]
        API[FastAPI Server]
        SSE[MCP SSE]
        REST[REST API]
        Web[Web Dashboard]
    end

    subgraph Database["Database"]
        MongoDB[(MongoDB)]
    end

    Claude -->|MCP SSE| SSE
    ChatGPT -->|MCP SSE| SSE
    Browser -->|HTTPS| Web

    SSE --> API
    REST --> API
    Web --> REST

    API --> MongoDB

    style Claude fill:#9b59b6,stroke:#7c3aed,color:#fff
    style ChatGPT fill:#3498db,stroke:#2563eb,color:#fff
    style Browser fill:#10b981,stroke:#059669,color:#fff
    style Server fill:#f59e0b,stroke:#d97706
    style MongoDB fill:#ef4444,stroke:#dc2626,color:#fff
```

## 시스템 개요 (PPT용)

```mermaid
graph LR
    A[AI Assistants]
    B[MCP Protocol]
    C[Cloud Server]
    D[MongoDB]

    A --> B
    B --> C
    C --> D

    style A fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style B fill:#6366f1,stroke:#4f46e5,color:#fff
    style C fill:#f59e0b,stroke:#d97706,color:#fff
    style D fill:#ef4444,stroke:#dc2626,color:#fff
```

## 클라이언트별 접근 방식

```mermaid
graph TB
    C1[Claude Desktop]
    C2[ChatGPT]
    W1[Web Browser]

    Server[Cloud Server<br/>FastAPI]

    C1 -->|MCP SSE| Server
    C2 -->|MCP SSE| Server
    W1 -->|REST API| Server

    Server --> DB[(MongoDB)]

    style C1 fill:#9b59b6,stroke:#7c3aed,color:#fff
    style C2 fill:#3498db,stroke:#2563eb,color:#fff
    style W1 fill:#10b981,stroke:#059669,color:#fff
    style Server fill:#f59e0b,stroke:#d97706,color:#fff
    style DB fill:#ef4444,stroke:#dc2626,color:#fff
```

## 데이터 흐름 - 회원가입/로그인

```mermaid
sequenceDiagram
    actor User
    participant Claude
    participant Server
    participant DB

    User->>Claude: 회원가입/로그인
    Claude->>Server: email, password
    Server->>DB: 사용자 확인/생성
    DB-->>Server: 사용자 정보
    Server->>Server: JWT 토큰 생성
    Server-->>Claude: access_token
    Claude-->>User: 로그인 완료
```

## 데이터 흐름 - 대화 저장

```mermaid
sequenceDiagram
    actor User
    participant Claude
    participant Server
    participant DB

    User->>Claude: 대화 진행
    Claude->>Server: save_conversation
    Server->>Server: JWT 검증
    Server->>DB: 대화 저장
    DB-->>Server: conversation_id
    Server-->>Claude: 저장 완료
    Claude-->>User: 완료 메시지
```

## 데이터 흐름 - 대화 불러오기

```mermaid
sequenceDiagram
    actor User
    participant ChatGPT
    participant Server
    participant DB

    User->>ChatGPT: 이전 대화 불러오기
    ChatGPT->>Server: load_conversation
    Server->>Server: JWT 검증
    Server->>DB: 대화 조회
    DB-->>Server: 대화 데이터
    Server-->>ChatGPT: messages
    ChatGPT-->>User: 컨텍스트 로드 완료
```

## 서버 구조

```mermaid
graph TB
    subgraph API["FastAPI Server"]
        MCP[MCP SSE Endpoint]
        REST[REST API]
        Auth[JWT Authentication]
        Logic[Business Logic]
    end

    subgraph DB["Database"]
        MongoDB[(MongoDB)]
        Users[users]
        Convs[conversations]
    end

    MCP --> Auth
    REST --> Auth
    Auth --> Logic
    Logic --> MongoDB
    MongoDB --> Users
    MongoDB --> Convs

    style API fill:#fef3c7,stroke:#f59e0b
    style DB fill:#fee2e2,stroke:#ef4444
```

## MCP Tools (제공 기능)

```mermaid
graph TB
    MCP[MCP Server]

    A1[회원가입<br/>mcp_register]
    A2[로그인<br/>mcp_login]

    C1[대화 저장<br/>save_conversation]
    C2[대화 불러오기<br/>load_conversation]
    C3[대화 추가<br/>append_to_conversation]

    L1[대화 목록<br/>list_conversations]
    L2[대화 검색<br/>search_conversations]

    MCP --> A1
    MCP --> A2
    MCP --> C1
    MCP --> C2
    MCP --> C3
    MCP --> L1
    MCP --> L2

    style MCP fill:#6366f1,stroke:#4f46e5,color:#fff
    style A1 fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style A2 fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style C1 fill:#10b981,stroke:#059669,color:#fff
    style C2 fill:#10b981,stroke:#059669,color:#fff
    style C3 fill:#10b981,stroke:#059669,color:#fff
    style L1 fill:#3b82f6,stroke:#2563eb,color:#fff
    style L2 fill:#3b82f6,stroke:#2563eb,color:#fff
```

## 데이터 모델

```mermaid
erDiagram
    USER ||--o{ CONVERSATION : owns
    CONVERSATION ||--|{ MESSAGE : contains

    USER {
        string _id
        string email
        string hashed_password
        datetime created_at
    }

    CONVERSATION {
        string _id
        string user_id
        array messages
        object metadata
        datetime created_at
        datetime updated_at
    }

    MESSAGE {
        string role
        string content
    }
```

## 보안 구조

```mermaid
graph LR
    Request[Client Request]
    Auth[JWT Token]
    Verify[Token Verification]
    Access[Data Access]
    DB[(User's Data Only)]

    Request --> Auth
    Auth --> Verify
    Verify --> Access
    Access --> DB

    style Request fill:#e0e7ff,stroke:#6366f1
    style Auth fill:#fef3c7,stroke:#f59e0b
    style Verify fill:#dbeafe,stroke:#3b82f6
    style Access fill:#dcfce7,stroke:#10b981
    style DB fill:#fee2e2,stroke:#ef4444
```

## 멀티 유저 격리

```mermaid
graph TB
    U1[User A]
    U2[User B]
    U3[User C]

    Server[Cloud Server]

    D1[(User A's Data)]
    D2[(User B's Data)]
    D3[(User C's Data)]

    U1 -->|Token A| Server
    U2 -->|Token B| Server
    U3 -->|Token C| Server

    Server -->|user_id filter| D1
    Server -->|user_id filter| D2
    Server -->|user_id filter| D3

    style U1 fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style U2 fill:#3b82f6,stroke:#2563eb,color:#fff
    style U3 fill:#10b981,stroke:#059669,color:#fff
    style Server fill:#f59e0b,stroke:#d97706,color:#fff
    style D1 fill:#fee2e2,stroke:#ef4444
    style D2 fill:#fee2e2,stroke:#ef4444
    style D3 fill:#fee2e2,stroke:#ef4444
```

## 배포 구조

```mermaid
graph TB
    Internet([Internet])

    Server[Cloud Server<br/>FastAPI]

    DB[(MongoDB<br/>Cloud Database)]

    Internet --> Server
    Server --> DB

    style Internet fill:#e0e7ff,stroke:#6366f1
    style Server fill:#fef3c7,stroke:#f59e0b
    style DB fill:#fee2e2,stroke:#ef4444
```

## 기술 스택

```mermaid
graph TB
    subgraph Frontend["Frontend"]
        HTML[HTML/CSS/JS]
    end

    subgraph Backend["Backend"]
        FastAPI[FastAPI]
        FastMCP[FastMCP]
    end

    subgraph Security["Security"]
        JWT[JWT Token]
        Bcrypt[Bcrypt Hash]
    end

    subgraph Database["Database"]
        MongoDB[(MongoDB)]
    end

    Frontend --> Backend
    Backend --> Security
    Backend --> Database

    style Frontend fill:#e0e7ff,stroke:#6366f1
    style Backend fill:#fef3c7,stroke:#f59e0b
    style Security fill:#fee2e2,stroke:#ef4444
    style Database fill:#dcfce7,stroke:#10b981
```

## 사용자 여정

```mermaid
journey
    title Pensieve 사용 흐름
    section 초기 설정
      회원가입: 5: User
      로그인: 5: User
    section Claude 사용
      대화 진행: 5: Claude
      대화 저장: 5: Claude
    section ChatGPT 사용
      대화 불러오기: 5: ChatGPT
      이어서 대화: 5: ChatGPT
    section 웹 관리
      대시보드 접속: 4: User
      대화 검색: 4: User
```

## 핵심 기능

```mermaid
mindmap
  root((Pensieve))
    Multi User
      회원가입/로그인
      JWT 인증
      사용자 격리
    Conversation
      저장
      불러오기
      검색
      이어쓰기
    Cross Platform
      Claude
      ChatGPT
      Web Dashboard
    Cloud
      FastAPI 서버
      MongoDB 데이터베이스
```

## 주요 특징

### 1. **멀티 유저 지원**
- JWT 토큰 기반 인증
- 사용자별 데이터 완전 격리
- Bcrypt 비밀번호 암호화

### 2. **Cross-Platform**
- Claude Desktop (MCP SSE)
- ChatGPT (MCP SSE)
- Web Dashboard (REST API)

### 3. **간단한 클라우드 구조**
- FastAPI 서버
- MongoDB 데이터베이스
- HTTPS 암호화 통신

### 4. **보안**
- JWT 토큰 인증 (24시간)
- 사용자별 권한 검증
- 비밀번호 해싱

---

## 🎨 PPT 추천 슬라이드

1. **시스템 개요** - 4개 블록 다이어그램
2. **클라이언트별 접근** - 3가지 사용 방식
3. **데이터 흐름** - 대화 저장/불러오기
4. **MCP Tools** - 제공하는 기능들
5. **멀티 유저 격리** - 보안 구조
6. **기술 스택** - 사용 기술
