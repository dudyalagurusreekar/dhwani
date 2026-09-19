"""
Unit tests for cybersecurity/api_security (Module 1).
Validates authentication, RBAC authorization, and rate limiting.
"""

from __future__ import annotations

import time
import unittest
from datetime import timedelta

from fastapi import HTTPException

from cybersecurity.api_security.authentication import (
    AuthenticationError,
    create_access_token,
    decode_access_token,
)
from cybersecurity.api_security.authorization import (
    Permission,
    Role,
    require_permission,
    require_role,
    user_has_permission,
)
from cybersecurity.api_security.rate_limiter import SlidingWindowRateLimiter


class TestAPISecurity(unittest.TestCase):

    def test_jwt_token_generation_and_validation(self):
        token = create_access_token(
            subject="client_node_101",
            role=Role.CLIENT.value,
            scopes=["audio:analyze"],
            expires_delta=timedelta(minutes=15),
        )
        self.assertIsInstance(token, str)

        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "client_node_101")
        self.assertEqual(payload["role"], "client")
        self.assertIn("audio:analyze", payload["scopes"])
        self.assertEqual(payload["iss"], "dhwani-auth-service")

    def test_expired_token_rejection(self):
        expired_token = create_access_token(
            subject="expired_user",
            role=Role.CLIENT.value,
            expires_delta=timedelta(seconds=-10),
        )
        with self.assertRaises(AuthenticationError) as ctx:
            decode_access_token(expired_token)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_tampered_token_rejection(self):
        valid_token = create_access_token(subject="valid_user", role=Role.CLIENT.value)
        # Flip characters in the signature segment
        parts = valid_token.split(".")
        tampered_sig = parts[2][:-4] + ("AAAA" if parts[2][-4:] != "AAAA" else "BBBB")
        tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

        with self.assertRaises(AuthenticationError):
            decode_access_token(tampered_token)

    def test_rbac_client_permissions(self):
        client_user = {"sub": "user1", "role": Role.CLIENT.value, "scopes": []}
        self.assertTrue(user_has_permission(client_user, Permission.AUDIO_ANALYZE.value))
        self.assertFalse(user_has_permission(client_user, Permission.AUDIT_VERIFY.value))
        self.assertFalse(user_has_permission(client_user, Permission.AUDIO_DECRYPT.value))

    def test_rbac_admin_permissions(self):
        admin_user = {"sub": "admin1", "role": Role.ADMIN.value, "scopes": []}
        self.assertTrue(user_has_permission(admin_user, Permission.AUDIO_ANALYZE.value))
        self.assertTrue(user_has_permission(admin_user, Permission.AUDIT_VERIFY.value))
        self.assertTrue(user_has_permission(admin_user, Permission.AUDIO_DECRYPT.value))
        self.assertTrue(user_has_permission(admin_user, Permission.ADMIN_ALL.value))

    def test_require_role_blocks_unauthorized_actor(self):
        import asyncio

        verifier = require_role(Role.ADMIN)
        client_user = {"sub": "user_client", "role": Role.CLIENT.value}

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verifier(client_user))
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Forbidden", ctx.exception.detail)

    def test_require_role_allows_authorized_actor(self):
        import asyncio

        verifier = require_role(Role.CLIENT, Role.ANALYST)
        client_user = {"sub": "user_client", "role": Role.CLIENT.value}

        result = asyncio.run(verifier(client_user))
        self.assertEqual(result["sub"], "user_client")

    def test_require_permission_blocks_missing_permission(self):
        import asyncio

        verifier = require_permission(Permission.AUDIT_VERIFY)
        client_user = {"sub": "client1", "role": Role.CLIENT.value, "scopes": []}

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(verifier(client_user))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_sliding_window_rate_limiter_allows_and_decrements(self):
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10.0)

        allowed1, stats1 = limiter.is_allowed("ip_1.2.3.4")
        self.assertTrue(allowed1)
        self.assertEqual(stats1["remaining"], 2)

        allowed2, stats2 = limiter.is_allowed("ip_1.2.3.4")
        self.assertTrue(allowed2)
        self.assertEqual(stats2["remaining"], 1)

        allowed3, stats3 = limiter.is_allowed("ip_1.2.3.4")
        self.assertTrue(allowed3)
        self.assertEqual(stats3["remaining"], 0)

        # 4th request exceeds rate limit
        allowed4, stats4 = limiter.is_allowed("ip_1.2.3.4")
        self.assertFalse(allowed4)
        self.assertEqual(stats4["remaining"], 0)
        self.assertGreater(stats4["retry_after"], 0)

    def test_rate_limiter_check_or_raise(self):
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=5.0)
        limiter.check_or_raise("client_test")

        with self.assertRaises(HTTPException) as ctx:
            limiter.check_or_raise("client_test")
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Rate limit exceeded", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
