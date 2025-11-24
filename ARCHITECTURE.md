# Pensieve MCP Architecture

## 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph Clients["AI Clients"]
        Claude[Claude Desktop]
        ChatGPT[ChatGPT]
    end

    subgraph MCP["MCP Layer"]
        MCPClient[MCP Client]
    end

    subgraph LocalMode["Local Mode"]
        LocalServer[Local MCP Server]
        LocalFS[File System]
    end

    subgraph CloudMode["Cloud Mode"]
        APIServer[FastAPI Server]
        RestAPI[REST API]
        MCPSSE[MCP SSE]
        MongoDB[(MongoDB)]
        Dashboard[Web Dashboard]
    end

    Claude --> MCPClient
    ChatGPT --> MCPClient

    MCPClient -->|stdio| LocalServer
    MCPClient -->|SSE| MCPSSE

    LocalServer --> LocalFS

    MCPSSE --> APIServer
    RestAPI --> APIServer
    Dashboard --> RestAPI

    APIServer --> MongoDB

    style Claude fill:#9b59b6
    style ChatGPT fill:#3498db
    style LocalServer fill:#2ecc71
    style APIServer fill:#e74c3c
    style MongoDB fill:#f39c12
```

## 데이터 흐름

### 1. Local Mode 데이터 흐름

```mermaid
sequenceDiagram
    participant User
    participant Claude
    participant MCP
    participant Server
    participant FS

    User->>Claude: 대화 저장 요청
    Claude->>MCP: save_conversation
    MCP->>Server: stdio 통신
    Server->>FS: JSON 저장
    FS-->>Server: 완료
    Server-->>MCP: conversation_id
    MCP-->>Claude: 결과
    Claude-->>User: 완료 메시지
```

### 2. Cloud Mode 데이터 흐름 (인증)

```mermaid
sequenceDiagram
    participant User
    participant Claude
    participant MCP
    participant API
    participant DB

    User->>Claude: 로그인
    Claude->>MCP: mcp_login
    MCP->>API: SSE 요청
    API->>DB: 사용자 확인
    DB-->>API: 정보
    API->>API: JWT 생성
    API-->>MCP: 토큰
    MCP->>MCP: 토큰 저장
    MCP-->>Claude: 성공
    Claude-->>User: 완료
```

### 3. Cloud Mode 데이터 흐름 (대화 저장)

```mermaid
sequenceDiagram
    participant User
    participant Claude
    participant MCP
    participant API
    participant DB

    User->>Claude: 대화 저장
    Claude->>MCP: save_conversation
    MCP->>API: SSE + token
    API->>API: JWT 검증
    API->>DB: 문서 삽입
    DB-->>API: 완료
    API-->>MCP: conversation_id
    MCP-->>Claude: 결과
    Claude-->>User: 완료
```

## 컴포넌트 상세 구조

### MCP Server (Local)

```mermaid
graph TB
    Tools[MCP Tools]
    Cache[Cache]
    Storage[File Storage]

    T1[save_conversation]
    T2[load_conversation]
    T3[list_conversations]
    T4[search_conversations]
    T5[append_to_conversation]

    Tools --> Cache
    Tools --> Storage
    Cache --> Storage

    Tools --> T1
    Tools --> T2
    Tools --> T3
    Tools --> T4
    Tools --> T5
```

### API Server (Cloud)

```mermaid
graph TB
    Auth[JWT Auth]
    BCrypt[Password Hash]
    RestAPI[REST API]
    MCPAPI[MCP SSE API]
    ConvLogic[Conversation]
    UserLogic[User Mgmt]
    MongoDB[(MongoDB)]

    Auth --> RestAPI
    Auth --> MCPAPI
    BCrypt --> Auth

    RestAPI --> ConvLogic
    RestAPI --> UserLogic
    MCPAPI --> ConvLogic
    MCPAPI --> UserLogic

    ConvLogic --> MongoDB
    UserLogic --> MongoDB
