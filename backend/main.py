"""FastAPI application for the M8 Solutions business analytics chatbot.

The service orchestrates natural language interpretation, clarification of
missing parameters, safe SQL generation, execution against Supabase, and
logging of every interaction for traceability.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


class ChatQuestion(BaseModel):
    question: str = Field(..., description="User's natural language question")
    user_id: Optional[str] = Field(None, description="Supabase Auth user ID")


class ChartPayload(BaseModel):
    type: str
    x: List[Any]
    y: List[Any]


class ChatbotResponse(BaseModel):
    answer: str
    chart: Optional[ChartPayload] = None
    raw_data: Optional[List[Dict[str, Any]]] = None


class ChatLog(BaseModel):
    id: Optional[int]
    user_id: Optional[str]
    question: str
    refined_question: Optional[str]
    generated_sql: Optional[str]
    response_summary: Optional[str]
    created_at: Optional[datetime]


class SupabaseService:
    """Supabase wrapper that centralizes auth and RPC usage."""

    def __init__(self, url: str, key: str) -> None:
        if not url or not key:
            raise RuntimeError("Supabase credentials are not configured")
        self.client: Client = create_client(url, key)

    async def execute_safe_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Invoke a secure RPC that runs parameterized SQL on the server."""
        response = self.client.rpc("execute_sql_safe", {"sql": sql}).execute()
        if response.error:
            raise HTTPException(status_code=500, detail=response.error.message)
        return response.data  # type: ignore[return-value]

    async def save_chat_log(self, log: ChatLog) -> None:
        payload = log.model_dump(exclude_none=True)
        result = self.client.table("chat_logs").insert(payload).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=result.error.message)

    async def list_history(self, user_id: str) -> List[ChatLog]:
        response = (
            self.client.table("chat_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        if response.error:
            raise HTTPException(status_code=500, detail=response.error.message)
        return [ChatLog(**item) for item in response.data]


def get_supabase_service() -> SupabaseService:
    return SupabaseService(SUPABASE_URL, SUPABASE_KEY)


def build_analysis_prompt(question: str) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a business analytics assistant for M8 Solutions. "
                "Identify the intent, main entity, filters, and missing information "
                "in this question. Return JSON with fields: intent, entities, "
                "missing_information."
            ),
        },
        {"role": "user", "content": question},
    ]


def build_sql_prompt(question: str) -> List[Dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Generate safe SQL for PostgreSQL (Supabase) to answer this "
                "question. Use only these tables: forecast_error_metrics, "
                "sales_summary, inventory_snapshots. Always use LIMIT 100. "
                "Return only the SQL code without markdown fences."
            ),
        },
        {"role": "user", "content": question},
    ]


async def call_openai(messages: List[Dict[str, str]]) -> str:
    """Call the OpenAI chat completions endpoint using httpx for async IO."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions", json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def parse_sql_from_response(response_text: str) -> str:
    cleaned = response_text.strip()
    if cleaned.startswith("```sql"):
        cleaned = cleaned.removeprefix("```sql").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def build_chart_payload(rows: List[Dict[str, Any]]) -> Optional[ChartPayload]:
    if not rows:
        return None
    first_row = rows[0]
    if len(first_row.keys()) < 2:
        return None
    keys = list(first_row.keys())
    x_key, y_key = keys[0], keys[1]
    return ChartPayload(
        type="bar",
        x=[row.get(x_key) for row in rows],
        y=[row.get(y_key) for row in rows],
    )


app = FastAPI(title="M8 Solutions Chatbot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chatbot/query", response_model=ChatbotResponse)
async def chatbot_query(
    payload: ChatQuestion, supabase: SupabaseService = Depends(get_supabase_service)
) -> ChatbotResponse:
    """Primary entry point for NL questions."""

    intent_analysis = await call_openai(build_analysis_prompt(payload.question))
    sql_raw = await call_openai(build_sql_prompt(payload.question))
    generated_sql = parse_sql_from_response(sql_raw)

    rows = await supabase.execute_safe_sql(generated_sql)
    chart = build_chart_payload(rows)
    answer = (
        f"Encontré {len(rows)} registros relevantes. "
        "Consulta refinada: "
        f"{intent_analysis}"
    )

    log = ChatLog(
        user_id=payload.user_id,
        question=payload.question,
        refined_question=intent_analysis,
        generated_sql=generated_sql,
        response_summary=answer,
    )
    await supabase.save_chat_log(log)

    return ChatbotResponse(answer=answer, chart=chart, raw_data=rows)


@app.get("/chatbot/history", response_model=List[ChatLog])
async def chatbot_history(
    user_id: str, supabase: SupabaseService = Depends(get_supabase_service)
) -> List[ChatLog]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return await supabase.list_history(user_id)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-App-Name"] = "M8 Solutions Chatbot"
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
