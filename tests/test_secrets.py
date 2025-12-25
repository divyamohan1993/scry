import subprocess
import json
import os
import sys
import pytest

# Determine project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_no_secrets_detected():
    """
    Runs detect-secrets on the repository and fails if any potential secrets are found.
    This ensures no sensitive data is committed.
    """
    # Path to the executable in the venv
    if sys.platform == "win32":
        executable = os.path.join(PROJECT_ROOT, "_runtime", "venv", "Scripts", "detect-secrets.exe")
    else:
        executable = os.path.join(PROJECT_ROOT, "_runtime", "venv", "bin", "detect-secrets")

    if not os.path.exists(executable):
        pytest.skip(f"detect-secrets not found at {executable}")

    # Run the scan
    # We scan the project root
    # We explicitly exclude the _runtime directory and .git to be safe, 
    # though .gitignore handling usually covers it.
    try:
        # construct command
        cmd = [
            executable,
            "scan",
            PROJECT_ROOT,
            "--exclude-files", "_runtime",
            "--exclude-files", ".git",
            "--exclude-files", ".pytest_cache",
            "--exclude-files", "__pycache__",
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't throw error on non-zero, we parse output
            cwd=PROJECT_ROOT
        )
        
        if result.returncode != 0:
             pytest.fail(f"detect-secrets failed to run: {result.stderr}")

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Failed to parse detect-secrets output: {result.stdout}")

        # Check for results
        # The structure usually has a "results" key which is a dict mapping filename to list of secrets
        secrets_found = data.get("results", {})
        
        # If dictionary is not empty, secrets were found
        if secrets_found:
            # Format a nice error message
            msg = "Sensitive data detected in the following files:\n"
            for filename, secrets in secrets_found.items():
                msg += f"\nFile: {filename}\n"
                for secret in secrets:
                    line = secret.get('line_number')
                    type_ = secret.get('type')
                    msg += f"  - Line {line}: {type_}\n"
            
            pytest.fail(msg)

    except Exception as e:
        pytest.fail(f"An error occurred during security scan: {e}")
