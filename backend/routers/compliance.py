"""
AI CFO — GDPR/CCPA Compliance Router
Data export, deletion, consent management, and retention policies.

Implements GDPR Article 20 (Right to Data Portability) and Article 17 (Right to Erasure),
plus CCPA compliance for data export and deletion requests.
"""
import json
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from auth import get_current_user
from config import settings
from dependencies import get_rls_db
from models import (
    User, Workspace, Transaction, Budget, Goal, Alert, ChatSession, 
    ChatMessage, AuditLog, FileUpload, UserConsent, DataExport, 
    DataDeletion, RetentionPolicy, ConsentStatus, DataExportStatus, 
    DataDeletionStatus, UserRole
)
from schemas import (
    DataExportRequest, DataExportResponse, DataDeletionRequest, 
    DataDeletionResponse, ConsentRequest, ConsentResponse, 
    ConsentWithdrawalRequest, RetentionPolicyResponse, 
    RetentionPolicyInfo, ComplianceStatusResponse
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# GDPR ARTICLE 20 — RIGHT TO DATA PORTABILITY
# ═══════════════════════════════════════════════════════════════════

@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    request: DataExportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """
    GDPR Article 20: Request export of all user data in portable format.
    
    Returns all personal data associated with the user in JSON or CSV format.
    Export files are available for 30 days and then automatically deleted.
    """
    if not settings.DATA_EXPORT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data export service is currently disabled"
        )
    
    # Check for existing pending/processing exports
    existing_export = await db.execute(
        select(DataExport)
        .where(
            and_(
                DataExport.user_id == user.id,
                DataExport.status.in_([DataExportStatus.requested, DataExportStatus.processing])
            )
        )
    )
    if existing_export.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A data export is already in progress. Please wait for it to complete."
        )
    
    # Create export record
    export_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    export_record = DataExport(
        id=export_id,
        workspace_id=user.workspace_id,
        user_id=user.id,
        status=DataExportStatus.processing,
        format=request.format,
        include_metadata=request.include_metadata,
        expires_at=expires_at
    )
    
    db.add(export_record)
    await db.commit()
    
    try:
        # Collect all user data
        user_data = await _collect_user_data(user, db, request.include_metadata)
        
        # Generate export file
        file_path, file_size = await _generate_export_file(
            export_id, user_data, request.format
        )
        
        # Update export record
        export_record.status = DataExportStatus.completed
        export_record.file_path = file_path
        export_record.file_size_bytes = file_size
        export_record.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return DataExportResponse(
            export_id=export_id,
            status="completed",
            format=request.format,
            file_size_bytes=file_size,
            created_at=export_record.created_at,
            expires_at=expires_at
        )
        
    except Exception as e:
        # Update export record with error
        export_record.status = DataExportStatus.failed
        export_record.error_message = str(e)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate data export: {str(e)}"
        )


