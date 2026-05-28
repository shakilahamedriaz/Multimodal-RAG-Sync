import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import KnowledgeBase, Conversation, Message
from app.schemas import (
    ChatMessageIn,
    ChatMessageOut,
    ConversationOut,
    ConversationListItem,
    ConversationRenameIn,
    SourceCitation,
)
from app.services.query_service import chat_stream, chat_sync

router = APIRouter(prefix="/kb", tags=["chat"])

_DEFAULT_OWNER = "default"  # matches existing auth pattern


def _owner_from_request() -> str:
    return _DEFAULT_OWNER


async def _get_kb(kb_id: uuid.UUID, db: AsyncSession) -> KnowledgeBase:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


async def _get_conv(conv_id: uuid.UUID, kb_id: uuid.UUID, db: AsyncSession) -> Conversation:
    conv = await db.get(Conversation, conv_id)
    if not conv or conv.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _msg_to_schema(msg: Message) -> ChatMessageOut:
    sources = None
    if msg.sources:
        try:
            sources = [SourceCitation(**s) for s in msg.sources]
        except Exception:
            sources = None
    return ChatMessageOut(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        sources=sources,
        has_answer=msg.has_answer,
        created_at=msg.created_at,
    )


# ── Create conversation ───────────────────────────────────────────────────────

@router.post("/{kb_id}/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _get_kb(kb_id, db)
    conv = Conversation(kb_id=kb_id, owner_id=_DEFAULT_OWNER)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationOut(
        id=conv.id,
        kb_id=conv.kb_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )


# ── List conversations ────────────────────────────────────────────────────────

@router.get("/{kb_id}/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    kb_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _get_kb(kb_id, db)
    result = await db.execute(
        select(
            Conversation,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.kb_id == kb_id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )
    rows = result.all()
    return [
        ConversationListItem(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count,
        )
        for conv, count in rows
    ]


# ── Get conversation with messages ────────────────────────────────────────────

@router.get("/{kb_id}/conversations/{conv_id}", response_model=ConversationOut)
async def get_conversation(
    kb_id: uuid.UUID,
    conv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_conv(conv_id, kb_id, db)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return ConversationOut(
        id=conv.id,
        kb_id=conv.kb_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_msg_to_schema(m) for m in messages],
    )


# ── Rename conversation ───────────────────────────────────────────────────────

@router.patch("/{kb_id}/conversations/{conv_id}", response_model=ConversationOut)
async def rename_conversation(
    kb_id: uuid.UUID,
    conv_id: uuid.UUID,
    payload: ConversationRenameIn,
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_conv(conv_id, kb_id, db)
    conv.title = payload.title[:255]
    await db.commit()
    await db.refresh(conv)
    return ConversationOut(
        id=conv.id,
        kb_id=conv.kb_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )


# ── Delete conversation ───────────────────────────────────────────────────────

@router.delete("/{kb_id}/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    kb_id: uuid.UUID,
    conv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_conv(conv_id, kb_id, db)
    await db.delete(conv)
    await db.commit()


# ── Send message ──────────────────────────────────────────────────────────────

@router.post(
    "/{kb_id}/conversations/{conv_id}/messages",
    responses={
        200: {"description": "JSON response (stream=false)"},
        206: {"description": "SSE stream (stream=true)", "content": {"text/event-stream": {}}},
    },
)
async def send_message(
    kb_id: uuid.UUID,
    conv_id: uuid.UUID,
    payload: ChatMessageIn,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to a conversation and get an AI response.

    **Streaming** (`stream=true`): Returns `text/event-stream` SSE.
    Events: `token`, `sources`, `done`, `error`.

    **Non-streaming** (`stream=false`): Returns JSON with the full response.
    """
    kb = await _get_kb(kb_id, db)
    conv = await _get_conv(conv_id, kb_id, db)

    # Auto-generate title from first user message
    if not conv.title:
        conv.title = payload.content[:60].strip()
        await db.commit()

    if payload.stream:
        async def event_generator():
            try:
                async for event in chat_stream(
                    kb=kb,
                    conversation_id=conv_id,
                    user_message=payload.content,
                    db=db,
                ):
                    yield event
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        return StreamingResponse(
            event_generator(),
            status_code=206,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = await chat_sync(
        kb=kb,
        conversation_id=conv_id,
        user_message=payload.content,
        db=db,
    )
    return result
