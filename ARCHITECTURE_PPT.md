# Pensieve MCP - PPT용 아키텍처 다이어그램

## 1. 시스템 개요 (High-Level Architecture)

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#6366f1','primaryTextColor':'#fff','primaryBorderColor':'#4f46e5','lineColor':'#64748b','secondaryColor':'#8b5cf6','tertiaryColor':'#ec4899'}}}%%
graph LR
    A[AI Assistants<br/>Claude/ChatGPT]
    B[MCP Protocol]
    C[Local Storage]
    D[Cloud API]
    E[MongoDB]

    A -->|stdio| B
    A -->|SSE| B
    B --> C
    B --> D
    D --> E

    style A fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style B fill:#6366f1,stroke:#4f46e5,color:#fff
    style C fill:#10b981,stroke:#059669,color:#fff
    style D fill:#f59e0b,stroke:#d97706,color:#fff
    style E fill:#ef4444,stroke:#dc2626,color:#fff
```

## 2. 아키텍처 비교 (Local vs Cloud)

```mermaid
%%{init: {'theme':'base'}}%%
graph TB
    subgraph Local["🏠 Local Mode"]
        L1[Claude Desktop]
        L2[MCP stdio]
        L3[Local Server]
        L4[JSON Files]

        L1 --> L2
        L2 --> L3
        L3 --> L4
    end

    subgraph Cloud["☁️ Cloud Mode"]
        C1[Claude Desktop]
        C2[MCP SSE]
        C3[FastAPI]
        C4[MongoDB]
        C5[Web Dashboard]

        C1 --> C2
        C2 --> C3
        C3 --> C4
        C5 --> C3
    end

    style Local fill:#e0f2fe,stroke:#0369a1
    style Cloud fill:#fef3c7,stroke:#d97706
    style L3 fill:#10b981,stroke:#059669,color:#fff
    style C3 fill:#f59e0b,stroke:#d97706,color:#fff
```

## 3. 데이터 흐름 (간단 버전)

```mermaid
%%{init: {'theme':'base'}}%%
sequenceDiagram
    actor User
    participant AI as AI Assistant
    participant MCP as MCP Client
    participant Server as Pensieve Server
    participant DB as Database

    User->>AI: 대화 내용
    AI->>MCP: save_conversation
    MCP->>Server: 저장 요청
    Server->>DB: 데이터 저장
    DB-->>Server: ✓
    Server-->>MCP: conversation_id
    MCP-->>AI: ✓
    AI-->>User: 저장 완료

    Note over User,DB: 나중에 다른 AI에서도 사용 가능
```

## 4. 핵심 기능 (Feature Overview)

```mermaid
%%{init: {'theme':'base'}}%%
mindmap
  root((Pensieve MCP))
    Multi User
      회원가입/로그인
      JWT 인증
      사용자별 격리
    Conversation
      저장
      불러오기
      검색
      이어쓰기
    Deployment
      Local Mode
      Cloud Mode
      Azure Container Apps
    Cross Platform
      Claude Desktop
      ChatGPT
      Web Dashboard
```

## 5. 기술 스택

```mermaid
%%{init: {'theme':'base'}}%%
graph TB
    subgraph Frontend["Frontend Layer"]
        F1[Web Dashboard]
        F2[HTML/CSS/JS]
    end

    subgraph Backend["Backend Layer"]
        B1[FastAPI]
        B2[MCP Server]
        B3[JWT Auth]
    end

    subgraph Data["Data Layer"]
        D1[MongoDB]
        D2[File System]
    end

    subgraph Protocol["Protocol Layer"]
        P1[MCP stdio]
        P2[MCP SSE]
        P3[REST API]
    end

    F1 --> P3
    P3 --> B1
    P1 --> B2
    P2 --> B1
    B1 --> B3
    B1 --> D1
    B2 --> D2

    style Frontend fill:#e0e7ff,stroke:#6366f1
    style Backend fill:#dbeafe,stroke:#3b82f6
    style Data fill:#dcfce7,stroke:#10b981
    style Protocol fill:#fef3c7,stroke:#f59e0b
```

## 6. 보안 구조

```mermaid
%%{init: {'theme':'base'}}%%
graph LR
    A[Client Request] --> B{Authentication}
    B -->|Valid Token| C[Authorization]
    B -->|Invalid| D[❌ 401 Error]
    C -->|Authorized| E[Data Access]
    C -->|Forbidden| F[❌ 403 Error]
    E --> G[User Data Only]

    H[Password] --> I[Bcrypt Hash]
    I --> J[JWT Token]
    J --> B

    style A fill:#e0e7ff,stroke:#6366f1
    style B fill:#fef3c7,stroke:#f59e0b
    style C fill:#dbeafe,stroke:#3b82f6
    style E fill:#dcfce7,stroke:#10b981
    style D fill:#fee2e2,stroke:#ef4444
    style F fill:#fee2e2,stroke:#ef4444
    style I fill:#fce7f3,stroke:#ec4899
    style J fill:#ddd6fe,stroke:#8b5cf6
