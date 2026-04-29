"""
Integration tests for password policy API endpoints.

**Validates: Requirements 1.3, 2.3, 3.2**

This test suite validates that the password policy API endpoints work correctly
and that the framework is ready for future custom authentication implementations.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from models import User


class TestPasswordPolicyAPIIntegration:
    """Test password policy API endpoints integration."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        
        # Mock user for authentication
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = "test-user-id"
        self.mock_user.email = "test@example.com"
        self.mock_user.full_name = "Test User"
        self.mock_user.role = "admin"
        self.mock_user.workspace_id = "test-workspace-id"
    
    @patch('routers.password_policy.get_current_user')
    def test_get_password_policy_info_endpoint(self, mock_get_user):
        """Test GET /api/v1/password-policy/info endpoint."""
        mock_get_user.return_value = self.mock_user
        
        response = self.client.get("/api/v1/password-policy/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "enabled" in data
        assert "requirements" in data
        assert isinstance(data["enabled"], bool)
        assert isinstance(data["requirements"], dict)
    
    @patch('routers.password_policy.get_current_user')
    def test_validate_password_endpoint(self, mock_get_user):
        """Test POST /api/v1/password-policy/validate endpoint."""
        mock_get_user.return_value = self.mock_user
        
        # Test with a strong password
        response = self.client.post(
            "/api/v1/password-policy/validate",
            json={
                "password": "StrongP@ssw0rd123!",
                "user_info": {
                    "email": "different@example.com",
                    "full_name": "Different User"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "strength_score" in data
        assert isinstance(data["is_valid"], bool)
        assert isinstance(data["errors"], list)
        assert isinstance(data["warnings"], list)
        assert isinstance(data["strength_score"], int)
        assert 0 <= data["strength_score"] <= 100
    
    @patch('routers.password_policy.get_current_user')
    def test_validate_password_without_user_info(self, mock_get_user):
        """Test password validation without explicit user info."""
        mock_get_user.return_value = self.mock_user
        
        response = self.client.post(
            "/api/v1/password-policy/validate",
            json={"password": "TestPassword123!"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use authenticated user's info for validation
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "strength_score" in data
    
    @patch('routers.password_policy.get_current_user')
    def test_get_password_policy_status_endpoint(self, mock_get_user):
        """Test GET /api/v1/password-policy/status endpoint."""
        mock_get_user.return_value = self.mock_user
        
        response = self.client.get("/api/v1/password-policy/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "framework_available" in data
        assert "policy_enabled" in data
        assert "current_auth_method" in data
        assert "custom_auth_ready" in data
        assert "message" in data
        
        assert data["framework_available"] is True
        assert data["current_auth_method"] == "clerk"
        assert isinstance(data["policy_enabled"], bool)
        assert isinstance(data["custom_auth_ready"], bool)
    
    @patch('routers.password_policy.get_current_user')
    def test_update_password_policy_config_admin(self, mock_get_user):
        """Test PUT /api/v1/password-policy/config endpoint with admin user."""
        # Set up admin user
        self.mock_user.role = "admin"
        mock_get_user.return_value = self.mock_user
        
        response = self.client.put(
            "/api/v1/password-policy/config",
            json={
                "enabled": True,
                "min_length": 10,
                "require_uppercase": True,
                "require_numbers": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "message" in data
        assert "current_policy" in data
        assert data["status"] == "updated"
    
    @patch('routers.password_policy.get_current_user')
    def test_update_password_policy_config_non_admin(self, mock_get_user):
        """Test PUT /api/v1/password-policy/config endpoint with non-admin user."""
        # Set up non-admin user
        self.mock_user.role = "viewer"
        mock_get_user.return_value = self.mock_user
        
        response = self.client.put(
            "/api/v1/password-policy/config",
            json={
                "enabled": True,
                "min_length": 10
            }
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "admin users" in data["detail"]
    
    @patch('routers.password_policy.get_current_user')
    def test_update_password_policy_config_validation(self, mock_get_user):
        """Test password policy config validation."""
        self.mock_user.role = "admin"
        mock_get_user.return_value = self.mock_user
        
        # Test invalid configuration (min > max length)
        response = self.client.put(
            "/api/v1/password-policy/config",
            json={
                "min_length": 20,
                "max_length": 10  # Invalid: max < min
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_password_policy_endpoints_without_auth(self):
        """Test that password policy endpoints require authentication."""
        # Test without authentication - should get 401 or redirect
        endpoints = [
            "/api/v1/password-policy/info",
            "/api/v1/password-policy/status"
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should require authentication (401 or 422 for missing auth)
            assert response.status_code in [401, 422]
    
    def test_backward_compatibility_routing(self):
        """Test that legacy API paths are routed to versioned endpoints."""
        # This test verifies the BackwardCompatibilityMiddleware works
        with patch('routers.password_policy.get_current_user') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            # Test legacy path (should be routed to v1)
            response = self.client.get("/api/password-policy/info")
            
            # Should work the same as versioned endpoint
            # (May get auth error, but should not get 404)
            assert response.status_code != 404


class TestPasswordPolicyFrameworkReadiness:
    """Test that password policy framework is ready for future custom authentication."""
    
    def test_framework_components_available(self):
        """Test that all framework components are available and importable."""
        # Test core password policy module
        from password_policy import (
            PasswordPolicyValidator,
            validate_password,
            get_password_policy,
            is_password_policy_enabled
        )
        
        # Test middleware
        from middleware.password_policy_middleware import (
            PasswordPolicyMiddleware,
            create_password_policy_middleware,
            validate_request_password
        )
        
        # Test schemas
        from schemas import (
            PasswordValidationRequest,
            PasswordValidationResponse,
            PasswordPolicyInfo,
            PasswordPolicyUpdateRequest
        )
        
        # Test router
        from routers.password_policy import router
        
        # All imports should succeed
        assert PasswordPolicyValidator is not None
        assert validate_password is not None
        assert get_password_policy is not None
        assert is_password_policy_enabled is not None
        assert PasswordPolicyMiddleware is not None
        assert create_password_policy_middleware is not None
        assert validate_request_password is not None
        assert PasswordValidationRequest is not None
        assert PasswordValidationResponse is not None
        assert PasswordPolicyInfo is not None
        assert PasswordPolicyUpdateRequest is not None
        assert router is not None
    
    def test_configuration_settings_available(self):
        """Test that password policy configuration settings are available."""
        from config import settings
        
        # Test that all password policy settings exist
        assert hasattr(settings, 'PASSWORD_POLICY_ENABLED')
        assert hasattr(settings, 'PASSWORD_MIN_LENGTH')
        assert hasattr(settings, 'PASSWORD_MAX_LENGTH')
        assert hasattr(settings, 'PASSWORD_REQUIRE_UPPERCASE')
        assert hasattr(settings, 'PASSWORD_REQUIRE_LOWERCASE')
        assert hasattr(settings, 'PASSWORD_REQUIRE_NUMBERS')
        assert hasattr(settings, 'PASSWORD_REQUIRE_SPECIAL_CHARS')
        assert hasattr(settings, 'PASSWORD_SPECIAL_CHARS')
        assert hasattr(settings, 'PASSWORD_MIN_SPECIAL_CHARS')
        assert hasattr(settings, 'PASSWORD_PREVENT_COMMON_PASSWORDS')
        assert hasattr(settings, 'PASSWORD_PREVENT_USER_INFO')
        assert hasattr(settings, 'PASSWORD_HISTORY_COUNT')
        assert hasattr(settings, 'PASSWORD_EXPIRY_DAYS')
        
        # Test default values are reasonable
        assert isinstance(settings.PASSWORD_POLICY_ENABLED, bool)
        assert settings.PASSWORD_MIN_LENGTH >= 1
        assert settings.PASSWORD_MAX_LENGTH >= settings.PASSWORD_MIN_LENGTH
        assert isinstance(settings.PASSWORD_SPECIAL_CHARS, str)
        assert len(settings.PASSWORD_SPECIAL_CHARS) > 0
    
    def test_clerk_authentication_unaffected(self):
        """Test that Clerk authentication is not affected by password policy framework."""
        # Test that Clerk auth modules still import correctly
        from auth import get_current_user, provision_user_and_workspace
        from routers.auth import router as auth_router
        
        # Test that password policy is disabled by default
        from config import settings
        assert settings.PASSWORD_POLICY_ENABLED is False
        
        # Test that auth router still works
        assert auth_router is not None
        assert get_current_user is not None
        assert provision_user_and_workspace is not None