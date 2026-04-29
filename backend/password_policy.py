"""
AI CFO — Password Policy Framework
Configurable password validation for future custom authentication implementations.

Note: This framework is designed for future custom authentication use.
Current Clerk authentication does not use these validation functions.
"""
import re
import string
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from config import settings


@dataclass
class PasswordValidationResult:
    """Result of password validation with detailed feedback."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    strength_score: int  # 0-100


class PasswordPolicyValidator:
    """Configurable password policy validator for custom authentication."""
    
    def __init__(self):
        """Initialize validator with current settings."""
        self.enabled = settings.PASSWORD_POLICY_ENABLED
        self.min_length = settings.PASSWORD_MIN_LENGTH
        self.max_length = settings.PASSWORD_MAX_LENGTH
        self.require_uppercase = settings.PASSWORD_REQUIRE_UPPERCASE
        self.require_lowercase = settings.PASSWORD_REQUIRE_LOWERCASE
        self.require_numbers = settings.PASSWORD_REQUIRE_NUMBERS
        self.require_special_chars = settings.PASSWORD_REQUIRE_SPECIAL_CHARS
        self.special_chars = settings.PASSWORD_SPECIAL_CHARS
        self.min_special_chars = settings.PASSWORD_MIN_SPECIAL_CHARS
        self.prevent_common = settings.PASSWORD_PREVENT_COMMON_PASSWORDS
        self.prevent_user_info = settings.PASSWORD_PREVENT_USER_INFO
        
        # Common passwords list (subset for demonstration)
        self.common_passwords = {
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "1234567890", "password1",
            "abc123", "Password1", "password!", "123456789", "welcome123"
        }
    
    def validate_password(
        self, 
        password: str, 
        user_info: Optional[Dict[str, str]] = None
    ) -> PasswordValidationResult:
        """
        Validate password against configured policy.
        
        Args:
            password: The password to validate
            user_info: Optional user information (email, name, etc.) to check against
            
        Returns:
            PasswordValidationResult with validation details
        """
        if not self.enabled:
            return PasswordValidationResult(
                is_valid=True,
                errors=[],
                warnings=["Password policy is disabled"],
                strength_score=50
            )
        
        errors = []
        warnings = []
        strength_score = 0
        
        # Length validation
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        elif len(password) >= self.min_length:
            strength_score += 20
            
        if len(password) > self.max_length:
            errors.append(f"Password must not exceed {self.max_length} characters")
        
        # Character type requirements
        has_uppercase = bool(re.search(r'[A-Z]', password))
        has_lowercase = bool(re.search(r'[a-z]', password))
        has_numbers = bool(re.search(r'\d', password))
        has_special = bool(re.search(f'[{re.escape(self.special_chars)}]', password))
        
        if self.require_uppercase and not has_uppercase:
            errors.append("Password must contain at least one uppercase letter")
        elif has_uppercase:
            strength_score += 15
            
        if self.require_lowercase and not has_lowercase:
            errors.append("Password must contain at least one lowercase letter")
        elif has_lowercase:
            strength_score += 15
            
        if self.require_numbers and not has_numbers:
            errors.append("Password must contain at least one number")
        elif has_numbers:
            strength_score += 15
            
        if self.require_special_chars and not has_special:
            errors.append(f"Password must contain at least one special character: {self.special_chars}")
        elif has_special:
            strength_score += 15
            
        # Special character count
        special_count = len([c for c in password if c in self.special_chars])
        if self.require_special_chars and special_count < self.min_special_chars:
            errors.append(f"Password must contain at least {self.min_special_chars} special characters")
        
        # Common password check
        if self.prevent_common and password.lower() in self.common_passwords:
            errors.append("Password is too common and easily guessable")
        
        # User information check
        if self.prevent_user_info and user_info:
            self._check_user_info_in_password(password, user_info, errors)
        
        # Additional strength scoring
        if len(password) >= 12:
            strength_score += 10
        if len(set(password)) >= len(password) * 0.7:  # Character diversity
            strength_score += 10
        
        # Cap strength score
        strength_score = min(100, strength_score)
        
        # Add warnings for weak but valid passwords
        if strength_score < 60 and not errors:
            warnings.append("Password meets requirements but could be stronger")
        
        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            strength_score=strength_score
        )
    
    def _check_user_info_in_password(
        self, 
        password: str, 
        user_info: Dict[str, str], 
        errors: List[str]
    ) -> None:
        """Check if password contains user information."""
        password_lower = password.lower()
        
        # Check email parts
        if 'email' in user_info:
            email_parts = user_info['email'].lower().split('@')[0].split('.')
            for part in email_parts:
                if len(part) >= 3 and part in password_lower:
                    errors.append("Password must not contain parts of your email address")
                    break
        
        # Check name parts
        if 'full_name' in user_info:
            name_parts = user_info['full_name'].lower().split()
            for part in name_parts:
                if len(part) >= 3 and part in password_lower:
                    errors.append("Password must not contain parts of your name")
                    break
    
    def get_policy_info(self) -> Dict[str, Any]:
        """Get current password policy configuration."""
        return {
            "enabled": self.enabled,
            "requirements": {
                "min_length": self.min_length,
                "max_length": self.max_length,
                "require_uppercase": self.require_uppercase,
                "require_lowercase": self.require_lowercase,
                "require_numbers": self.require_numbers,
                "require_special_chars": self.require_special_chars,
                "min_special_chars": self.min_special_chars,
                "special_chars": self.special_chars,
                "prevent_common_passwords": self.prevent_common,
                "prevent_user_info": self.prevent_user_info
            }
        }


# Global validator instance
password_validator = PasswordPolicyValidator()


def validate_password(
    password: str, 
    user_info: Optional[Dict[str, str]] = None
) -> PasswordValidationResult:
    """
    Convenience function for password validation.
    
    Args:
        password: The password to validate
        user_info: Optional user information to check against
        
    Returns:
        PasswordValidationResult with validation details
    """
    return password_validator.validate_password(password, user_info)


def get_password_policy() -> Dict[str, Any]:
    """Get current password policy configuration."""
    return password_validator.get_policy_info()


def is_password_policy_enabled() -> bool:
    """Check if password policy validation is enabled."""
    return password_validator.enabled