import os
import pytest

from app.core.config import validate_security_settings, settings


def test_validate_security_settings_with_safe_values(monkeypatch):
    """Test that validate_security_settings passes when safe values are set."""
    # Set safe environment variables before importing/initializing settings
    monkeypatch.setenv("JWT_SECRET", "a-safe-jwt-secret-that-is-long-enough")
    monkeypatch.setenv("ENCRYPTION_KEY", "a-safe-encryption-key-that-is-long-enough")

    # Re-import or re-validate - but since Settings is a singleton,
    # we need to reset it. We'll test the function directly with overridden settings.
    # The function reads from the global settings object, so we monkeypatch it.
    import app.core.config as config_mod

    original_jwt = config_mod.settings.JWT_SECRET
    original_enc = config_mod.settings.ENCRYPTION_KEY

    try:
        config_mod.settings.JWT_SECRET = "a-safe-jwt-secret-that-is-long-enough"
        config_mod.settings.ENCRYPTION_KEY = "a-safe-encryption-key-that-is-long-enough"

        # This should not raise SystemExit
        validate_security_settings()
    finally:
        config_mod.settings.JWT_SECRET = original_jwt
        config_mod.settings.ENCRYPTION_KEY = original_enc


def test_validate_security_settings_fails_on_insecure_defaults():
    """Test that validate_security_settings fails when defaults are used."""
    import app.core.config as config_mod

    original_jwt = config_mod.settings.JWT_SECRET
    original_enc = config_mod.settings.ENCRYPTION_KEY

    try:
        # Set insecure defaults - should cause validation to fail
        config_mod.settings.JWT_SECRET = "change-me-in-production"
        config_mod.settings.ENCRYPTION_KEY = "change-me-use-fernet-key"

        with pytest.raises(SystemExit) as exc_info:
            validate_security_settings()

        assert exc_info.value.code == 1
    finally:
        config_mod.settings.JWT_SECRET = original_jwt
        config_mod.settings.ENCRYPTION_KEY = original_enc