```

### 데이터 모델

```mermaid
erDiagram
    USER ||--o{ CONVERSATION : owns

    USER {
        string _id PK
        string email UK
        string hashed_password
        datetime created_at
    }

    CONVERSATION {
        string _id PK
        string user_id FK
        array messages
        object metadata
        datetime created_at
        datetime updated_at
    }

    MESSAGE {
        string role
        string content
    }

    CONVERSATION ||--|{ MESSAGE : contains
```

## 배포 아키텍처 (Azure)

```mermaid
graph TB
    Users[Users]
    Ingress[HTTPS Ingress]
    Container[Container Apps]
    CosmosDB[(Cosmos DB)]
    UsersCol[users collection]
    ConvsCol[conversations collection]

    Users --> Ingress
    Ingress --> Container
    Container --> CosmosDB
    CosmosDB --> UsersCol
    CosmosDB --> ConvsCol

    style Container fill:#0078d4
    style CosmosDB fill:#f39c12
```

## 통신 프로토콜

### 1. MCP stdio Protocol (Local)

```mermaid
sequenceDiagram
    participant Claude
    participant MCP as MCP Client
    participant Server as MCP Server

    Note over Claude,Server: 초기화
    MCP->>Server: initialize
    Server-->>MCP: server_info

    Note over Claude,Server: 도구 목록 요청
    Claude->>MCP: 사용 가능한 도구?
    MCP->>Server: tools/list
    Server-->>MCP: [tools]
    MCP-->>Claude: 도구 목록 표시

    Note over Claude,Server: 도구 실행
    Claude->>MCP: 도구 실행 요청
    MCP->>Server: tools/call
    Server->>Server: 비즈니스 로직 실행
    Server-->>MCP: result
    MCP-->>Claude: 결과 표시
```

### 2. MCP SSE Protocol (Cloud)

```mermaid
sequenceDiagram
    participant Claude
    participant MCP as MCP SSE Client
    participant API as FastAPI /sse

    Note over Claude,API: SSE 연결 설정
    MCP->>API: GET /sse (SSE handshake)
    API-->>MCP: SSE connection established

    Note over Claude,API: 도구 목록 요청
    Claude->>MCP: 사용 가능한 도구?
    MCP->>API: SSE message: tools/list
    API-->>MCP: SSE event: [tools]
    MCP-->>Claude: 도구 목록 표시

    Note over Claude,API: 도구 실행
    Claude->>MCP: 도구 실행 요청
    MCP->>API: SSE message: tools/call
    API->>API: JWT 인증 및 실행
    API-->>MCP: SSE event: result
    MCP-->>Claude: 결과 표시
```

## 보안 아키텍처

```mermaid
graph TB
    JWT[JWT Token]
    Bcrypt[Bcrypt Hash]
    TokenValidation[Token Validation]
    UserIsolation[User Isolation]
    HTTPS[HTTPS/TLS]
    EnvVars[Env Variables]

    Bcrypt --> JWT
    JWT --> TokenValidation
    TokenValidation --> UserIsolation
    UserIsolation --> HTTPS
    JWT --> EnvVars
```

## 주요 특징

### 1. **Dual Mode Architecture**
- **Local Mode**: 파일 시스템 기반, 빠른 응답, 단일 사용자
- **Cloud Mode**: MongoDB 기반, 멀티 유저, 어디서나 접근

### 2. **MCP Protocol Support**
- **stdio**: Local mode, Claude Desktop 네이티브 통합
- **SSE**: Cloud mode, HTTP 기반 실시간 통신

### 3. **Security**
- JWT 토큰 기반 인증
- Bcrypt 비밀번호 해싱
- 사용자별 데이터 격리

### 4. **Scalability**
- Azure Container Apps 자동 스케일링
- Cosmos DB 글로벌 분산
- 캐싱 메커니즘 (Local mode)

### 5. **User Experience**
- Web Dashboard for conversation management
- Setup guides for easy configuration
- RESTful API for external integrations
