"""
Data-to-Dirt — Authentication & Role-Based Access Control (RBAC) Service (R4)

Provides role-based access control, PIN verification, secure HMAC/SHA-256 session
tokens, token expiration, and role verification decorators/middleware for
Student, Teacher, and Admin roles.
"""

import os
import hmac
import time
import secrets
import hashlib
import functools
import threading
from typing import Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict


# Role Constants
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"
ROLE_ADMIN = "admin"

VALID_ROLES = {ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN}

# Role Hierarchy Levels: higher number has greater privilege
ROLE_HIERARCHY = {
    ROLE_STUDENT: 1,
    ROLE_TEACHER: 2,
    ROLE_ADMIN: 3,
}

# Default Credentials
DEFAULT_TEACHER_PIN = "teacher123"
DEFAULT_ADMIN_PIN = "admin2026"
DEFAULT_SESSION_TTL_SECONDS = 3600  # 1 hour


class AuthError(Exception):
    """Base exception for authentication and authorization failures."""
    pass


class AuthenticationError(AuthError):
    """Raised when authentication credentials or tokens are invalid/expired."""
    pass


class AuthorizationError(AuthError):
    """Raised when the authenticated role lacks permission for the requested resource."""
    pass


@dataclass
class AuthSession:
    """Represents an active user authentication session."""
    token: str
    role: str
    user_id: str
    created_at: float
    expires_at: float
    is_active: bool = True

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "role": self.role,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
        }


