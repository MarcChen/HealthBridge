#!/usr/bin/env python3
"""Garmin Connect Token Retriever for HealthBridge.

Allows users to log in interactively, handle MFA, and extract their session
tokens for use in non-interactive environments (CI/CD like GitHub Actions).
"""

import getpass
import json
import sys
from pathlib import Path

from garminconnect import Garmin


def main():
    print("=" * 60)
    print("        Garmin Connect Token Retriever for HealthBridge       ")
    print("=" * 60)
    print("This script will log in to Garmin Connect, handle MFA, and retrieve")
    print("the session tokens for use in CI environments (e.g. GitHub Actions).")
    print()

    email = input("Enter Garmin Connect Email: ").strip()
    if not email:
        print("[-] Email cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Enter Garmin Connect Password: ").strip()
    if not password:
        print("[-] Password cannot be empty.")
        sys.exit(1)

    is_cn_str = (
        input("Are you using a Garmin Connect China account? (y/N): ").strip().lower()
    )
    is_cn = is_cn_str in ("y", "yes")

    print("\n[*] Logging in to Garmin Connect to retrieve token...")

    # We will write the token to a temporary location to read it, then clean it up
    temp_dir = Path("./.temp_tokenstore")
    temp_dir.mkdir(exist_ok=True)
    token_file = temp_dir / "garmin_tokens.json"

    def mfa_prompt() -> str:
        print("\n" + "=" * 50)
        print(" Garmin Connect Multi-Factor Authentication Required ")
        print("=" * 50)
        code = input("Enter the MFA code sent to your email/phone: ").strip()
        return code

    try:
        client = Garmin(
            email=email, password=password, is_cn=is_cn, prompt_mfa=mfa_prompt
        )
        client.login(str(token_file))
        print("[+] Authentication successful!")

        if not token_file.exists():
            print("[-] Error: Token file was not created by garminconnect library.")
            sys.exit(1)

        token_data = token_file.read_text(encoding="utf-8")

        # Verify it is valid JSON
        json.loads(token_data)

        print("\n" + "=" * 60)
        print(" YOUR GARMIN_TOKEN (JSON FORMAT):")
        print("=" * 60)
        print(token_data)
        print("=" * 60)
        print()
        print("You can copy the raw JSON line above and set it as:")
        print("  - GARMIN_TOKEN environment variable in CI")
        print("  - GARMIN_TOKEN repository secret in GitHub Settings")
        print()

        # Ask to save to .env
        save_to_env = (
            input("Would you like to save this token to your local .env file? (y/N): ")
            .strip()
            .lower()
        )
        if save_to_env in ("y", "yes"):
            env_path = Path(".env")
            env_content = ""
            if env_path.exists():
                env_content = env_path.read_text(encoding="utf-8")

            # Check if GARMIN_TOKEN already exists in .env, replace or append
            lines = env_content.splitlines()

            # Comment out legacy credentials for security
            cleaned_lines = []
            for line in lines:
                if line.startswith("GARMIN_EMAIL=") or line.startswith(
                    "GARMIN_PASSWORD="
                ):
                    cleaned_lines.append(
                        f"# {line} (removed for security - use GARMIN_TOKEN instead)"
                    )
                else:
                    cleaned_lines.append(line)
            lines = cleaned_lines

            token_line_index = -1
            for idx, line in enumerate(lines):
                if line.startswith("GARMIN_TOKEN="):
                    token_line_index = idx
                    break

            new_line = f"GARMIN_TOKEN={token_data}"
            if token_line_index != -1:
                lines[token_line_index] = new_line
            else:
                lines.append("")
                lines.append(
                    "# Garmin Connect Token for CI usage (retrieved via script)"
                )
                lines.append(new_line)

            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print("[+] Successfully saved GARMIN_TOKEN to .env!")

    except Exception as e:
        print(f"\n[-] Authentication failed: {e}")
        sys.exit(1)
    finally:
        # Clean up the temporary token file and folder
        if token_file.exists():
            token_file.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()


if __name__ == "__main__":
    main()
