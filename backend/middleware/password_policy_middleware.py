"""
AI CFO — Password Policy Middleware
Middleware for password validation in future custom authentication implementations.

Note: This middleware is designed for future use with custom authentication.
Current Clerk authentication does not use this middleware.
"""
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from password_policy import validate_password, is_password_policy_enabled


class PasswordPolicyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce password policy on custom authentication endpoints.
    
    This middleware can be selectively applied to custom authentication routes
    that require password validation. It does not affect Clerk authentication.
    """
    
    def __init__(self, app, enforce_on_paths: Optional[list] = None):
        """
        Initialize password policy middleware.
        
        Args:
            app: FastAPI application instance
            enforce_on_paths: List of path patterns to enforce policy on
                             (e.g., ["/api/v1/custom-auth/register", "/api/v1/custom-auth/change-password"])
        """
        super().__init__(app)
        self.enforce_on_paths = enforce_on_paths or [
            "/api/v1/custom-auth/register",
            "/api/v1/custom-auth/change-password",
            "/api/v1/custom-auth/reset-password"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enforce password policy if applicable.
        
        Only processes requests to custom authentication endpoints that require
        password validation. All other requests pass through unchanged.
        """
        # Check if this request should be subject to password policy
        if not self._should_enforce_policy(request):
            return await call_next(request)
        
        # Only enforce if password policy is enabled
        if not is_password_policy_enabled():
            return await call_next(request)
        
        # Extract password from request body for validation
        password = await self._extract_password_from_request(request)
        if not password:
            return await call_next(request)  # No password to validate
        
        # Extract user info for validation
        user_info = await self._extract_user_info_from_request(request)
        
        # Validate password
        result = validate_password(password, user_info)
        
        if not result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet policy requirements",
                    "errors": result.errors,
                    "strength_score": result.strength_score
                }
            )
        
        # Add validation result to request state for use by endpoint
        request.state.password_validation = result
        
        return await call_next(request)
    
    def _should_enforce_policy(self, request: Request) -> bool:
        """Check if password policy should be enforced for this request."""
        return any(
            request.url.path.startswith(path) 
            for path in self.enforce_on_paths
        )
    
    async def _extract_password_from_request(self, request: Request) -> Optional[str]:
        """
        Extract password from request body.
        
        This is a simplified implementation. In a real scenario, you would
        need to handle different content types and request formats.
        """
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                # Clone the request body for inspection
                body = await request.body()
                if body:
                    # This is a simplified example - in practice you'd parse JSON/form data
                    # and extract the password field appropriately
                    import json
                    try:
                        data = json.loads(body)
                        return data.get("password")
                    except (json.JSONDecodeError, AttributeError):
                        pass
        except Exception:
            pass
        
        return None
    
    async def _extract_user_info_from_request(self, request: Request) -> Optional[Dict[str, str]]:
        """
        Extract user information from request for password validation.
        
        This helps prevent passwords that contain user information.
        """
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    import json
                    try:
                        data = json.loads(body)
                        user_info = {}
                        
                        # Extract common user fields
                        if "email" in data:
                            user_info["email"] = data["email"]
                        if "full_name" in data:
                            user_info["full_name"] = data["full_name"]
                        if "name" in data:
                            user_info["full_name"] = data["name"]
                        
                        return user_info if user_info else None
                    except (json.JSONDecodeError, AttributeError):
                        pass
        except Exception:
            pass
        
        return None


def create_password_policy_middleware(enforce_on_paths: Optional[list] = None):
    """
    Factory function to create password policy middleware with custom paths.
    
    Args:
        enforce_on_paths: List of path patterns to enforce policy on
        
    Returns:
        Configured middleware class
    """
    class ConfiguredPasswordPolicyMiddleware(PasswordPolicyMiddleware):
        def __init__(self, app):
            super().__init__(app, enforce_on_paths)
    
    return ConfiguredPasswordPolicyMiddleware


# Utility functions for manual password validation in endpoints
async def validate_request_password(request: Request, user_info: Optional[Dict[str, str]] = None):
    """
    Utility function to manually validate password from request in custom auth endpoints.
    
    This can be used directly in endpoint functions for more control over validation.
    """
    if not is_password_policy_enabled():
        return None  # Policy disabled, no validation needed
    
    # Extract password from request
    try:
        body = await request.body()
        if body:
            import json
            data = json.loads(body)
            password = data.get("password")
            
            if password:
                result = validate_password(password, user_info)
                if not result.is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Password does not meet policy requirements",
                            "errors": result.errors,
                            "strength_score": result.strength_score
                        }
                    )
                return result
    except json.JSONDecodeError:
        pass
    
    return None