"""Regression tests for security settings validation.

These tests verify that validate_security_settings() behaves correctly:
- Passes when safe (non-default) values are set for JWT_SECRET and ENCRYPTION_KEY
- Fails when insecure default values are used
"""

import os
import sys

# Set safe environment variables before importing the app module
# to avoid SystemExit(1) at import time
os.environ["JWT_SECRET"] = "safe-jwt-secret-that-is-long-enough"
os.environ["ENCRYPTION_KEY"] = "safe-encryption-key-that-is-long-enough"

# Now import the app module (validate_security_settings is called at module level)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.config import validate_security_settings


def test_validate_security_settings_with_safe_values():
    """Test that validate_security_settings passes when safe values are set."""
    # Should not raise SystemExit
    validate_security_settings()


def test_validate_security_settings_fails_on_insecure_defaults():
    """Test that validate_security_settings fails when insecure defaults are used.

    This test temporarily sets insecure values to verify the validation
    correctly catches them. We re-import the config module to get fresh state.
    """
    # Temporarily set insecure defaults
    os.environ["JWT_SECRET"] = "change-me-in-production"
    os.environ["ENCRYPTION_KEY"] = "change-me-use-fernet-key"

    # Need to reimport to get fresh state since config is loaded at module level
    import importlib

    from app.core import config

    # Reset the settings instance to pick up new env vars
    importlib.reload(config)

    try:
        config.validate_security_settings()
        assert False, "Expected SystemExit(1) for insecure defaults"
    except SystemExit as e:
        assert e.code == 1
