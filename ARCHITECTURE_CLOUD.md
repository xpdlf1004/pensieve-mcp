# Pensieve MCP - Cloud Architecture

## 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph Clients["AI Clients"]
        Claude[Claude Desktop]
        ChatGPT[ChatGPT]
        Browser[Web Browser]
    end

    subgraph MCP["MCP Protocol Layer"]
        MCPSSE[MCP SSE Client]
    end

    subgraph Azure["Azure Cloud"]
        subgraph API["FastAPI Server"]
            SSE[SSE Endpoint<br/>/sse]
            REST[REST API<br/>/api/*]
            Auth[Authentication<br/>/auth/*]
            WebUI[Web Pages<br/>/, /dashboard]
        end

        subgraph DB["Data Storage"]
            MongoDB[(Azure Cosmos DB<br/>MongoDB API)]
            Users[users collection]
            Convs[conversations collection]
        end
    end

    Claude -->|MCP SSE| MCPSSE
    ChatGPT -->|MCP SSE| MCPSSE
    Browser -->|HTTPS| WebUI

    MCPSSE --> SSE
    WebUI --> REST

    SSE --> Auth
    REST --> Auth

    Auth --> MongoDB
    MongoDB --> Users
    MongoDB --> Convs

    style Claude fill:#9b59b6,stroke:#7c3aed,color:#fff
    style ChatGPT fill:#3498db,stroke:#2563eb,color:#fff
    style Browser fill:#10b981,stroke:#059669,color:#fff
    style MCPSSE fill:#6366f1,stroke:#4f46e5,color:#fff
    style API fill:#f59e0b,stroke:#d97706
    style MongoDB fill:#ef4444,stroke:#dc2626,color:#fff
```

## 클라이언트별 접근 방식

```mermaid
graph LR
    subgraph Desktop["Desktop Apps"]
        C1[Claude Desktop]
        C2[ChatGPT Desktop]
    end

    subgraph Web["Web Access"]
        W1[Chrome/Safari/Edge]
    end

    subgraph Server["Cloud Server"]
        MCP[MCP SSE Endpoint]
        API[REST API]
        Auth[JWT Auth]
    end

    C1 -->|MCP Protocol| MCP
    C2 -->|MCP Protocol| MCP
    W1 -->|HTTPS| API

    MCP --> Auth
    API --> Auth

    style Desktop fill:#e0e7ff,stroke:#6366f1
    style Web fill:#dcfce7,stroke:#10b981
    style Server fill:#fef3c7,stroke:#f59e0b
```

## 데이터 흐름 - 회원가입/로그인

```mermaid
sequenceDiagram
    actor User
    participant Claude
    participant MCP
    participant API
    participant DB

    User->>Claude: 회원가입/로그인 요청
    Claude->>MCP: mcp_register/mcp_login
    MCP->>API: SSE 요청 (email, password)
    API->>DB: 사용자 확인/생성
    DB-->>API: 사용자 정보
    API->>API: Bcrypt 검증<br/>JWT 토큰 생성
    API-->>MCP: access_token
    MCP->>MCP: 세션에 토큰 저장
    MCP-->>Claude: 로그인 성공
    Claude-->>User: 인증 완료 메시지
```

## 데이터 흐름 - 대화 저장

```mermaid
sequenceDiagram
    actor User
    participant Claude
    participant MCP
    participant API
    participant DB

    User->>Claude: 대화 진행
    Claude->>MCP: save_conversation(email, messages)
    MCP->>API: SSE 요청 + JWT token
    API->>API: JWT 토큰 검증
    API->>DB: 대화 문서 삽입<br/>{user_id, messages, metadata}
    DB-->>API: conversation_id
    API-->>MCP: 저장 완료 + ID
    MCP-->>Claude: 성공 메시지
    Claude-->>User: "대화가 저장되었습니다"
```

## 데이터 흐름 - 대화 불러오기

```mermaid
sequenceDiagram
    actor User
    participant ChatGPT
    participant MCP
    participant API
    participant DB

    User->>ChatGPT: 이전 대화 불러오기
    ChatGPT->>MCP: load_conversation(email, conv_id)
    MCP->>API: SSE 요청 + JWT token
    API->>API: JWT 검증 + 권한 확인
    API->>DB: 대화 조회<br/>{_id, user_id}
    DB-->>API: 대화 데이터
    API-->>MCP: messages + metadata
    MCP-->>ChatGPT: 대화 내용
    ChatGPT-->>User: 컨텍스트 로드 완료
```

## API Server 아키텍처

```mermaid
graph TB
    subgraph Presentation["Presentation Layer"]
        SSE[MCP SSE<br/>FastMCP]
        REST[REST API<br/>FastAPI]
        Static[Static Files<br/>HTML/CSS/JS]
    end

    subgraph Security["Security Layer"]
        JWT[JWT Validation]
        Bcrypt[Password Hashing]
        CORS[CORS Middleware]
    end

    subgraph Business["Business Logic"]
        Conv[Conversation Logic]
        User[User Management]
        Search[Search Logic]
    end

    subgraph Data["Data Access Layer"]
        Motor[Motor AsyncIO<br/>MongoDB Driver]
        MongoDB[(Cosmos DB)]
    end

    SSE --> JWT
    REST --> JWT
    Static --> CORS

    JWT --> Conv
    JWT --> User
    Bcrypt --> User

    Conv --> Motor
    User --> Motor
    Search --> Motor
    Motor --> MongoDB

    style Presentation fill:#e0e7ff,stroke:#6366f1
    style Security fill:#fef3c7,stroke:#f59e0b
    style Business fill:#dbeafe,stroke:#3b82f6
    style Data fill:#fee2e2,stroke:#ef4444
```

## MCP Tools (사용 가능한 기능)

```mermaid
graph TB
    MCP[MCP Server]

    subgraph Auth["인증 관리"]
        T1[mcp_register]
        T2[mcp_login]
        T3[set_api_token]
    end

    subgraph Conv["대화 관리"]
        T4[save_conversation]
        T5[load_conversation]
        T6[append_to_conversation]
    end

    subgraph Query["조회/검색"]
        T7[list_conversations]
        T8[search_conversations]
    end

    MCP --> Auth
    MCP --> Conv
    MCP --> Query

    style MCP fill:#6366f1,stroke:#4f46e5,color:#fff
    style Auth fill:#8b5cf6,stroke:#7c3aed
    style Conv fill:#10b981,stroke:#059669
    style Query fill:#3b82f6,stroke:#2563eb
```

## 데이터 모델

```mermaid
erDiagram
    USER ||--o{ CONVERSATION : owns
    CONVERSATION ||--|{ MESSAGE : contains

    USER {
        string _id PK "UUID"
        string email UK "이메일"
        string hashed_password "Bcrypt 해시"
        datetime created_at "생성일시"
    }

    CONVERSATION {
        string _id PK "UUID"
        string user_id FK "소유자"
        array messages "메시지 배열"
        object metadata "메타데이터"
        datetime created_at "생성일시"
        datetime updated_at "수정일시"
    }

    MESSAGE {
        string role "user/assistant/system"
        string content "메시지 내용"
    }
```

## Azure 배포 아키텍처

```mermaid
graph TB
    Internet([Internet])

    subgraph Azure["Microsoft Azure"]
        subgraph Network["Networking"]
            DNS[Azure DNS]
            LB[Load Balancer<br/>HTTPS Ingress]
        end

        subgraph Compute["Container Apps"]
            C1[FastAPI Instance 1]
            C2[FastAPI Instance 2]
            C3[FastAPI Instance N]
        end

        subgraph Database["Cosmos DB"]
            Primary[(Primary Region)]
            Replica[(Replica Region)]
        end

        subgraph Config["Configuration"]
            Env[Environment Variables]
            Secrets[Key Vault]
        end
    end

    Internet --> DNS
    DNS --> LB
    LB --> C1
    LB --> C2
    LB --> C3

    C1 --> Primary
    C2 --> Primary
    C3 --> Primary

    Primary -.복제.-> Replica

    C1 -.읽기.-> Env
    C1 -.읽기.-> Secrets

    style Internet fill:#e0e7ff,stroke:#6366f1
    style Network fill:#dbeafe,stroke:#3b82f6
    style Compute fill:#fef3c7,stroke:#f59e0b
    style Database fill:#fee2e2,stroke:#ef4444
    style Config fill:#dcfce7,stroke:#10b981
```

## 보안 아키텍처

```mermaid
graph TB
    Request[Client Request]

    subgraph Layer1["Transport Security"]
        HTTPS[HTTPS/TLS 1.3]
        CORS[CORS Policy]
    end

    subgraph Layer2["Authentication"]
        JWT[JWT Token<br/>24h expiration]
        Bcrypt[Bcrypt Hash<br/>Password]
    end

    subgraph Layer3["Authorization"]
        Validation[Token Validation]
        UserCheck[User ID Check]
    end

    subgraph Layer4["Data Security"]
        Isolation[User Data Isolation]
        Encryption[Data Encryption<br/>at rest]
    end

    Request --> HTTPS
    HTTPS --> CORS
    CORS --> JWT
    JWT --> Bcrypt
    Bcrypt --> Validation
    Validation --> UserCheck
    UserCheck --> Isolation
    Isolation --> Encryption

    style Request fill:#e0e7ff,stroke:#6366f1
    style Layer1 fill:#dbeafe,stroke:#3b82f6
    style Layer2 fill:#fef3c7,stroke:#f59e0b
    style Layer3 fill:#dcfce7,stroke:#10b981
    style Layer4 fill:#fee2e2,stroke:#ef4444
```

## 멀티 유저 격리

```mermaid
graph LR
    subgraph Users["사용자들"]
        U1[User A]
        U2[User B]
        U3[User C]
    end

    subgraph Auth["인증"]
        T1[Token A]
        T2[Token B]
        T3[Token C]
    end

    subgraph Server["서버"]
        API[Shared API]
    end

    subgraph DB["데이터베이스"]
        D1[User A's Data]
        D2[User B's Data]
        D3[User C's Data]
    end

    U1 --> T1
    U2 --> T2
    U3 --> T3

    T1 --> API
    T2 --> API
    T3 --> API

    API -->|user_id filter| D1
    API -->|user_id filter| D2
    API -->|user_id filter| D3

    style Users fill:#e0e7ff,stroke:#6366f1
    style Auth fill:#fef3c7,stroke:#f59e0b
    style Server fill:#dbeafe,stroke:#3b82f6
    style DB fill:#dcfce7,stroke:#10b981
```

## 사용자 여정

```mermaid
journey
    title Pensieve 사용 흐름
    section 초기 설정
      회원가입: 5: User
      Claude 설정: 4: User
      로그인: 5: User
    section Claude 사용
      대화 진행: 5: User, Claude
      대화 저장: 5: User
    section ChatGPT 사용
      로그인: 5: User
      대화 목록 조회: 4: User
      대화 불러오기: 5: User, ChatGPT
      이어서 대화: 5: User, ChatGPT
    section 웹 대시보드
      대시보드 접속: 4: User
      대화 검색: 4: User
      대화 삭제: 3: User
```

## 기술 스택

```mermaid
graph TB
    subgraph Frontend["Frontend"]
        HTML[HTML5]
        CSS[CSS3]
        JS[JavaScript]
    end

    subgraph Backend["Backend"]
        FastAPI[FastAPI]
        FastMCP[FastMCP]
        Pydantic[Pydantic]
    end

    subgraph Security["Security"]
        JWT_LIB[python-jose]
        BCrypt[passlib]
        HTTPBearer[HTTPBearer]
    end

    subgraph Database["Database"]
        Motor[Motor<br/>Async MongoDB]
        CosmosDB[Azure Cosmos DB<br/>MongoDB API]
    end

    subgraph Infrastructure["Infrastructure"]
        Docker[Docker]
        Azure[Azure Container Apps]
        HTTPS[HTTPS/TLS]
    end

    Frontend --> Backend
    Backend --> Security
    Backend --> Database
    Database --> Infrastructure

    style Frontend fill:#e0e7ff,stroke:#6366f1
    style Backend fill:#fef3c7,stroke:#f59e0b
    style Security fill:#fee2e2,stroke:#ef4444
    style Database fill:#dcfce7,stroke:#10b981
    style Infrastructure fill:#dbeafe,stroke:#3b82f6
```

## 핵심 특징

### 1. **클라우드 네이티브**
- Azure Container Apps 완전 관리형
- 자동 스케일링 (0 → N instances)
- 글로벌 배포 가능

### 2. **멀티 유저 지원**
- JWT 기반 인증
- 사용자별 데이터 완전 격리
- Bcrypt 암호화

### 3. **Cross-Platform**
- Claude Desktop (MCP SSE)
- ChatGPT (MCP SSE)
- Web Dashboard (REST API)

### 4. **보안**
- HTTPS/TLS 암호화
- JWT 토큰 인증 (24시간)
- 사용자별 권한 검증
- CORS 정책

### 5. **확장성**
- Azure Cosmos DB 글로벌 분산
- Container Apps 자동 스케일
- 비동기 I/O (AsyncIO)
- MongoDB 인덱싱
