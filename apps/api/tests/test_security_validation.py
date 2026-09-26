"""
Regression test for security settings validation.

Locks in the current behavior: validate_security_settings() must pass
when safe (non-default) JWT_SECRET and ENCRYPTION_KEY values are set,
and must raise SystemExit(1) when insecure defaults are used.
"""
import os

import pytest


def _reimport_config():
    """Force re-import of app.core.config to get fresh Settings instance."""
    # Remove the module from cache so it gets reimported fresh
    import importlib
    import app.core.config as config_mod
    importlib.reload(config_mod)
    return config_mod.validate_security_settings, config_mod.settings


def test_validate_security_settings_passes_with_safe_values(monkeypatch):
    """verify that validate_security_settings() does NOT raise SystemExit
    when JWT_SECRET and ENCRYPTION_KEY are set to safe values."""
    os.environ["JWT_SECRET"] = "safe-jwt-secret-change-me"
    os.environ["ENCRYPTION_KEY"] = "safe-encryption-key-change-me"

    validate_security_settings, settings = _reimport_config()

    # This should NOT raise SystemExit
    try:
        validate_security_settings()
    except SystemExit as e:
        raise AssertionError(
            "validate_security_settings() raised SystemExit with safe values. "
            "This test locks in the expected behavior."
        ) from e


def test_validate_security_settings_fails_with_insecure_defaults(monkeypatch):
    """verify that validate_security_settings() raises SystemExit(1)
    when JWT_SECRET or ENCRYPTION_KEY are at insecure defaults."""
    os.environ["JWT_SECRET"] = "change-me-in-production"
    os.environ["ENCRYPTION_KEY"] = "change-me-use-fernet-key"

    validate_security_settings, settings = _reimport_config()

    # This SHOULD raise SystemExit(1)
    try:
        validate_security_settings()
        raise AssertionError(
            "validate_security_settings() should have raised SystemExit(1) "
            "with insecure defaults. This test locks in the expected behavior."
        )
    except SystemExit as e:
        assert e.code == 1, (
            f"Expected SystemExit(1), got SystemExit({e.code})"
        )