@router.get("/export/{export_id}")
async def get_export_status(
    export_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Get the status of a data export request."""
    export_record = await db.execute(
        select(DataExport)
        .where(
            and_(
                DataExport.id == export_id,
                DataExport.user_id == user.id
            )
        )
    )
    export_record = export_record.scalar_one_or_none()
    
    if not export_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )
    
    return DataExportResponse(
        export_id=export_record.id,
        status=export_record.status.value,
        format=export_record.format,
        file_size_bytes=export_record.file_size_bytes or 0,
        created_at=export_record.created_at,
        expires_at=export_record.expires_at
    )


# ═══════════════════════════════════════════════════════════════════
# GDPR ARTICLE 17 — RIGHT TO ERASURE
# ═══════════════════════════════════════════════════════════════════

@router.post("/delete", response_model=DataDeletionResponse)
async def request_data_deletion(
    request: DataDeletionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """
    GDPR Article 17: Request deletion of all user data.
    
    Permanently deletes all personal data associated with the user.
    Includes a grace period for accidental deletion recovery.
    """
    if not settings.DATA_DELETION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data deletion service is currently disabled"
        )
    
    # Check for existing pending deletion
    existing_deletion = await db.execute(
        select(DataDeletion)
        .where(
            and_(
                DataDeletion.user_id == user.id,
                DataDeletion.status.in_([
                    DataDeletionStatus.requested, 
                    DataDeletionStatus.scheduled,
                    DataDeletionStatus.in_progress
                ])
            )
        )
    )
    if existing_deletion.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A data deletion request is already pending"
        )
    
    # Create deletion record
    deletion_id = uuid.uuid4()
    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour delay
    grace_period_ends_at = None
    
    if settings.SOFT_DELETE_ENABLED and settings.DELETION_GRACE_PERIOD_DAYS > 0:
        grace_period_ends_at = scheduled_at + timedelta(days=settings.DELETION_GRACE_PERIOD_DAYS)
    
    deletion_record = DataDeletion(
        id=deletion_id,
        workspace_id=user.workspace_id,
        user_id=user.id,
        status=DataDeletionStatus.scheduled,
        reason=request.reason,
        scheduled_at=scheduled_at,
        grace_period_ends_at=grace_period_ends_at
    )
    
    db.add(deletion_record)
    await db.commit()
    
    return DataDeletionResponse(
        deletion_id=deletion_id,
        status="scheduled",
        scheduled_at=scheduled_at,
        grace_period_ends_at=grace_period_ends_at,
        message=(
            f"Data deletion scheduled for {scheduled_at.isoformat()}. "
            f"Grace period ends {grace_period_ends_at.isoformat() if grace_period_ends_at else 'immediately'}."
        )
    )


@router.delete("/delete/{deletion_id}")
async def cancel_data_deletion(
    deletion_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Cancel a pending data deletion request during grace period."""
    deletion_record = await db.execute(
        select(DataDeletion)
        .where(
            and_(
                DataDeletion.id == deletion_id,
                DataDeletion.user_id == user.id
            )
        )
    )
    deletion_record = deletion_record.scalar_one_or_none()
    
    if not deletion_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deletion request not found"
        )
    
    if deletion_record.status not in [DataDeletionStatus.requested, DataDeletionStatus.scheduled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel deletion request in current status"
        )
    
    deletion_record.status = DataDeletionStatus.cancelled
    await db.commit()
    
    return {"message": "Data deletion request cancelled successfully"}


