"""Security validation tests for settings."""

import os
import subprocess
import sys

# Set secure environment variables before importing the app module
# to avoid SystemExit from validate_security_settings() with insecure defaults
os.environ["JWT_SECRET"] = "secure-jwt-secret-that-is-at-least-32-characters-long"
os.environ["ENCRYPTION_KEY"] = "secure-encryption-key-that-is-32-bytes-fernet"

# Ensure the app directory is in the Python path
if "apps/api" not in sys.path:
    sys.path.insert(0, "apps/api")

# Now import after setting env vars
from app.core.config import validate_security_settings


def test_validate_security_settings_with_safe_values():
    """Verify that validate_security_settings() passes with safe (non-default) values."""
    validate_security_settings()


def test_validate_security_settings_fails_on_insecure_defaults():
    """Verify that validate_security_settings() raises SystemExit with insecure defaults.

    This test uses a subprocess because module-level env var changes persist across tests.
    """
    env = os.environ.copy()
    env["JWT_SECRET"] = "change-me-in-production"
    env["ENCRYPTION_KEY"] = "change-me-use-fernet-key"
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "apps/api")
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import validate_security_settings; validate_security_settings()"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0, (
        f"Expected SystemExit(1) for insecure defaults, got {result.returncode}. "
        f"stderr: {result.stderr}"
    )
    assert "SECURITY VALIDATION FAILED" in result.stderr