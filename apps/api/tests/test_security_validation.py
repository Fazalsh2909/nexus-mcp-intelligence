"""Regression tests for security settings validation."""

import os
import sys
import pytest


def test_validate_security_settings_with_safe_values():
    """Test that validate_security_settings() passes when safe values are set."""
    # Set safe environment variables BEFORE importing
    os.environ["JWT_SECRET"] = "safe-jwt-secret-that-is-long-enough"
    os.environ["ENCRYPTION_KEY"] = "safe-encryption-key-that-is-fernet-compatible"

    # Clear any cached module to force reimport with new env vars
    for mod in list(sys.modules.keys()):
        if "app" in mod:
            del sys.modules[mod]

    from app.core.config import validate_security_settings, settings

    # Should not raise SystemExit
    validate_security_settings()

    # Verify the settings were actually updated
    assert settings.JWT_SECRET != "change-me-in-production"
    assert settings.ENCRYPTION_KEY != "change-me-use-fernet-key"


def test_validate_security_settings_fails_on_insecure_defaults():
    """Test that validate_security_settings() fails on insecure default values."""
    # Set insecure default values
    os.environ["JWT_SECRET"] = "change-me-in-production"
    os.environ["ENCRYPTION_KEY"] = "change-me-use-fernet-key"

    # Clear any cached module to force reimport with new env vars
    for mod in list(sys.modules.keys()):
        if "app" in mod:
            del sys.modules[mod]

    # Import after setting insecure env vars - this should raise SystemExit
    from app.core.config import validate_security_settings

    with pytest.raises(SystemExit) as exc_info:
        validate_security_settings()

    # Verify the exit code is 1
    assert exc_info.value.code == 1