"""
AI CFO — Consent Management Service
Handles user consent tracking and management for GDPR compliance.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict
import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models import UserConsent, User, ConsentStatus


class ConsentManager:
    """
    Service for managing user consent preferences and tracking.
    
    Implements GDPR requirements for consent management including:
    - Tracking consent grants and withdrawals
    - Maintaining audit trail of consent changes
    - Privacy-preserving IP and user agent hashing
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def grant_consent(
        self,
        user: User,
        consent_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserConsent:
        """
        Grant consent for a specific data processing type.
        
        Args:
            user: The user granting consent
            consent_type: Type of consent (data_processing, analytics, marketing, third_party_sharing)
            ip_address: Client IP address (will be hashed for privacy)
            user_agent: Client user agent (will be hashed for privacy)
        
        Returns:
            UserConsent record
        """
        # Hash IP and user agent for privacy
        ip_hash = self._hash_value(ip_address) if ip_address else None
        ua_hash = self._hash_value(user_agent) if user_agent else None
        
        consent_date = datetime.now(timezone.utc)
        
        # Check for existing consent record
        existing_consent = await self.get_consent(user.id, consent_type)
        
        if existing_consent:
            # Update existing consent
            existing_consent.status = ConsentStatus.granted
            existing_consent.granted_at = consent_date
            existing_consent.withdrawn_at = None
            existing_consent.ip_address_hash = ip_hash
            existing_consent.user_agent_hash = ua_hash
            existing_consent.updated_at = consent_date
            await self.db.commit()
            return existing_consent
        else:
            # Create new consent record
            new_consent = UserConsent(
                workspace_id=user.workspace_id,
                user_id=user.id,
                consent_type=consent_type,
                status=ConsentStatus.granted,
                granted_at=consent_date,
                ip_address_hash=ip_hash,
                user_agent_hash=ua_hash
            )
            self.db.add(new_consent)
            await self.db.commit()
            await self.db.refresh(new_consent)
            return new_consent
    
    async def withdraw_consent(
        self,
        user: User,
        consent_type: str,
        reason: Optional[str] = None
    ) -> Optional[UserConsent]:
        """
        Withdraw consent for a specific data processing type.
        
        Args:
            user: The user withdrawing consent
            consent_type: Type of consent to withdraw
            reason: Optional reason for withdrawal
        
        Returns:
            Updated UserConsent record or None if not found
        """
        consent_record = await self.get_consent(user.id, consent_type)
        
        if not consent_record:
            return None
        
        if consent_record.status == ConsentStatus.granted:
            withdrawal_date = datetime.now(timezone.utc)
            consent_record.status = ConsentStatus.withdrawn
            consent_record.withdrawn_at = withdrawal_date
            consent_record.withdrawal_reason = reason
            consent_record.updated_at = withdrawal_date
            await self.db.commit()
            await self.db.refresh(consent_record)
        
        return consent_record
    
    async def get_consent(
        self,
        user_id: uuid.UUID,
        consent_type: str
    ) -> Optional[UserConsent]:
        """
        Get consent record for a specific user and consent type.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
        
        Returns:
            UserConsent record or None if not found
        """
        result = await self.db.execute(
            select(UserConsent)
            .where(
                and_(
                    UserConsent.user_id == user_id,
                    UserConsent.consent_type == consent_type
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_consents(self, user_id: uuid.UUID) -> List[UserConsent]:
        """
        Get all consent records for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of UserConsent records
        """
        result = await self.db.execute(
            select(UserConsent)
            .where(UserConsent.user_id == user_id)
            .order_by(UserConsent.updated_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_consent_status(self, user_id: uuid.UUID) -> Dict[str, bool]:
        """
        Get current consent status for all consent types.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary mapping consent types to granted status
        """
        consents = await self.get_all_consents(user_id)
        
        # Default consent values
        consent_status = {
            "data_processing": False,
            "analytics": False,
            "marketing": False,
            "third_party_sharing": False
        }
        
        # Update with actual consent values
        for consent in consents:
            if consent.consent_type in consent_status:
                consent_status[consent.consent_type] = (
                    consent.status == ConsentStatus.granted
                )
        
        return consent_status
    
    async def has_consent(
        self,
        user_id: uuid.UUID,
        consent_type: str
    ) -> bool:
        """
        Check if user has granted consent for a specific type.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to check
        
        Returns:
            True if consent is granted, False otherwise
        """
        consent = await self.get_consent(user_id, consent_type)
        return consent is not None and consent.status == ConsentStatus.granted
    
    async def bulk_update_consents(
        self,
        user: User,
        consent_updates: Dict[str, bool],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> List[UserConsent]:
        """
        Update multiple consent preferences at once.
        
        Args:
            user: The user updating consents
            consent_updates: Dictionary mapping consent types to granted status
            ip_address: Client IP address (will be hashed for privacy)
            user_agent: Client user agent (will be hashed for privacy)
        
        Returns:
            List of updated UserConsent records
        """
        updated_consents = []
        
        for consent_type, granted in consent_updates.items():
            if granted:
                consent = await self.grant_consent(
                    user, consent_type, ip_address, user_agent
                )
            else:
                consent = await self.withdraw_consent(user, consent_type)
            
            if consent:
                updated_consents.append(consent)
        
        return updated_consents
    
    @staticmethod
    def _hash_value(value: str) -> str:
        """
        Hash a value using SHA-256 for privacy-preserving storage.
        
        Args:
            value: Value to hash
        
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(value.encode()).hexdigest()
