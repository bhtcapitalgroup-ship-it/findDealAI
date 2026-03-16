"""AI chat and conversation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.conversation import (
    ChannelType,
    Conversation,
    ConversationStatus,
    Message,
    SenderType,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationResponse,
    EscalationResponse,
    MessageResponse,
)

router = APIRouter(prefix="/ai", tags=["ai-chat"])


@router.post("/chat", response_model=ChatMessageResponse)
async def process_chat(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """Process a tenant chat message and return the AI-generated response.

    In production this calls the conversational AI pipeline which:
    1. Classifies intent (rent inquiry, maintenance, general)
    2. Generates a contextual response
    3. Takes actions (create maintenance request, etc.)
    4. Escalates to landlord if confidence is low
    """
    # Verify tenant belongs to landlord
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == payload.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    if tenant.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to chat for this tenant",
        )

    # Find or create conversation
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == payload.tenant_id,
            Conversation.landlord_id == current_user.id,
            Conversation.status == ConversationStatus.OPEN,
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if conversation is None:
        channel = ChannelType.WEB
        if payload.channel == "sms":
            channel = ChannelType.SMS
        elif payload.channel == "email":
            channel = ChannelType.EMAIL

        conversation = Conversation(
            tenant_id=payload.tenant_id,
            landlord_id=current_user.id,
            channel=channel,
        )
        db.add(conversation)
        await db.flush()

    # Store tenant message
    tenant_msg = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.TENANT,
        content=payload.message,
    )
    db.add(tenant_msg)

    # AI integration placeholder — will call chat_pipeline.process()
    # In production: intent classification -> response generation -> action dispatch
    intent = "maintenance_request"
    confidence = 0.88
    ai_reply = (
        f"Thank you, {tenant.first_name}. I understand you're reporting a "
        f"maintenance issue. I've logged this and will notify your property "
        f"manager. Is there anything else I can help with?"
    )
    actions_taken = ["maintenance_request_created"]
    escalated = confidence < 0.5

    # Store AI response
    ai_msg = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.AI,
        content=ai_reply,
        intent=intent,
        confidence=confidence,
    )
    db.add(ai_msg)

    # Escalate if low confidence
    if escalated:
        conversation.status = ConversationStatus.ESCALATED

    await db.flush()

    return ChatMessageResponse(
        conversation_id=conversation.id,
        reply=ai_reply,
        intent=intent,
        confidence=confidence,
        escalated=escalated,
        actions_taken=actions_taken,
    )


@router.get(
    "/conversations/{tenant_id}",
    response_model=list[ConversationResponse],
)
async def get_conversations(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    """Get conversation history for a tenant."""
    # Verify tenant belongs to landlord
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    if tenant.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view conversations for this tenant",
        )

    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.tenant_id == tenant_id,
            Conversation.landlord_id == current_user.id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/escalations", response_model=list[EscalationResponse])
async def list_escalations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EscalationResponse]:
    """List escalated conversations for the landlord."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.landlord_id == current_user.id,
            Conversation.status == ConversationStatus.ESCALATED,
        )
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    escalations = []
    for conv in conversations:
        # Get tenant name
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == conv.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        tenant_name = (
            f"{tenant.first_name} {tenant.last_name}" if tenant else "Unknown"
        )

        last_message = None
        if conv.messages:
            last_message = conv.messages[-1].content

        escalations.append(
            EscalationResponse(
                id=conv.id,
                tenant_id=conv.tenant_id,
                tenant_name=tenant_name,
                channel=conv.channel.value if hasattr(conv.channel, 'value') else str(conv.channel),
                status=conv.status.value if hasattr(conv.status, 'value') else str(conv.status),
                last_message=last_message,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )
    return escalations


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resolve an escalated conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == escalation_id,
            Conversation.status == ConversationStatus.ESCALATED,
        )
    )
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found",
        )
    if conversation.landlord_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to resolve this escalation",
        )

    conversation.status = ConversationStatus.CLOSED
    await db.flush()

    return {"status": "resolved", "conversation_id": str(conversation.id)}