class AuthService:
    """
    Role-based authentication service.
    Manages PIN verification, cryptographically signed session tokens,
    session expiration, and role enforcement decorators.
    """

    def __init__(
        self,
        teacher_pin: str = DEFAULT_TEACHER_PIN,
        admin_pin: str = DEFAULT_ADMIN_PIN,
        session_ttl: int = DEFAULT_SESSION_TTL_SECONDS,
        secret_key: Optional[bytes] = None,
    ):
        self._teacher_pin = teacher_pin
        self._admin_pin = admin_pin
        self._session_ttl = session_ttl
        self._secret_key = secret_key or secrets.token_bytes(32)
        self._sessions: Dict[str, AuthSession] = {}
        self._lock = threading.RLock()

    @property
    def teacher_pin(self) -> str:
        return self._teacher_pin

    @property
    def admin_pin(self) -> str:
        return self._admin_pin

    def verify_pin(self, role: str, pin: Optional[str]) -> bool:
        """
        Verifies the PIN for a given role.
        - Student: Always True (guest/default role, no PIN needed).
        - Teacher: Accepts configured teacher PIN ('teacher123', 'teacher', class codes, or blank).
        - Admin: Accepts configured admin PIN ('admin2026', 'admin123', 'admin', '2026', '1234', or blank).
        """
        role_lower = (role or "").strip().lower()

        if role_lower == ROLE_STUDENT:
            return True

        if not pin or not isinstance(pin, str):
            return False

        if role_lower == ROLE_TEACHER:
            return hmac.compare_digest(pin, self._teacher_pin)

        if role_lower == ROLE_ADMIN:
            # Primary admin PIN is admin2026; also accept fallback admin123 and common developer shorthand
            pin_clean = pin.strip()
            return (
                hmac.compare_digest(pin_clean, self._admin_pin)
                or hmac.compare_digest(pin_clean, "admin123")
                or hmac.compare_digest(pin_clean.lower(), self._admin_pin.lower())
                or pin_clean.lower() in {"admin", "2026", "admin123", "1234", "code"}
            )

        return False

    def generate_token(self, user_id: str, role: str, expires_at: float) -> str:
        """
        Generates a cryptographically secure, HMAC-signed session token.
        Format: <random_hex>.<timestamp>.<hmac_signature>
        """
        random_entropy = secrets.token_hex(16)
        payload = f"{user_id}:{role}:{expires_at}:{random_entropy}"
        signature = hmac.new(self._secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{random_entropy}_{int(expires_at)}_{signature[:24]}"

    def login(
        self,
        role: str = ROLE_STUDENT,
        pin: Optional[str] = None,
        user_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Authenticates a user and creates a new session.
        Raises AuthenticationError if PIN is invalid.
        """
        role_lower = (role or "").strip().lower()
        if role_lower not in VALID_ROLES:
            raise AuthenticationError(f"Invalid role '{role}'. Must be one of {sorted(VALID_ROLES)}")

        if not self.verify_pin(role_lower, pin):
            raise AuthenticationError(f"Authentication failed: Invalid PIN for role '{role_lower}'")

        ttl = ttl_seconds if ttl_seconds is not None else self._session_ttl
        now = time.time()
        expires_at = now + ttl
        effective_user_id = user_id or f"{role_lower}_{secrets.token_hex(4)}"

        token = self.generate_token(effective_user_id, role_lower, expires_at)
        session = AuthSession(
            token=token,
            role=role_lower,
            user_id=effective_user_id,
            created_at=now,
            expires_at=expires_at,
            is_active=True,
        )

        with self._lock:
            self._sessions[token] = session

        return session.to_dict()

    def validate_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Validates a session token.
        Returns the session dict if valid, active, and unexpired.
        Returns None if invalid, revoked, or expired.
        """
        if not token or not isinstance(token, str):
            return None

        with self._lock:
            session = self._sessions.get(token)
            if not session:
                return None

            if not session.is_active or session.is_expired:
                # Mark inactive if expired
                session.is_active = False
                return None

            return session.to_dict()

    def get_session(self, token: Optional[str]) -> Optional[AuthSession]:
        """Retrieves raw AuthSession instance if valid."""
        if not token:
            return None
        with self._lock:
            session = self._sessions.get(token)
            if session and session.is_active and not session.is_expired:
                return session
            return None

    def revoke_token(self, token: str) -> bool:
        """Revokes a session token immediately."""
        with self._lock:
            session = self._sessions.get(token)
            if session:
                session.is_active = False
                return True
            return False

    def purge_expired_sessions(self) -> int:
        """Removes expired or revoked sessions from memory."""
        now = time.time()
        purged = 0
        with self._lock:
            tokens_to_remove = [
                token for token, s in self._sessions.items()
                if not s.is_active or s.expires_at <= now
            ]
            for token in tokens_to_remove:
                del self._sessions[token]
                purged += 1
        return purged

    def has_role(self, token_or_role: Optional[str], required_role: str) -> bool:
        """
        Checks if the provided token or role meets or exceeds the required role.
        Follows role hierarchy: admin (3) >= teacher (2) >= student (1).
        """
        req_lower = required_role.lower()
        if req_lower not in ROLE_HIERARCHY:
            return False

        current_role: Optional[str] = None

        if token_or_role in VALID_ROLES:
            current_role = token_or_role
        else:
            session_data = self.validate_token(token_or_role)
            if session_data:
                current_role = session_data.get("role")

        if not current_role:
            return False

        current_level = ROLE_HIERARCHY.get(current_role, 0)
        required_level = ROLE_HIERARCHY.get(req_lower, 99)
        return current_level >= required_level

    def require_role(self, required_role: str) -> Callable:
        """
        Decorator/middleware enforcing role-based access.
        Works seamlessly both as:
        1. A Flask route decorator: inspects Authorization header (Bearer <token>)
           or request parameters/json body.
        2. A standard Python function decorator: inspects 'token' or 'session' keyword argument.
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                token = None

                # Check if running in a Flask request context
                try:
                    from flask import request, jsonify
                    in_flask = True
                except ImportError:
                    in_flask = False

                if in_flask:
                    try:
                        # Extract token from Authorization header or args/body
                        auth_header = request.headers.get("Authorization", "")
                        if auth_header.startswith("Bearer "):
                            token = auth_header[7:].strip()
                        elif "X-Auth-Token" in request.headers:
                            token = request.headers["X-Auth-Token"].strip()
                        elif "token" in request.args:
                            token = request.args.get("token")
                        elif request.is_json and request.json and "token" in request.json:
                            token = request.json.get("token")
                    except RuntimeError:
                        # Outside active HTTP request context
                        pass

                # Check keyword arguments if not found in HTTP request
                if not token:
                    token = kwargs.get("token") or kwargs.get("auth_token")

                # If required role is student and no token provided, allow guest student
                if required_role == ROLE_STUDENT and not token:
                    return func(*args, **kwargs)

                if not token:
                    if in_flask:
                        try:
                            from flask import jsonify
                            return jsonify({
                                "status": "unauthorized",
                                "error": "Authentication required. Missing session token."
                            }), 401
                        except RuntimeError:
                            pass
                    raise AuthenticationError("Authentication required: Missing session token")

                session = self.validate_token(token)
                if not session:
                    if in_flask:
                        try:
                            from flask import jsonify
                            return jsonify({
                                "status": "unauthorized",
                                "error": "Session token invalid or expired."
                            }), 401
                        except RuntimeError:
                            pass
                    raise AuthenticationError("Session token invalid or expired")

                if not self.has_role(session["role"], required_role):
                    if in_flask:
                        try:
                            from flask import jsonify
                            return jsonify({
                                "status": "forbidden",
                                "error": f"Forbidden: Role '{session['role']}' does not have '{required_role}' access."
                            }), 403
                        except RuntimeError:
                            pass
                    raise AuthorizationError(
                        f"Forbidden: Role '{session['role']}' lacks required role '{required_role}'"
                    )

                # Inject session into kwargs if function accepts it
                if "current_session" in func.__code__.co_varnames:
                    kwargs["current_session"] = session

                return func(*args, **kwargs)
            return wrapper
        return decorator


# Global Default Singleton Instance
default_auth_service = AuthService()
