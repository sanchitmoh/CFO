"""
AI CFO — Data Retention Policy Service
Handles automated data cleanup and retention policy management.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from models import (
    RetentionPolicy, AuditLog, ChatMessage, FileUpload, 
    Transaction, DataExport, DataDeletion
)


class RetentionPolicyManager:
    """
    Service for managing data retention policies and automated cleanup.
    
    Implements GDPR requirements for data retention including:
    - Configurable retention periods per entity type
    - Automated cleanup of expired data
    - Audit trail of cleanup operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_policy(
        self,
        workspace_id: uuid.UUID,
        entity_type: str,
        retention_days: int,
        description: Optional[str] = None,
        is_enabled: bool = True
    ) -> RetentionPolicy:
        """
        Create a new retention policy for a workspace.
        
        Args:
            workspace_id: Workspace ID
            entity_type: Type of entity (audit_logs, chat_messages, transactions, etc.)
            retention_days: Number of days to retain data
            description: Optional policy description
            is_enabled: Whether policy is active
        
        Returns:
            Created RetentionPolicy record
        """
        policy = RetentionPolicy(
            workspace_id=workspace_id,
            entity_type=entity_type,
            retention_days=retention_days,
            description=description,
            is_enabled=is_enabled,
            next_cleanup_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy
    
    async def get_policy(
        self,
        workspace_id: uuid.UUID,
        entity_type: str
    ) -> Optional[RetentionPolicy]:
        """
        Get retention policy for a specific entity type.
        
        Args:
            workspace_id: Workspace ID
            entity_type: Type of entity
        
        Returns:
            RetentionPolicy record or None if not found
        """
        result = await self.db.execute(
            select(RetentionPolicy)
            .where(
                and_(
                    RetentionPolicy.workspace_id == workspace_id,
                    RetentionPolicy.entity_type == entity_type
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_policies(
        self,
        workspace_id: uuid.UUID,
        enabled_only: bool = False
    ) -> List[RetentionPolicy]:
        """
        Get all retention policies for a workspace.
        
        Args:
            workspace_id: Workspace ID
            enabled_only: If True, only return enabled policies
        
        Returns:
            List of RetentionPolicy records
        """
        query = select(RetentionPolicy).where(
            RetentionPolicy.workspace_id == workspace_id
        )
        
        if enabled_only:
            query = query.where(RetentionPolicy.is_enabled == True)
        
        query = query.order_by(RetentionPolicy.entity_type)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_policy(
        self,
        policy_id: uuid.UUID,
        retention_days: Optional[int] = None,
        description: Optional[str] = None,
        is_enabled: Optional[bool] = None
    ) -> Optional[RetentionPolicy]:
        """
        Update an existing retention policy.
        
        Args:
            policy_id: Policy ID
            retention_days: New retention period in days
            description: New description
            is_enabled: New enabled status
        
        Returns:
            Updated RetentionPolicy record or None if not found
        """
        result = await self.db.execute(
            select(RetentionPolicy).where(RetentionPolicy.id == policy_id)
        )
        policy = result.scalar_one_or_none()
        
        if not policy:
            return None
        
        if retention_days is not None:
            policy.retention_days = retention_days
        if description is not None:
            policy.description = description
        if is_enabled is not None:
            policy.is_enabled = is_enabled
        
        policy.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy
    
    async def execute_cleanup(
        self,
        workspace_id: uuid.UUID,
        entity_type: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Execute retention policy cleanup for a workspace.
        
        Args:
            workspace_id: Workspace ID
            entity_type: Optional specific entity type to clean up
        
        Returns:
            Dictionary with cleanup results per entity type
        """
        cleanup_results = {}
        
        # Get policies to execute
        if entity_type:
            policy = await self.get_policy(workspace_id, entity_type)
            policies = [policy] if policy else []
        else:
            policies = await self.get_all_policies(workspace_id, enabled_only=True)
        
        # Execute cleanup for each policy
        for policy in policies:
            if not policy.is_enabled:
                continue
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
            deleted_count = 0
            
            try:
                if policy.entity_type == "audit_logs":
                    deleted_count = await self._cleanup_audit_logs(workspace_id, cutoff_date)
                
                elif policy.entity_type == "chat_messages":
                    deleted_count = await self._cleanup_chat_messages(workspace_id, cutoff_date)
                
                elif policy.entity_type == "file_uploads":
                    deleted_count = await self._cleanup_file_uploads(workspace_id, cutoff_date)
                
                elif policy.entity_type == "data_exports":
                    deleted_count = await self._cleanup_data_exports(workspace_id, cutoff_date)
                
                elif policy.entity_type == "transactions":
                    # Be careful with financial data - may need special handling
                    deleted_count = await self._cleanup_transactions(workspace_id, cutoff_date)
                
                # Update policy metadata
                policy.last_cleanup_at = datetime.now(timezone.utc)
                policy.next_cleanup_at = datetime.now(timezone.utc) + timedelta(days=1)
                policy.cleanup_count += 1
                
                cleanup_results[policy.entity_type] = deleted_count
                
            except Exception as e:
                cleanup_results[policy.entity_type] = f"Error: {str(e)}"
        
        await self.db.commit()
        return cleanup_results
    
    async def _cleanup_audit_logs(
        self,
        workspace_id: uuid.UUID,
        cutoff_date: datetime
    ) -> int:
        """Clean up old audit logs."""
        result = await self.db.execute(
            delete(AuditLog)
            .where(
                and_(
                    AuditLog.workspace_id == workspace_id,
                    AuditLog.created_at < cutoff_date
                )
            )
        )
        return result.rowcount
    
    async def _cleanup_chat_messages(
        self,
        workspace_id: uuid.UUID,
        cutoff_date: datetime
    ) -> int:
        """Clean up old chat messages."""
        result = await self.db.execute(
            delete(ChatMessage)
            .where(
                and_(
                    ChatMessage.workspace_id == workspace_id,
                    ChatMessage.created_at < cutoff_date
                )
            )
        )
        return result.rowcount
    
    async def _cleanup_file_uploads(
        self,
        workspace_id: uuid.UUID,
        cutoff_date: datetime
    ) -> int:
        """Clean up old file uploads."""
        # Note: This should also delete physical files from storage
        result = await self.db.execute(
            delete(FileUpload)
            .where(
                and_(
                    FileUpload.workspace_id == workspace_id,
                    FileUpload.created_at < cutoff_date
                )
            )
        )
        return result.rowcount
    
    async def _cleanup_data_exports(
        self,
        workspace_id: uuid.UUID,
        cutoff_date: datetime
    ) -> int:
        """Clean up expired data exports."""
        # Clean up exports that have expired
        result = await self.db.execute(
            delete(DataExport)
            .where(
                and_(
                    DataExport.workspace_id == workspace_id,
                    DataExport.expires_at < datetime.now(timezone.utc)
                )
            )
        )
        return result.rowcount
    
    async def _cleanup_transactions(
        self,
        workspace_id: uuid.UUID,
        cutoff_date: datetime
    ) -> int:
        """
        Clean up old transactions.
        
        WARNING: Be careful with financial data cleanup.
        Consider regulatory requirements before enabling this.
        """
        # This is a placeholder - financial data cleanup needs careful consideration
        # May need to archive instead of delete, or have longer retention periods
        # For now, we'll return 0 to indicate no cleanup
        return 0
    
    async def get_cleanup_schedule(
        self,
        workspace_id: uuid.UUID
    ) -> List[Dict]:
        """
        Get scheduled cleanup information for all policies.
        
        Args:
            workspace_id: Workspace ID
        
        Returns:
            List of dictionaries with policy and schedule information
        """
        policies = await self.get_all_policies(workspace_id, enabled_only=True)
        
        schedule = []
        for policy in policies:
            schedule.append({
                "entity_type": policy.entity_type,
                "retention_days": policy.retention_days,
                "last_cleanup": policy.last_cleanup_at,
                "next_cleanup": policy.next_cleanup_at,
                "cleanup_count": policy.cleanup_count,
                "is_enabled": policy.is_enabled
            })
        
        return schedule
    
    async def estimate_cleanup_impact(
        self,
        workspace_id: uuid.UUID,
        entity_type: str
    ) -> Dict[str, int]:
        """
        Estimate how many records would be deleted by cleanup.
        
        Args:
            workspace_id: Workspace ID
            entity_type: Type of entity to estimate
        
        Returns:
            Dictionary with estimated counts
        """
        policy = await self.get_policy(workspace_id, entity_type)
        
        if not policy:
            return {"estimated_deletions": 0, "error": "Policy not found"}
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        # Count records that would be deleted
        if entity_type == "audit_logs":
            result = await self.db.execute(
                select(AuditLog)
                .where(
                    and_(
                        AuditLog.workspace_id == workspace_id,
                        AuditLog.created_at < cutoff_date
                    )
                )
            )
            count = len(result.scalars().all())
        
        elif entity_type == "chat_messages":
            result = await self.db.execute(
                select(ChatMessage)
                .where(
                    and_(
                        ChatMessage.workspace_id == workspace_id,
                        ChatMessage.created_at < cutoff_date
                    )
                )
            )
            count = len(result.scalars().all())
        
        else:
            count = 0
        
        return {
            "estimated_deletions": count,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": policy.retention_days
        }
