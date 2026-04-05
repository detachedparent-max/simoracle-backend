"""
API key authentication and rate limiting for SimOracle
Handles free tier generation, validation, and rate limit enforcement
"""
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, Header
from database.schema import get_db_connection

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages API key generation, validation, and rate limiting"""

    RATE_LIMIT_REQUESTS = 50  # Free tier: 50 requests/day
    RATE_LIMIT_PERIOD_HOURS = 24
    FREE_TIER_EXPIRY_DAYS = 30

    @staticmethod
    def generate_api_key(email: str, tier: str = "free") -> str:
        """
        Generate a new API key for user
        Format: sk_free_<random_32_chars> or sk_pro_<random_32_chars>
        """
        prefix = f"sk_{tier}_"
        random_part = secrets.token_urlsafe(32)
        api_key = prefix + random_part
        return api_key

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash API key for secure storage in database
        Never store plain API keys
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def create_api_key(email: str, tier: str = "free") -> dict:
        """
        Create and store a new API key in database
        Returns: dict with api_key, tier, rate_limit, expires_in_days
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if table exists, create if not
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                api_key_hash TEXT NOT NULL,
                tier TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                is_active BOOLEAN DEFAULT 1,
                rate_limit_requests INTEGER DEFAULT 50,
                rate_limit_period_hours INTEGER DEFAULT 24
            )
            """)

            # Check if API usage table exists
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id TEXT PRIMARY KEY,
                api_key_hash TEXT NOT NULL,
                endpoint TEXT,
                method TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (api_key_hash) REFERENCES api_keys(api_key_hash)
            )
            """)

            api_key = APIKeyManager.generate_api_key(email, tier)
            key_hash = APIKeyManager.hash_api_key(api_key)
            key_id = f"key_{secrets.token_hex(8)}"

            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=APIKeyManager.FREE_TIER_EXPIRY_DAYS)
            ).isoformat()

            cursor.execute("""
            INSERT INTO api_keys
            (id, email, api_key_hash, tier, expires_at, rate_limit_requests, rate_limit_period_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                key_id,
                email,
                key_hash,
                tier,
                expires_at,
                APIKeyManager.RATE_LIMIT_REQUESTS,
                APIKeyManager.RATE_LIMIT_PERIOD_HOURS,
            ))

            conn.commit()
            conn.close()

            logger.info(f"Created {tier} API key for {email}")

            return {
                "api_key": api_key,
                "tier": tier,
                "rate_limit": APIKeyManager.RATE_LIMIT_REQUESTS,
                "rate_period": "day",
                "expires_in_days": APIKeyManager.FREE_TIER_EXPIRY_DAYS,
            }
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise HTTPException(status_code=500, detail="Failed to create API key")

    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, Optional[dict]]:
        """
        Validate API key and return key metadata
        Returns: (is_valid, key_metadata)
        """
        try:
            key_hash = APIKeyManager.hash_api_key(api_key)
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
            SELECT id, email, tier, created_at, expires_at, is_active,
                   rate_limit_requests, rate_limit_period_hours
            FROM api_keys
            WHERE api_key_hash = ?
            """, (key_hash,))

            result = cursor.fetchone()
            conn.close()

            if not result:
                return False, None

            key_data = dict(result)

            # Check if key is active
            if not key_data.get("is_active"):
                return False, None

            # Check if key has expired
            expires_at = key_data.get("expires_at")
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now(timezone.utc) > expires_dt:
                    return False, None

            return True, key_data

        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False, None

    @staticmethod
    def check_rate_limit(api_key_hash: str) -> Tuple[bool, dict]:
        """
        Check if API key has exceeded rate limit
        Returns: (is_allowed, rate_limit_info)
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get rate limit config for this key
            cursor.execute("""
            SELECT rate_limit_requests, rate_limit_period_hours
            FROM api_keys
            WHERE api_key_hash = ?
            """, (api_key_hash,))

            result = cursor.fetchone()
            if not result:
                return False, {}

            rate_limit_requests = result[0]
            rate_limit_period_hours = result[1]

            # Count requests in the current period
            cutoff_time = (
                datetime.now(timezone.utc) - timedelta(hours=rate_limit_period_hours)
            ).isoformat()

            cursor.execute("""
            SELECT COUNT(*) as request_count
            FROM api_usage
            WHERE api_key_hash = ? AND timestamp > ?
            """, (api_key_hash, cutoff_time))

            usage = cursor.fetchone()
            request_count = usage[0] if usage else 0
            conn.close()

            is_allowed = request_count < rate_limit_requests
            remaining = max(0, rate_limit_requests - request_count)

            return is_allowed, {
                "limit": rate_limit_requests,
                "used": request_count,
                "remaining": remaining,
                "reset_hours": rate_limit_period_hours,
            }

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, {}  # Fail open to prevent blocking

    @staticmethod
    def log_api_request(api_key_hash: str, endpoint: str, method: str) -> None:
        """Log API request for rate limiting and analytics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            request_id = f"req_{secrets.token_hex(8)}"
            cursor.execute("""
            INSERT INTO api_usage (id, api_key_hash, endpoint, method)
            VALUES (?, ?, ?, ?)
            """, (request_id, api_key_hash, endpoint, method))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log API request: {e}")


async def validate_bearer_token(authorization: Optional[str] = Header(None)) -> Tuple[bool, Optional[dict]]:
    """
    FastAPI dependency to validate Bearer token from Authorization header
    Usage: async def my_endpoint(key_data = Depends(validate_bearer_token))
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid Authorization header format")

        api_key = parts[1]
        is_valid, key_data = APIKeyManager.validate_api_key(api_key)

        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")

        # Check rate limit
        key_hash = APIKeyManager.hash_api_key(api_key)
        is_allowed, rate_info = APIKeyManager.check_rate_limit(key_hash)

        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Free tier: 50 requests/day",
                headers={"Retry-After": "86400"},
            )

        # Log the request
        APIKeyManager.log_api_request(key_hash, "", "")

        return key_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bearer token validation error: {e}")
        raise HTTPException(status_code=401, detail="Invalid API key")
