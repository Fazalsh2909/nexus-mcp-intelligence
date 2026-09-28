"""Regression tests for validate_security_settings().

These tests verify that the security settings validation behaves correctly
both with safe values and insecure defaults.

NOTE: Because validate_security_settings() is called at module import time
(in apps/api/app/main.py:12), we must set environment variables BEFORE
importing the app module. Each test runs in a fresh subprocess to avoid
pytest's module caching issues.
"""

import subprocess
import sys


def test_validate_security_settings_with_safe_values():
    """Test that validate_security_settings() passes with safe values.

    This test sets JWT_SECRET and ENCRYPTION_KEY to non-default values
    before importing the app module, to verify the validation passes.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
os.environ["JWT_SECRET"] = "a-very-secure-jwt-secret-that-is-definitely-not-the-default"
os.environ["ENCRYPTION_KEY"] = "a-very-encryption-key-that-is-definitely-not-the-default"

# Now import and call the function
from app.core.config import validate_security_settings
validate_security_settings()
print("PASS: validate_security_settings passed with safe values")
""",
        ],
        cwd="apps/api",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected return code 0, got {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_validate_security_settings_fails_on_insecure_defaults():
    """Test that validate_security_settings() fails with insecure defaults.

    This test verifies that the validation raises SystemExit(1) when
    JWT_SECRET or ENCRYPTION_KEY are at their insecure default values.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
# Use the insecure default values
os.environ["JWT_SECRET"] = "change-me-in-production"
os.environ["ENCRYPTION_KEY"] = "change-me-use-fernet-key"

# Now import and call the function - this should raise SystemExit(1)
from app.core.config import validate_security_settings
validate_security_settings()
print("FAIL: validate_security_settings should have raised SystemExit(1)")
""",
        ],
        cwd="apps/api",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"Expected non-zero return code, got {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    # The function raises SystemExit(1), so the subprocess exit code should be 1
    assert result.returncode == 1, (
        f"Expected return code 1 (SystemExit), got {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
