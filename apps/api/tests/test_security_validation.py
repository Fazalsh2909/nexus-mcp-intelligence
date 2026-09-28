"""Regression tests for security settings validation.

Environment variables MUST be set BEFORE importing app.core.config,
because Settings() is created at module import time (in config.py)
and validate_security_settings() is called at app import time (in main.py).
"""

import os
import pytest


# Set env vars BEFORE any app imports so pydantic_settings picks them up
os.environ["JWT_SECRET"] = "safe-jwt-secret-that-is-long-enough"
os.environ["ENCRYPTION_KEY"] = "safe-encryption-key-that-is-long-enough"


def test_validate_security_settings_with_safe_values():
    """Test that validate_security_settings() passes when safe values are set."""
    from app.core.config import validate_security_settings

    # This should not raise SystemExit
    validate_security_settings()


def test_validate_security_settings_fails_on_insecure_defaults():
    """Test that validate_security_settings() fails when insecure defaults are used."""
    # Remove the safe env vars so the defaults (insecure) are used
    os.environ.pop("JWT_SECRET", None)
    os.environ.pop("ENCRYPTION_KEY", None)

    # Now import config - it will use the insecure default values
    from app.core.config import validate_security_settings

    try:
        with pytest.raises(SystemExit) as exc_info:
            validate_security_settings()
        assert exc_info.value.code == 1
    finally:
        # Clean up env vars
        os.environ.pop("JWT_SECRET", None)
        os.environ.pop("ENCRYPTION_KEY", None)