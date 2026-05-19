#!/usr/bin/env python3
"""setup_secrets.py.

A helper script that reads Garmin Connect credentials from the local `.env` file
and uploads them to the GitHub repository secrets using the GitHub CLI (`gh`).
"""

import subprocess
import sys
from pathlib import Path


def check_gh_cli():
    """Verify that the GitHub CLI is installed and authenticated."""
    print("[*] Verifying GitHub CLI installation...")
    try:
        res = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            print("[-] Error: 'gh' CLI is not installed or not in PATH.")
            sys.exit(1)
    except FileNotFoundError:
        print("[-] Error: 'gh' CLI is not installed or not in PATH.")
        sys.exit(1)

    print("[*] Checking GitHub CLI authentication status...")
    res = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print("[-] Error: 'gh' is not authenticated. Please run 'gh auth login' first.")
        print(res.stderr or res.stdout)
        sys.exit(1)
    print("[+] GitHub CLI is installed and authenticated.")


def load_env_secrets(env_path: Path) -> dict[str, str]:
    """Parse the .env file to extract target secrets."""
    secrets = {}
    target_keys = {
        "GARMIN_TOKEN",
        "GARMIN_IS_CN",
        "GARMIN_EMAIL",
        "GARMIN_USERNAME",
        "GARMIN_PASSWORD",
    }

    print(f"[*] Reading secrets from {env_path}...")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignore empty lines and comments
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()

                # Clean potential surrounding quotes
                if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                    val = val[1:-1]

                if key in target_keys:
                    secrets[key] = val

    return secrets


def upload_secrets(secrets: dict[str, str]):
    """Upload extracted secrets to GitHub repository secrets using 'gh secret set'."""
    has_token = "GARMIN_TOKEN" in secrets
    has_creds = (
        "GARMIN_EMAIL" in secrets or "GARMIN_USERNAME" in secrets
    ) and "GARMIN_PASSWORD" in secrets

    if not (has_token or has_creds):
        print("[-] No valid authentication configuration found in the .env file.")
        print(
            "    Please configure either GARMIN_TOKEN, or both Garmin "
            "credentials (email/username and password)."
        )
        sys.exit(1)

    print(f"[*] Found {len(secrets)} secrets to upload.")
    for key, val in secrets.items():
        print(f"[*] Syncing secret '{key}' to GitHub repository secrets...")
        try:
            # Run gh secret set <KEY> --body "<VAL>"
            subprocess.run(
                ["gh", "secret", "set", key, "--body", val],
                check=True,
                capture_output=True,
            )
            print(f"[+] Successfully uploaded '{key}'.")
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to set secret '{key}':")
            print(e.stderr.decode("utf-8") if e.stderr else str(e))
            sys.exit(1)


def main():
    print("=" * 60)
    print("           HealthBridge GitHub Secrets Sync Script         ")
    print("=" * 60)

    # 1. Verify gh CLI
    check_gh_cli()

    # 2. Locate .env file
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    if not env_path.exists():
        # Check current working directory as fallback
        env_path = Path(".env").resolve()

    if not env_path.exists():
        print(f"[-] Error: .env file not found at {env_path.parent / '.env'}.")
        print("    Please configure a '.env' file with your credentials first.")
        sys.exit(1)

    # 3. Load secrets from .env
    secrets = load_env_secrets(env_path)

    # 4. Upload secrets to GitHub
    upload_secrets(secrets)

    print("\n[+] Repository secrets are fully synced and up to date!")
    print("=" * 60)


if __name__ == "__main__":
    main()
