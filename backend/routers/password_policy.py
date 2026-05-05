"""
AI CFO — Password Policy Router
Configuration endpoints for password policy framework.

⚠️ DEPRECATION NOTICE (ARCH-002):
This router is currently UNUSED in production. Authentication is handled by Clerk (JWT-based).
The password policy endpoints are maintained for potential future custom authentication but
should be considered for removal to reduce attack surface and maintenance burden.

Note: This router provides configuration for future custom authentication implementations.
Current Clerk authentication does not use these password validation settings.
"""
import warnings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from dependencies import get_rls_db
from models import User
from password_policy import (
    validate_password, 
    get_password_policy, 
    is_password_policy_enabled,
    password_validator
)
from schemas import (
    PasswordValidationRequest,
    PasswordValidationResponse,
    PasswordPolicyInfo,
    PasswordPolicyUpdateRequest
)

router = APIRouter()

# Issue deprecation warning
warnings.warn(
    "password_policy router is currently unused. "
    "Authentication is handled by Clerk. "
    "Consider removing this router. (ARCH-002)",
    DeprecationWarning,
    stacklevel=2
)


@router.get("/info", response_model=PasswordPolicyInfo)
async def get_password_policy_info(
    user: User = Depends(get_current_user)
):
    """
    Get current password policy configuration.
    
    Available to all authenticated users for future custom authentication implementations.
    """
    policy_info = get_password_policy()
    return PasswordPolicyInfo(**policy_info)


@router.post("/validate", response_model=PasswordValidationResponse)
async def validate_password_endpoint(
    request: PasswordValidationRequest,
    user: User = Depends(get_current_user)
):
    """
    Validate a password against the current policy.
    
    This endpoint is designed for future custom authentication implementations
    where password validation will be required during user registration or password changes.
    
    Note: Current Clerk authentication handles password validation internally.
    """
    # Prepare user info for validation if not provided
    user_info = request.user_info or {
        "email": user.email,
        "full_name": user.full_name
    }
    
    result = validate_password(request.password, user_info)
    
    return PasswordValidationResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
        strength_score=result.strength_score
    )


@router.put("/config")
async def update_password_policy_config(
    request: PasswordPolicyUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db)
):
    """
    Update password policy configuration.
    
    Restricted to admin users only. Updates are applied to the global password validator
    for future custom authentication implementations.
    
    Note: Changes do not affect current Clerk authentication behavior.
    """
    # Check if user has admin privileges
    if user.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can modify password policy settings"
        )
    
    # Update validator settings (in a real implementation, these would be persisted to database)
    updates_applied = []
    
    if request.enabled is not None:
        password_validator.enabled = request.enabled
        updates_applied.append(f"enabled: {request.enabled}")
    
    if request.min_length is not None:
        if request.min_length > password_validator.max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum length cannot exceed maximum length"
            )
        password_validator.min_length = request.min_length
        updates_applied.append(f"min_length: {request.min_length}")
    
    if request.max_length is not None:
        if request.max_length < password_validator.min_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum length cannot be less than minimum length"
            )
        password_validator.max_length = request.max_length
        updates_applied.append(f"max_length: {request.max_length}")
    
    if request.require_uppercase is not None:
        password_validator.require_uppercase = request.require_uppercase
        updates_applied.append(f"require_uppercase: {request.require_uppercase}")
    
    if request.require_lowercase is not None:
        password_validator.require_lowercase = request.require_lowercase
        updates_applied.append(f"require_lowercase: {request.require_lowercase}")
    
    if request.require_numbers is not None:
        password_validator.require_numbers = request.require_numbers
        updates_applied.append(f"require_numbers: {request.require_numbers}")
    
    if request.require_special_chars is not None:
        password_validator.require_special_chars = request.require_special_chars
        updates_applied.append(f"require_special_chars: {request.require_special_chars}")
    
    if request.min_special_chars is not None:
        password_validator.min_special_chars = request.min_special_chars
        updates_applied.append(f"min_special_chars: {request.min_special_chars}")
    
    if request.prevent_common_passwords is not None:
        password_validator.prevent_common = request.prevent_common_passwords
        updates_applied.append(f"prevent_common_passwords: {request.prevent_common_passwords}")
    
    if request.prevent_user_info is not None:
        password_validator.prevent_user_info = request.prevent_user_info
        updates_applied.append(f"prevent_user_info: {request.prevent_user_info}")
    
    if not updates_applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid updates provided"
        )
    
    return {
        "status": "updated",
        "message": f"Password policy configuration updated: {', '.join(updates_applied)}",
        "current_policy": get_password_policy()
    }


@router.get("/status")
async def get_password_policy_status(
    user: User = Depends(get_current_user)
):
    """
    Get password policy framework status.
    
    Provides information about whether the password policy framework is enabled
    and ready for future custom authentication implementations.
    """
    return {
        "framework_available": True,
        "policy_enabled": is_password_policy_enabled(),
        "current_auth_method": "clerk",
        "custom_auth_ready": is_password_policy_enabled(),
        "message": (
            "Password policy framework is available for future custom authentication. "
            "Current Clerk authentication does not use these settings."
        )
    }