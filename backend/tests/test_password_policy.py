"""
Tests for password policy framework.

**Validates: Requirements 1.3, 2.3, 3.2**

This test suite validates the password policy framework implementation
for future custom authentication use while ensuring Clerk authentication
continues to work unchanged.
"""
import pytest
from unittest.mock import patch, MagicMock

from password_policy import (
    PasswordPolicyValidator,
    validate_password,
    get_password_policy,
    is_password_policy_enabled,
    PasswordValidationResult
)
from config import settings


class TestPasswordPolicyValidator:
    """Test the core password policy validator."""
    
    def test_validator_initialization(self):
        """Test validator initializes with current settings."""
        validator = PasswordPolicyValidator()
        
        assert validator.enabled == settings.PASSWORD_POLICY_ENABLED
        assert validator.min_length == settings.PASSWORD_MIN_LENGTH
        assert validator.max_length == settings.PASSWORD_MAX_LENGTH
        assert validator.require_uppercase == settings.PASSWORD_REQUIRE_UPPERCASE
        assert validator.require_lowercase == settings.PASSWORD_REQUIRE_LOWERCASE
        assert validator.require_numbers == settings.PASSWORD_REQUIRE_NUMBERS
        assert validator.require_special_chars == settings.PASSWORD_REQUIRE_SPECIAL_CHARS
    
    def test_password_validation_disabled(self):
        """Test validation when policy is disabled."""
        validator = PasswordPolicyValidator()
        validator.enabled = False
        
        result = validator.validate_password("weak")
        
        assert result.is_valid is True
        assert "Password policy is disabled" in result.warnings
        assert result.strength_score == 50
    
    def test_password_length_validation(self):
        """Test password length requirements."""
        validator = PasswordPolicyValidator()
        validator.enabled = True
        validator.min_length = 8
        validator.max_length = 20
        
        # Too short
        result = validator.validate_password("short")
        assert not result.is_valid
        assert any("at least 8 characters" in error for error in result.errors)
        
        # Too long
        result = validator.validate_password("a" * 25)
        assert not result.is_valid
        assert any("not exceed 20 characters" in error for error in result.errors)
        
        # Valid length
        result = validator.validate_password("ValidPass123!")
        assert len([e for e in result.errors if "characters" in e]) == 0
    
    def test_character_requirements(self):
        """Test character type requirements."""
        validator = PasswordPolicyValidator()
        validator.enabled = True
        validator.min_length = 8
        validator.require_uppercase = True
        validator.require_lowercase = True
        validator.require_numbers = True
        validator.require_special_chars = True
        
        # Missing uppercase
        result = validator.validate_password("lowercase123!")
        assert not result.is_valid
        assert any("uppercase letter" in error for error in result.errors)
        
        # Missing lowercase
        result = validator.validate_password("UPPERCASE123!")
        assert not result.is_valid
        assert any("lowercase letter" in error for error in result.errors)
        
        # Missing numbers
        result = validator.validate_password("ValidPass!")
        assert not result.is_valid
        assert any("number" in error for error in result.errors)
        
        # Missing special characters
        result = validator.validate_password("ValidPass123")
        assert not result.is_valid
        assert any("special character" in error for error in result.errors)
        
        # All requirements met
        result = validator.validate_password("ValidPass123!")
        assert result.is_valid
    
    def test_common_password_prevention(self):
        """Test prevention of common passwords."""
        validator = PasswordPolicyValidator()
        validator.enabled = True
        validator.min_length = 8
        validator.prevent_common = True
        
        result = validator.validate_password("password")
        assert not result.is_valid
        assert any("too common" in error for error in result.errors)
    
    def test_user_info_prevention(self):
        """Test prevention of passwords containing user info."""
        validator = PasswordPolicyValidator()
        validator.enabled = True
        validator.min_length = 8
        validator.prevent_user_info = True
        
        user_info = {
            "email": "john.doe@example.com",
            "full_name": "John Doe"
        }
        
        # Password contains email part
        result = validator.validate_password("john123!", user_info)
        assert not result.is_valid
        assert any("email address" in error for error in result.errors)
        
        # Password contains name part
        result = validator.validate_password("doe123!", user_info)
        assert not result.is_valid
        assert any("name" in error for error in result.errors)
    
    def test_strength_scoring(self):
        """Test password strength scoring."""
        validator = PasswordPolicyValidator()
        validator.enabled = True
        validator.min_length = 8
        
        # Weak password (meets minimum requirements)
        result = validator.validate_password("Pass123!")
        assert result.is_valid
        assert 0 <= result.strength_score <= 100
        
        # Strong password
        result = validator.validate_password("VeryStrongP@ssw0rd2024!")
        assert result.is_valid
        assert result.strength_score > 80
    
    def test_get_policy_info(self):
        """Test policy information retrieval."""
        validator = PasswordPolicyValidator()
        policy_info = validator.get_policy_info()
        
        assert "enabled" in policy_info
        assert "requirements" in policy_info
        assert "min_length" in policy_info["requirements"]
        assert "max_length" in policy_info["requirements"]


