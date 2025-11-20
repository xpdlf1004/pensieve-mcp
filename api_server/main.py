from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import jwt
import os
from uuid import uuid4
import motor.motor_asyncio
from passlib.context import CryptContext
import json

# MCP 임포트
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from sse_starlette import EventSourceResponse

app = FastAPI(title="Pensieve API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "pensieve"

# MongoDB 연결
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
users_collection = db.users
conversations_collection = db.conversations

# 보안
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 모델
class UserCreate(BaseModel):
    email: EmailStr  # 이메일 형식 검증
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('비밀번호는 최소 6자 이상이어야 합니다')
        if len(v) > 100:
            raise ValueError('비밀번호는 100자 이하여야 합니다')
        return v

class UserLogin(BaseModel):
    email: str
    password: str

class Message(BaseModel):
    role: str
    content: str

class ConversationCreate(BaseModel):
    messages: List[Message]
    metadata: Optional[Dict[str, Any]] = None

class ConversationUpdate(BaseModel):
    messages: List[Message]

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# 헬퍼 함수
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user = await users_collection.find_one({"email": email})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

# 인증 엔드포인트
@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    # 이메일 중복 확인
    if await users_collection.find_one({"email": user.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 사용자 생성
    hashed_password = pwd_context.hash(user.password)
    user_doc = {
        "_id": str(uuid4()),
        "email": user.email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    await users_collection.insert_one(user_doc)

    # 토큰 생성
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token}

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    # 사용자 확인
    db_user = await users_collection.find_one({"email": user.email})
    if not db_user or not pwd_context.verify(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # 토큰 생성
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token}

# 대화 엔드포인트
@app.post("/conversations")
async def create_conversation(
    conversation: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    conversation_doc = {
        "_id": str(uuid4()),
        "user_id": current_user["_id"],
        "messages": [msg.dict() for msg in conversation.messages],
        "metadata": conversation.metadata or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await conversations_collection.insert_one(conversation_doc)
    return {"id": conversation_doc["_id"], "message": "Conversation created successfully"}

@app.get("/conversations")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    cursor = conversations_collection.find(
        {"user_id": current_user["_id"]}
    ).skip(offset).limit(limit)
    
    conversations = []
    async for conv in cursor:
        conversations.append({
            "id": conv["_id"],
            "metadata": conv.get("metadata", {}),
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
            "message_count": len(conv.get("messages", []))
        })
    
    return conversations

@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    conversation = await conversations_collection.find_one({
        "_id": conversation_id,
        "user_id": current_user["_id"]
    })
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return conversation

@app.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    update: ConversationUpdate,
    current_user: dict = Depends(get_current_user)
):
    result = await conversations_collection.update_one(
        {"_id": conversation_id, "user_id": current_user["_id"]},
        {
            "$set": {
                "messages": [msg.dict() for msg in update.messages],
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"message": "Conversation updated successfully"}

@app.post("/conversations/{conversation_id}/messages")
async def append_messages(
    conversation_id: str,
    messages: List[Message],
    current_user: dict = Depends(get_current_user)
):
    result = await conversations_collection.update_one(
        {"_id": conversation_id, "user_id": current_user["_id"]},
        {
            "$push": {"messages": {"$each": [msg.dict() for msg in messages]}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"message": f"Added {len(messages)} messages to conversation"}

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    result = await conversations_collection.delete_one({
        "_id": conversation_id,
        "user_id": current_user["_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {"message": "Conversation deleted successfully"}

@app.get("/conversations/search")
async def search_conversations(
    query: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    # MongoDB 텍스트 검색 사용
    cursor = conversations_collection.find(
        {
            "user_id": current_user["_id"],
            "$text": {"$search": query}
        }
    ).limit(limit)
    
    results = []
    async for conv in cursor:
        results.append({
            "id": conv["_id"],
            "metadata": conv.get("metadata", {}),
            "created_at": conv["created_at"],
            "message_count": len(conv.get("messages", []))
        })
    
    return results

# 웹 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """메인 대시보드 페이지"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """대화 관리 대시보드"""
    with open("static/dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/conversation/{conversation_id}", response_class=HTMLResponse)
async def conversation_detail(conversation_id: str):
    """대화 상세 페이지"""
    with open("static/conversation.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/guide", response_class=HTMLResponse)
async def guide_page():
    """사용 가이드 페이지"""
    with open("static/guide.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """MCP 설정 가이드 페이지"""
    with open("static/setup.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# API 라우트 (프론트엔드에서 사용)
@app.get("/api/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """현재 로그인한 사용자 정보"""
    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "created_at": current_user["created_at"]
    }

@app.post("/api/login")
async def api_login(user: UserLogin):
    """로그인 API"""
    return await login(user)

@app.post("/api/register")
async def api_register(user: UserCreate):
    """회원가입 API"""
    return await register(user)

@app.get("/api/conversations")
async def api_get_conversations(
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """사용자의 대화 목록 조회"""
    try:
        cursor = conversations_collection.find(
            {"user_id": current_user["_id"]}
        ).sort("created_at", -1).limit(limit).skip(skip)

        conversations = []
        async for conv in cursor:
            conversations.append({
                "id": str(conv["_id"]),
                "messages": conv.get("messages", []),
                "metadata": conv.get("metadata", {}),
                "created_at": conv.get("created_at"),  # .get() 사용으로 안전하게
                "updated_at": conv.get("updated_at")   # .get() 사용으로 안전하게
            })

        return conversations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/conversations/{conversation_id}")
async def api_get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """특정 대화 상세 조회"""
    return await get_conversation(conversation_id, current_user)

@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """대화 삭제"""
    return await delete_conversation(conversation_id, current_user)

# 기존 API 호환성을 위한 라우트
@app.get("/health")
async def health_check():
    return {"message": "Pensieve API", "version": "1.0.0", "status": "healthy"}

# ==================== MCP SSE 서버 ====================
# MCP 서버 인스턴스
mcp_server = Server("pensieve-mcp")

# MCP 세션별 토큰 저장
mcp_api_tokens: Dict[str, str] = {}

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """사용 가능한 MCP 도구 목록을 반환합니다"""
    return [
        Tool(
            name="register",
            description="새 계정을 등록합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소"
                    },
                    "password": {
                        "type": "string",
                        "description": "비밀번호 (최소 6자, 최대 72바이트)"
                    }
                },
                "required": ["email", "password"]
            }
        ),
        Tool(
            name="login",
            description="이메일과 비밀번호로 로그인합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소"
                    },
                    "password": {
                        "type": "string",
                        "description": "비밀번호"
                    }
                },
                "required": ["email", "password"]
            }
        ),
        Tool(
            name="set_api_token",
            description="API 토큰을 수동으로 설정합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소"
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT 액세스 토큰"
                    }
                },
                "required": ["email", "token"]
            }
        ),
        Tool(
            name="save_conversation",
            description="대화 내역을 저장합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소 (인증용)"
                    },
                    "messages": {
                        "type": "array",
                        "description": "저장할 메시지 목록",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant", "system"],
                                    "description": "메시지 역할"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "메시지 내용"
                                }
                            },
                            "required": ["role", "content"]
                        }
                    },
                    "metadata": {
                        "type": "object",
                        "description": "대화에 대한 추가 메타데이터 (제목, 태그 등)"
                    }
                },
                "required": ["email", "messages"]
            }
        ),
        Tool(
            name="load_conversation",
            description="저장된 대화를 불러옵니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소 (인증용)"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "불러올 대화의 ID"
                    }
                },
                "required": ["email", "conversation_id"]
            }
        ),
        Tool(
            name="list_conversations",
            description="저장된 대화 목록을 조회합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소 (인증용)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "조회할 대화 개수 (기본값: 50)",
                        "default": 50
                    },
                    "offset": {
                        "type": "integer",
                        "description": "건너뛸 대화 개수 (페이징용, 기본값: 0)",
                        "default": 0
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="search_conversations",
            description="대화 내용을 검색합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소 (인증용)"
                    },
                    "query": {
                        "type": "string",
                        "description": "검색할 키워드"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "검색 결과 개수 (기본값: 20)",
                        "default": 20
                    }
                },
                "required": ["email", "query"]
            }
        ),
        Tool(
            name="append_to_conversation",
            description="기존 대화에 메시지를 추가합니다",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "사용자 이메일 주소 (인증용)"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "메시지를 추가할 대화의 ID"
                    },
                    "messages": {
                        "type": "array",
                        "description": "추가할 메시지 목록",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant", "system"],
                                    "description": "메시지 역할"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "메시지 내용"
                                }
                            },
                            "required": ["role", "content"]
                        }
                    }
                },
                "required": ["email", "conversation_id", "messages"]
            }
        )
    ]

async def get_mcp_user(email: str):
    """MCP 토큰으로 사용자 인증"""
    token = mcp_api_tokens.get(email)
    if not token:
        raise HTTPException(status_code=401, detail="먼저 로그인해주세요")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_email = payload.get("sub")
        user = await users_collection.find_one({"email": user_email})
        if not user:
            raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
        return user
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """MCP 도구 실행"""
    try:
        if name == "set_api_token":
            email = arguments["email"]
            token = arguments["token"]
            mcp_api_tokens[email] = token
            return [TextContent(
                type="text",
                text="API 토큰이 설정되었습니다. 이제 대화를 저장하고 불러올 수 있습니다."
            )]

        elif name == "login":
            email = arguments["email"]
            password = arguments["password"]

            db_user = await users_collection.find_one({"email": email})
            if not db_user or not pwd_context.verify(password, db_user["hashed_password"]):
                return [TextContent(
                    type="text",
                    text="로그인 실패: 이메일 또는 비밀번호가 잘못되었습니다"
                )]

            token = create_access_token(data={"sub": email})
            mcp_api_tokens[email] = token

            return [TextContent(
                type="text",
                text=f"로그인 성공! 토큰이 자동으로 설정되었습니다."
            )]

        elif name == "register":
            email = arguments["email"]
            password = arguments["password"]

            user = await users_collection.find_one({"email": email})
            if user:
                return [TextContent(
                    type="text",
                    text="이미 등록된 이메일입니다"
                )]

            if len(password) < 6:
                return [TextContent(
                    type="text",
                    text="비밀번호는 최소 6자 이상이어야 합니다"
                )]
            if len(password.encode('utf-8')) > 72:
                return [TextContent(
                    type="text",
                    text="비밀번호는 72바이트 이하여야 합니다"
                )]

            hashed_password = pwd_context.hash(password)
            user_doc = {
                "_id": str(uuid4()),
                "email": email,
                "hashed_password": hashed_password,
                "created_at": datetime.utcnow()
            }
            await users_collection.insert_one(user_doc)

            token = create_access_token(data={"sub": email})
            mcp_api_tokens[email] = token

            return [TextContent(
                type="text",
                text=f"회원가입 성공! 토큰이 자동으로 설정되었습니다."
            )]

        # 나머지 도구들은 인증이 필요
        email = arguments.get("email")
        if not email or email not in mcp_api_tokens:
            return [TextContent(
                type="text",
                text="먼저 로그인하거나 API 토큰을 설정해주세요. login 또는 set_api_token 도구를 사용하세요."
            )]

        if name == "save_conversation":
            user = await get_mcp_user(email)
            messages = arguments["messages"]
            metadata = arguments.get("metadata", {})

            conversation_doc = {
                "_id": str(uuid4()),
                "user_id": user["_id"],
                "messages": messages,
                "metadata": metadata,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await conversations_collection.insert_one(conversation_doc)
            return [TextContent(
                type="text",
                text=f"대화가 저장되었습니다. ID: {conversation_doc['_id']}"
            )]

        elif name == "load_conversation":
            user = await get_mcp_user(email)
            conversation_id = arguments["conversation_id"]

            conv = await conversations_collection.find_one({
                "_id": conversation_id,
                "user_id": user["_id"]
            })

            if not conv:
                return [TextContent(
                    type="text",
                    text=f"대화를 찾을 수 없습니다: {conversation_id}"
                )]

            return [TextContent(
                type="text",
                text=json.dumps(conv, default=str, ensure_ascii=False, indent=2)
            )]

        elif name == "list_conversations":
            user = await get_mcp_user(email)
            limit = arguments.get("limit", 50)
            offset = arguments.get("offset", 0)

            cursor = conversations_collection.find({"user_id": user["_id"]}).sort("created_at", -1).limit(limit).skip(offset)
            convs = []
            async for conv in cursor:
                convs.append({
                    "id": conv["_id"],
                    "metadata": conv.get("metadata", {}),
                    "created_at": str(conv["created_at"]),
                    "message_count": len(conv.get("messages", []))
                })

            return [TextContent(
                type="text",
                text=json.dumps(convs, ensure_ascii=False, indent=2)
            )]

        elif name == "search_conversations":
            user = await get_mcp_user(email)
            query = arguments["query"]
            limit = arguments.get("limit", 20)

            cursor = conversations_collection.find({
                "user_id": user["_id"],
                "messages.content": {"$regex": query, "$options": "i"}
            }).limit(limit)

            results = []
            async for conv in cursor:
                matched_message = None
                for msg in conv.get("messages", []):
                    if query.lower() in msg.get("content", "").lower():
                        matched_message = msg
                        break

                results.append({
                    "id": conv["_id"],
                    "metadata": conv.get("metadata", {}),
                    "created_at": str(conv["created_at"]),
                    "matched_message": matched_message,
                    "message_count": len(conv.get("messages", []))
                })

            return [TextContent(
                type="text",
                text=json.dumps(results, ensure_ascii=False, indent=2)
            )]

        elif name == "append_to_conversation":
            user = await get_mcp_user(email)
            conversation_id = arguments["conversation_id"]
            messages = arguments["messages"]

            conv = await conversations_collection.find_one({
                "_id": conversation_id,
                "user_id": user["_id"]
            })

            if not conv:
                return [TextContent(
                    type="text",
                    text=f"대화를 찾을 수 없습니다: {conversation_id}"
                )]

            result = await conversations_collection.update_one(
                {"_id": conversation_id, "user_id": user["_id"]},
                {
                    "$push": {"messages": {"$each": messages}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            if result.modified_count > 0:
                return [TextContent(
                    type="text",
                    text=f"대화에 {len(messages)}개의 메시지가 추가되었습니다."
                )]
            else:
                return [TextContent(
                    type="text",
                    text="메시지 추가에 실패했습니다."
                )]

        else:
            return [TextContent(
                type="text",
                text=f"알 수 없는 도구: {name}"
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"오류 발생: {str(e)}"
        )]

# MCP SSE 엔드포인트
@app.get("/sse")
@app.post("/sse")
async def handle_sse(request: Request):
    """MCP SSE 엔드포인트"""
    async def event_generator():
        transport = SseServerTransport("/messages")

        async with transport.connect_sse(
            request.scope,
            request.receive,
            request._send
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )

    return EventSourceResponse(event_generator())

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)