```

## 7. 배포 아키텍처 (Azure)

```mermaid
%%{init: {'theme':'base'}}%%
graph TB
    Internet([Internet])

    subgraph Azure["☁️ Azure Cloud"]
        LB[Load Balancer<br/>HTTPS]

        subgraph ACA["Container Apps"]
            C1[FastAPI<br/>Container 1]
            C2[FastAPI<br/>Container 2]
        end

        DB[(Cosmos DB<br/>MongoDB API)]
    end

    Internet --> LB
    LB --> C1
    LB --> C2
    C1 --> DB
    C2 --> DB

    style Internet fill:#e0e7ff,stroke:#6366f1
    style LB fill:#dbeafe,stroke:#3b82f6
    style ACA fill:#fef3c7,stroke:#f59e0b
    style C1 fill:#f59e0b,stroke:#d97706,color:#fff
    style C2 fill:#f59e0b,stroke:#d97706,color:#fff
    style DB fill:#ef4444,stroke:#dc2626,color:#fff
```

## 8. MCP Tools 구조

```mermaid
%%{init: {'theme':'base'}}%%
graph TB
    MCP[MCP Server]

    T1[save_conversation<br/>💾]
    T2[load_conversation<br/>📖]
    T3[list_conversations<br/>📋]
    T4[search_conversations<br/>🔍]
    T5[append_to_conversation<br/>➕]

    A1[mcp_register<br/>👤]
    A2[mcp_login<br/>🔐]

    MCP --> T1
    MCP --> T2
    MCP --> T3
    MCP --> T4
    MCP --> T5
    MCP --> A1
    MCP --> A2

    style MCP fill:#6366f1,stroke:#4f46e5,color:#fff
    style T1 fill:#10b981,stroke:#059669,color:#fff
    style T2 fill:#10b981,stroke:#059669,color:#fff
    style T3 fill:#10b981,stroke:#059669,color:#fff
    style T4 fill:#10b981,stroke:#059669,color:#fff
    style T5 fill:#10b981,stroke:#059669,color:#fff
    style A1 fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style A2 fill:#8b5cf6,stroke:#7c3aed,color:#fff
```

## 9. 사용 시나리오

```mermaid
%%{init: {'theme':'base'}}%%
journey
    title Pensieve 사용자 여정
    section 준비
      회원가입: 5: User
      로그인: 5: User
      설정 완료: 4: User
    section Claude 사용
      대화 진행: 5: User, Claude
      대화 저장: 5: User, Claude
    section ChatGPT 사용
      대화 불러오기: 5: User, ChatGPT
      이어서 대화: 5: User, ChatGPT
      검색: 4: User, ChatGPT
    section 관리
      웹 대시보드: 4: User
      대화 관리: 4: User
```

## 10. 시스템 구성요소

```mermaid
%%{init: {'theme':'base'}}%%
flowchart LR
    subgraph Clients["클라이언트"]
        C1[Claude Desktop]
        C2[ChatGPT]
        C3[Web Browser]
    end

    subgraph MCP["MCP Layer"]
        M1[stdio Protocol]
        M2[SSE Protocol]
    end

    subgraph Servers["서버"]
        S1[Local MCP Server]
        S2[Cloud API Server]
    end

    subgraph Storage["저장소"]
        ST1[File System]
        ST2[MongoDB]
    end

    C1 --> M1
    C2 --> M2
    C3 --> S2

    M1 --> S1
    M2 --> S2

    S1 --> ST1
    S2 --> ST2

    style Clients fill:#e0e7ff,stroke:#6366f1
    style MCP fill:#dbeafe,stroke:#3b82f6
    style Servers fill:#fef3c7,stroke:#f59e0b
    style Storage fill:#dcfce7,stroke:#10b981
```

---

## 🎨 PPT 작성 팁

### 추천 다이어그램 순서:
1. **슬라이드 1**: 시스템 개요 (#1)
2. **슬라이드 2**: Local vs Cloud 비교 (#2)
3. **슬라이드 3**: 데이터 흐름 (#3)
4. **슬라이드 4**: 핵심 기능 (#4)
5. **슬라이드 5**: 기술 스택 (#5)
6. **슬라이드 6**: Azure 배포 (#7)

### Mermaid를 이미지로 변환하는 방법:

#### 방법 1: Mermaid Live Editor
1. https://mermaid.live 접속
2. 다이어그램 코드 복사/붙여넣기
3. PNG/SVG로 다운로드

#### 방법 2: VS Code Extension
1. "Markdown Preview Mermaid Support" 설치
2. 미리보기에서 우클릭 → 이미지로 저장

#### 방법 3: CLI 도구
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.md -o output.png
```

### 색상 팔레트:
- 🟣 Purple: #8b5cf6 (AI/Client)
- 🔵 Blue: #6366f1 (MCP Protocol)
- 🟢 Green: #10b981 (Local/Storage)
- 🟡 Orange: #f59e0b (API/Cloud)
- 🔴 Red: #ef4444 (Database)