class TestPasswordPolicyFunctions:
    """Test module-level convenience functions."""
    
    def test_validate_password_function(self):
        """Test the validate_password convenience function."""
        result = validate_password("TestPass123!")
        assert isinstance(result, PasswordValidationResult)
    
    def test_get_password_policy_function(self):
        """Test the get_password_policy convenience function."""
        policy = get_password_policy()
        assert isinstance(policy, dict)
        assert "enabled" in policy
        assert "requirements" in policy
    
    def test_is_password_policy_enabled_function(self):
        """Test the is_password_policy_enabled convenience function."""
        enabled = is_password_policy_enabled()
        assert isinstance(enabled, bool)


class TestPasswordPolicyIntegration:
    """Test password policy integration scenarios."""
    
    def test_policy_framework_availability(self):
        """
        Test that password policy framework is available for future custom authentication.
        
        **Validates: Requirements 2.3** - configurable password policy validation framework
        """
        # Framework should be importable and functional
        from password_policy import PasswordPolicyValidator, validate_password
        
        validator = PasswordPolicyValidator()
        assert validator is not None
        
        # Should be able to validate passwords
        result = validate_password("TestPassword123!")
        assert isinstance(result, PasswordValidationResult)
        
        # Should provide policy configuration
        policy = get_password_policy()
        assert "enabled" in policy
        assert "requirements" in policy
    
    def test_clerk_authentication_preservation(self):
        """
        Test that Clerk authentication is not affected by password policy framework.
        
        **Validates: Requirements 3.2** - Clerk authentication continues to work
        """
        # Password policy should not interfere with Clerk auth imports
        try:
            from auth import get_current_user, provision_user_and_workspace
            assert get_current_user is not None
            assert provision_user_and_workspace is not None
        except ImportError as e:
            pytest.fail(f"Clerk authentication imports failed: {e}")
        
        # Password policy should be disabled by default to not interfere
        assert settings.PASSWORD_POLICY_ENABLED is False
    
    def test_configurable_policy_parameters(self):
        """
        Test that password policy parameters are configurable.
        
        **Validates: Requirements 2.3** - configurable password policy parameters
        """
        # Test that all policy parameters are configurable
        validator = PasswordPolicyValidator()
        validator.enabled = True  # Enable for testing
        
        # Test length configuration
        validator.min_length = 12
        validator.max_length = 64
        result = validator.validate_password("short")
        assert not result.is_valid
        
        # Test character requirements configuration
        validator.require_uppercase = False
        validator.require_lowercase = True
        validator.require_numbers = True
        validator.require_special_chars = False
        
        result = validator.validate_password("lowercase123")
        assert result.is_valid  # Should pass with relaxed requirements
    
    def test_future_custom_auth_readiness(self):
        """
        Test that framework is ready for future custom authentication implementations.
        
        **Validates: Requirements 2.3** - policy configuration endpoints for future custom auth
        """
        # Test that policy can be enabled and configured
        validator = PasswordPolicyValidator()
        validator.enabled = True
        
        # Test validation works when enabled
        result = validator.validate_password("WeakPass")
        assert not result.is_valid
        
        result = validator.validate_password("StrongP@ssw0rd123!")
        assert result.is_valid
        
        # Test policy info is available for API endpoints
        policy_info = validator.get_policy_info()
        assert policy_info["enabled"] is True
        assert "requirements" in policy_info


class TestPasswordPolicyRouter:
    """Test password policy API endpoints."""
    
    def test_password_policy_endpoints_exist(self):
        """Test that password policy endpoints are available."""
        # This test verifies the router is properly configured
        from routers.password_policy import router
        
        # Check that router has the expected endpoints
        routes = [route.path for route in router.routes]
        
        assert "/info" in routes
        assert "/validate" in routes
        assert "/config" in routes
        assert "/status" in routes
    
    def test_password_validation_request_schema(self):
        """Test password validation request schema."""
        from schemas import PasswordValidationRequest
        
        # Valid request
        request = PasswordValidationRequest(
            password="TestPass123!",
            user_info={"email": "test@example.com"}
        )
        assert request.password == "TestPass123!"
        assert request.user_info["email"] == "test@example.com"
        
        # Request without user_info
        request = PasswordValidationRequest(password="TestPass123!")
        assert request.password == "TestPass123!"
        assert request.user_info is None
    
    def test_password_validation_response_schema(self):
        """Test password validation response schema."""
        from schemas import PasswordValidationResponse
        
        response = PasswordValidationResponse(
            is_valid=True,
            errors=[],
            warnings=["Password could be stronger"],
            strength_score=75
        )
        
        assert response.is_valid is True
        assert response.errors == []
        assert response.warnings == ["Password could be stronger"]
        assert response.strength_score == 75
    
    def test_password_policy_info_schema(self):
        """Test password policy info schema."""
        from schemas import PasswordPolicyInfo
        
        info = PasswordPolicyInfo(
            enabled=True,
            requirements={
                "min_length": 8,
                "require_uppercase": True
            }
        )
        
        assert info.enabled is True
        assert info.requirements["min_length"] == 8