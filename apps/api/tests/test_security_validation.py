"""
Regression tests for security settings validation.

These tests verify that validate_security_settings() behaves correctly:
- Passes when safe (non-default) values are set for JWT_SECRET and ENCRYPTION_KEY
- Fails when insecure default values are used
"""

import os
import subprocess

import pytest


def _run_validate_with_env(env_vars: dict) -> int:
    """Run validate_security_settings in a subprocess with given env vars.

    This avoids pytest's module import caching issues where env vars from
    one test persist into another.
    """
    env = {**os.environ, **env_vars}
    # Set PYTHONPATH to include the apps/api directory so "app" module is findable
    env["PYTHONPATH"] = "apps/api"

    # Build script with env vars as a dict for os.environ.update()
    env_repr = str(env_vars)
    script = f"""import os
env_dict = {env_repr}
os.environ.update(env_dict)
from app.core.config import validate_security_settings
validate_security_settings()
print("VALIDATION_PASSED")
"""

    result = subprocess.run(
        [os.sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        return 1
    return 0


@pytest.mark.parametrize(
    "env_vars, expected_pass",
    [
        # Test 1: Safe values should pass validation
        (
            {
                "JWT_SECRET": "a-very-secure-jwt-secret-that-is-definitely-not-the-default",
                "ENCRYPTION_KEY": "a-very-encryption-key-also-not-the-default",
            },
            True,
        ),
        # Test 2: Insecure defaults should fail validation
        (
            {
                "JWT_SECRET": "change-me-in-production",
                "ENCRYPTION_KEY": "change-me-use-fernet-key",
            },
            False,
        ),
    ],
)
def test_validate_security_settings(env_vars, expected_pass):
    """Test validate_security_settings with various env var values.

    The validate_security_settings() function is called at module import
    time in main.py:12, so we use a subprocess to avoid pytest's module
    caching issues.
    """
    result = _run_validate_with_env(env_vars)
    passed = result == 0

    if expected_pass:
        assert passed, f"Expected validation to pass with {env_vars}, but it failed"
    else:
        assert not passed, (
            f"Expected validation to fail with insecure defaults {env_vars}, "
            f"but it passed. This is a security issue!"
        )