# ═══════════════════════════════════════════════════════════════════
# CONSENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@router.post("/consent", response_model=ConsentResponse)
async def update_consent(
    request: ConsentRequest,
    user_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Update user consent preferences for data processing."""
    if not settings.CONSENT_MANAGEMENT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consent management is currently disabled"
        )
    
    # Hash IP address for audit trail (privacy-preserving)
    client_ip = user_request.client.host if user_request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()
    
    # Hash user agent for audit trail
    user_agent = user_request.headers.get("user-agent", "unknown")
    ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()
    
    consent_types = {
        "data_processing": request.data_processing,
        "analytics": request.analytics,
        "marketing": request.marketing,
        "third_party_sharing": request.third_party_sharing
    }
    
    consent_date = datetime.now(timezone.utc)
    
    # Update or create consent records
    for consent_type, granted in consent_types.items():
        if granted is None:
            continue
            
        # Check for existing consent record
        existing_consent = await db.execute(
            select(UserConsent)
            .where(
                and_(
                    UserConsent.user_id == user.id,
                    UserConsent.consent_type == consent_type
                )
            )
        )
        existing_consent = existing_consent.scalar_one_or_none()
        
        if existing_consent:
            existing_consent.status = ConsentStatus.granted if granted else ConsentStatus.withdrawn
            existing_consent.granted_at = consent_date if granted else existing_consent.granted_at
            existing_consent.withdrawn_at = None if granted else consent_date
            existing_consent.ip_address_hash = ip_hash
            existing_consent.user_agent_hash = ua_hash
            existing_consent.updated_at = consent_date
        else:
            new_consent = UserConsent(
                workspace_id=user.workspace_id,
                user_id=user.id,
                consent_type=consent_type,
                status=ConsentStatus.granted if granted else ConsentStatus.withdrawn,
                granted_at=consent_date if granted else None,
                withdrawn_at=None if granted else consent_date,
                ip_address_hash=ip_hash,
                user_agent_hash=ua_hash
            )
            db.add(new_consent)
    
    await db.commit()
    
    # Return current consent status
    return await _get_consent_status(user, db)


@router.get("/consent", response_model=ConsentResponse)
async def get_consent_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Get current user consent status."""
    return await _get_consent_status(user, db)


@router.post("/consent/withdraw")
async def withdraw_consent(
    request: ConsentWithdrawalRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Withdraw consent for specific data processing types."""
    if not settings.CONSENT_MANAGEMENT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consent management is currently disabled"
        )
    
    withdrawal_date = datetime.now(timezone.utc)
    withdrawn_count = 0
    
    for consent_type in request.consent_types:
        consent_record = await db.execute(
            select(UserConsent)
            .where(
                and_(
                    UserConsent.user_id == user.id,
                    UserConsent.consent_type == consent_type
                )
            )
        )
        consent_record = consent_record.scalar_one_or_none()
        
        if consent_record and consent_record.status == ConsentStatus.granted:
            consent_record.status = ConsentStatus.withdrawn
            consent_record.withdrawn_at = withdrawal_date
            consent_record.withdrawal_reason = request.reason
            consent_record.updated_at = withdrawal_date
            withdrawn_count += 1
    
    await db.commit()
    
    return {
        "message": f"Consent withdrawn for {withdrawn_count} data processing types",
        "withdrawn_types": request.consent_types,
        "withdrawal_date": withdrawal_date
    }


# ═══════════════════════════════════════════════════════════════════
# DATA RETENTION POLICIES
# ═══════════════════════════════════════════════════════════════════

@router.get("/retention", response_model=RetentionPolicyResponse)
async def get_retention_policies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Get data retention policies for the workspace."""
    if not settings.DATA_RETENTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data retention management is currently disabled"
        )
    
    # Get workspace retention policies
    policies_result = await db.execute(
        select(RetentionPolicy)
        .where(RetentionPolicy.workspace_id == user.workspace_id)
        .order_by(RetentionPolicy.entity_type)
    )
    policies = policies_result.scalars().all()
    
    # Convert to response format
    policy_infos = []
    for policy in policies:
        policy_info = RetentionPolicyInfo(
            policy_name=f"{policy.entity_type.replace('_', ' ').title()} Retention",
            description=f"Data retention policy for {policy.entity_type}",
            retention_days=policy.retention_days,
            applies_to=[policy.entity_type],
            last_cleanup=policy.last_cleanup_at,
            next_cleanup=policy.next_cleanup_at
        )
        policy_infos.append(policy_info)
    
    return RetentionPolicyResponse(
        policies=policy_infos,
        total_policies=len(policy_infos),
        cleanup_enabled=settings.DATA_RETENTION_ENABLED
    )


@router.post("/retention/cleanup")
async def trigger_retention_cleanup(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """
    Trigger manual retention policy cleanup (admin only).
    
    This endpoint allows administrators to manually trigger data cleanup
    based on retention policies instead of waiting for scheduled cleanup.
    """
    if user.role not in (UserRole.owner, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can trigger retention cleanup"
        )
    
    if not settings.DATA_RETENTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data retention management is currently disabled"
        )
    
    # This would trigger the retention cleanup process
    # In a real implementation, this would be handled by a background task
    cleanup_results = await _execute_retention_cleanup(user.workspace_id, db)
    
    return {
        "message": "Retention cleanup completed",
        "results": cleanup_results,
        "executed_at": datetime.now(timezone.utc)
    }


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE STATUS
# ═══════════════════════════════════════════════════════════════════

@router.get("/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """Get overall GDPR/CCPA compliance status for the user."""
    # Get latest export
    latest_export = await db.execute(
        select(DataExport)
        .where(DataExport.user_id == user.id)
        .order_by(DataExport.created_at.desc())
        .limit(1)
    )
    latest_export = latest_export.scalar_one_or_none()
    
    # Get consent status
    consent_status = await _get_consent_status(user, db)
    
    # Determine compliance status
    gdpr_compliant = (
        settings.DATA_EXPORT_ENABLED and 
        settings.DATA_DELETION_ENABLED and 
        settings.CONSENT_MANAGEMENT_ENABLED
    )
    
    ccpa_compliant = (
        settings.DATA_EXPORT_ENABLED and 
        settings.DATA_DELETION_ENABLED
    )
    
    return ComplianceStatusResponse(
        user_id=user.id,
        workspace_id=user.workspace_id,
        gdpr_compliant=gdpr_compliant,
        ccpa_compliant=ccpa_compliant,
        data_export_available=settings.DATA_EXPORT_ENABLED,
        data_deletion_available=settings.DATA_DELETION_ENABLED,
        consent_management_active=settings.CONSENT_MANAGEMENT_ENABLED,
        retention_policies_active=settings.DATA_RETENTION_ENABLED,
        last_export=latest_export.created_at if latest_export else None,
        consent_status=consent_status
    )


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def _collect_user_data(user: User, db: AsyncSession, include_metadata: bool) -> dict:
    """Collect all user data for export."""
    data = {
        "user_profile": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if include_metadata else None
        }
    }
    
    # Collect transactions
    transactions_result = await db.execute(
        select(Transaction).where(Transaction.user_id == user.id)
    )
    transactions = transactions_result.scalars().all()
    data["transactions"] = [
        {
            "id": str(t.id) if include_metadata else None,
            "date": t.date.isoformat(),
            "description": t.description,
            "amount": str(t.amount),
            "category": t.category,
            "type": t.type.value,
            "account": t.account,
            "vendor": t.vendor,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if include_metadata else None
        }
        for t in transactions
    ]
    
    # Collect budgets
    budgets_result = await db.execute(
        select(Budget).where(Budget.user_id == user.id)
    )
    budgets = budgets_result.scalars().all()
    data["budgets"] = [
        {
            "id": str(b.id) if include_metadata else None,
            "category": b.category,
            "monthly_limit": str(b.monthly_limit),
            "current_spend": str(b.current_spend),
            "month": b.month,
            "created_at": b.created_at.isoformat() if include_metadata else None
        }
        for b in budgets
    ]
    
    # Collect goals
    goals_result = await db.execute(
        select(Goal).where(Goal.user_id == user.id)
    )
    goals = goals_result.scalars().all()
    data["goals"] = [
        {
            "id": str(g.id) if include_metadata else None,
            "title": g.title,
            "target_value": str(g.target_value),
            "current_value": str(g.current_value),
            "metric_type": g.metric_type,
            "status": g.status.value,
            "deadline": g.deadline.isoformat() if g.deadline else None,
            "created_at": g.created_at.isoformat() if include_metadata else None
        }
        for g in goals
    ]
    
    # Collect chat sessions and messages
    chat_sessions_result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.user_id == user.id)
    )
    chat_sessions = chat_sessions_result.scalars().all()
    data["chat_sessions"] = [
        {
            "id": str(cs.id) if include_metadata else None,
            "title": cs.title,
            "created_at": cs.created_at.isoformat() if include_metadata else None,
            "messages": [
                {
                    "id": str(m.id) if include_metadata else None,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if include_metadata else None
                }
                for m in cs.messages
            ]
        }
        for cs in chat_sessions
    ]
    
    # Collect consent records
    consent_result = await db.execute(
        select(UserConsent).where(UserConsent.user_id == user.id)
    )
    consents = consent_result.scalars().all()
    data["consent_records"] = [
        {
            "consent_type": c.consent_type,
            "status": c.status.value,
            "granted_at": c.granted_at.isoformat() if c.granted_at else None,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            "created_at": c.created_at.isoformat() if include_metadata else None
        }
        for c in consents
    ]
    
    return data


async def _generate_export_file(export_id: uuid.UUID, data: dict, format: str) -> tuple[str, int]:
    """Generate export file and return file path and size."""
    import os
    
    # Ensure export directory exists
    export_dir = os.path.join(settings.UPLOAD_DIR, "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    file_name = f"data_export_{export_id}.{format}"
    file_path = os.path.join(export_dir, file_name)
    
    if format == "json":
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:  # CSV format
        # For CSV, we'd need to flatten the data structure
        # This is a simplified implementation
        import csv
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Data Type", "Content"])
            writer.writerow(["User Data", json.dumps(data)])
    
    file_size = os.path.getsize(file_path)
    return file_path, file_size


async def _get_consent_status(user: User, db: AsyncSession) -> ConsentResponse:
    """Get current consent status for user."""
    consent_result = await db.execute(
        select(UserConsent)
        .where(UserConsent.user_id == user.id)
        .order_by(UserConsent.updated_at.desc())
    )
    consents = consent_result.scalars().all()
    
    # Default consent values
    consent_status = {
        "data_processing": False,
        "analytics": False,
        "marketing": False,
        "third_party_sharing": False
    }
    
    latest_consent_date = datetime.now(timezone.utc)
    latest_update_date = datetime.now(timezone.utc)
    
    # Update with actual consent values
    for consent in consents:
        if consent.consent_type in consent_status:
            consent_status[consent.consent_type] = (consent.status == ConsentStatus.granted)
            if consent.granted_at and consent.granted_at < latest_consent_date:
                latest_consent_date = consent.granted_at
            if consent.updated_at and consent.updated_at > latest_update_date:
                latest_update_date = consent.updated_at
    
    return ConsentResponse(
        user_id=user.id,
        data_processing=consent_status["data_processing"],
        analytics=consent_status["analytics"],
        marketing=consent_status["marketing"],
        third_party_sharing=consent_status["third_party_sharing"],
        consent_date=latest_consent_date,
        last_updated=latest_update_date
    )


async def _execute_retention_cleanup(workspace_id: uuid.UUID, db: AsyncSession) -> dict:
    """Execute retention policy cleanup for a workspace."""
    # This is a simplified implementation
    # In production, this would be more sophisticated with proper logging
    
    cleanup_results = {
        "transactions_cleaned": 0,
        "audit_logs_cleaned": 0,
        "chat_messages_cleaned": 0,
        "file_uploads_cleaned": 0
    }
    
    # Get retention policies
    policies_result = await db.execute(
        select(RetentionPolicy)
        .where(
            and_(
                RetentionPolicy.workspace_id == workspace_id,
                RetentionPolicy.is_enabled == True
            )
        )
    )
    policies = policies_result.scalars().all()
    
    for policy in policies:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        if policy.entity_type == "audit_logs":
            # Clean old audit logs
            result = await db.execute(
                delete(AuditLog)
                .where(
                    and_(
                        AuditLog.workspace_id == workspace_id,
                        AuditLog.created_at < cutoff_date
                    )
                )
            )
            cleanup_results["audit_logs_cleaned"] = result.rowcount
        
        elif policy.entity_type == "chat_messages":
            # Clean old chat messages
            result = await db.execute(
                delete(ChatMessage)
                .where(
                    and_(
                        ChatMessage.workspace_id == workspace_id,
                        ChatMessage.created_at < cutoff_date
                    )
                )
            )
            cleanup_results["chat_messages_cleaned"] = result.rowcount
        
        # Update policy last cleanup time
        policy.last_cleanup_at = datetime.now(timezone.utc)
        policy.next_cleanup_at = datetime.now(timezone.utc) + timedelta(days=1)  # Daily cleanup
        policy.cleanup_count += 1
    
    await db.commit()
    return cleanup_results