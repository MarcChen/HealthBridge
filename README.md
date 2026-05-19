# 🏥 HealthBridge

An elegant, modern Python repository integrating the **Garmin Connect API** with secure **Pydantic Settings** configuration, automated weight syncing, delta-based deduplication, GitHub Actions integration, and state-of-the-art Python packaging using **`uv`**, **Ruff**, and **Black**.

HealthBridge is optimized for **Python 3.13+** and incorporates modern security practices (e.g., masking credentials with Pydantic's `SecretStr`) and user-friendly CLI interaction for Multi-Factor Authentication (MFA).

---

## ✨ Features

- **⚡ Blazing Fast Setup**: Uses [uv](https://github.com/astral-sh/uv), the modern Python package installer and resolver.
- **🐍 Python 3.13+ Ready**: Pre-configured and locked to Python 3.13+ syntax and features.
- **⚖️ Automated Weight Sync & Delta Logic**: Parses, type-validates, and date-deduplicates raw weight payloads (keeping the last entry for duplicate dates). Synchronizes with Garmin Connect using a rolling delta check (past $X$ months and $Y$ points) to only upload new data points.
- **🔒 Secure Credentials**: Implements Pydantic v2 `BaseSettings` and `SecretStr` to prevent credential leakage in logs and tracebacks.
- **🔑 Session & Token Caching**: Securely caches OAuth tokens in a local `.garminconnect/` directory (gitignored by default) to bypass recurrent logins and MFA requests.
- **🚀 GitHub Actions & Dispatch Workflows**: Out-of-the-box CI/CD support for manual triggering (`workflow_dispatch`) and webhook automation (`repository_dispatch`).
- **🤖 Automatic Secrets Deployer**: Script to push credentials directly from local `.env` to GitHub repository secrets using the GitHub CLI (`gh`).
- **🧪 Robust Test Suite**: Configured with `pytest` and pre-built unit tests validating Pydantic models, defensive weight conversions, and mock syncing operations.

---

## 🏗️ Project Architecture

```
HealthBridge/
├── .garminconnect/           # Local OAuth tokens cache (Git-ignored)
├── .github/
│   └── workflows/
│       └── sync_weights.yml  # GitHub Actions weight sync workflow (manual & webhook)
├── healthbridge/             # Core library package
│   ├── __init__.py           # Package entry points & public interface
│   ├── client.py             # GarminConnect client wrapper with MFA, caching, & sync logic
│   ├── config.py             # Pydantic Settings configuration model
│   └── models.py             # Pydantic WeightPayload and WeightEntry models
├── scripts/
│   └── setup_secrets.py      # Automated .env-to-GitHub secret deployment script
├── tests/
│   └── test_sync.py          # Unit tests verifying validation, deduplication, & syncing
├── .env                      # Environment variables (Git-ignored)
├── .env.example              # Environment template file
├── .gitignore                # Standard Python, UV, and Garmin token ignores
├── main.py                   # CLI sync and demonstration entry point
├── Makefile                  # Automation commands
└── pyproject.toml            # Project metadata & pytest/Ruff/Black locked specs
```

---

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have **Python 3.13+** and **`uv`** installed on your system.

To install `uv` (if you haven't already):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Installation

Clone the repository and run the setup target:
```bash
# Setup the virtual environment and install all dependencies
make setup
```
*Behind the scenes, this executes `uv sync` to build a precise virtual environment (`.venv`) with production and development dependencies.*

### 3. Configuration

HealthBridge uses token-only authentication to prevent storing credentials in plaintext and to support non-interactive runners (like GitHub Actions) cleanly without ongoing MFA prompts.

You must run the token retriever script first to authenticate interactively and extract your token before running the main tool.

#### Step 1: Initialize environment configuration
Copy the configuration template to create your `.env` file:
```bash
cp .env.example .env
```

#### Step 2: Retrieve your Garmin token
Run the interactive token retriever script. This script will prompt you for your Garmin email, password, and the MFA code sent to your phone/email:
```bash
PYTHONPATH=. uv run python scripts/get_garmin_token.py
```

At the end of the script, press `y` to automatically save the token to your local `.env` file as `GARMIN_TOKEN`. For security, the retriever script will automatically comment out any plaintext credentials if they are present in `.env`.

Alternatively, you can manually copy the printed token JSON string and add it to your `.env` file:
```env
GARMIN_TOKEN={"oauth_token": "...", "oauth_token_secret": "..."}
GARMIN_IS_CN=False
GARMIN_TOKEN_PATH=.garminconnect/garmin_tokens.json
```


---

## 💻 CLI Usage

HealthBridge provides a unified CLI to trigger demonstrations or run automated delta-syncing using raw payloads.

### 1. Weight Delta-Syncing (JSON String)
You can directly pass a raw weight payload as a JSON string containing newline-separated values for `poids` (weights) and `date` (dates):
```bash
PYTHONPATH=. uv run python main.py --payload-json '{"poids": "74.5\n74.0\n72.7", "date": "2025-12-06\n2025-12-13\n2025-12-17"}'
```

### 2. Weight Delta-Syncing (JSON File)
Alternatively, you can load the payload from a local JSON file:
```bash
PYTHONPATH=. uv run python main.py --payload-file path/to/payload.json
```

### 3. Weight Delta-Syncing (Environment Variable)
The CLI automatically picks up the `PAYLOAD_JSON` environment variable:
```bash
export PAYLOAD_JSON='{"poids": "74.5\n74.0", "date": "2025-12-06\n2025-12-13"}'
PYTHONPATH=. uv run python main.py
```

### 4. Running the Original Daily Stats Demo
To run the original stats demonstration:
```bash
PYTHONPATH=. uv run python main.py --demo
```
*(Or simply use the shorthand: `make run`)*

---

## 🤖 GitHub Automation

### 1. Syncing Secrets from `.env` to GitHub
To secure your repository for GitHub Actions, a helper script automatically deploys the `GARMIN_TOKEN` and `GARMIN_IS_CN` variables configured in your local `.env` straight to your GitHub repository secrets:
```bash
PYTHONPATH=. uv run python scripts/setup_secrets.py
```
*Requires the GitHub CLI (`gh`) to be installed and authenticated (`gh auth login`).*

### 2. Triggering the Workflow Manually (Workflow Dispatch)
Go to the **Actions** tab of your repository on GitHub, select the **Garmin Weight Sync** workflow, and click **Run workflow**. Fill in the newline-separated weights and dates in the input fields.

### 3. Triggering the Workflow via API (Repository Dispatch)
You can easily sync weights from external scripts or webhooks by sending a Repository Dispatch event:
```bash
curl -L \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <YOUR_GITHUB_TOKEN>" \
  https://api.github.com/repos/<OWNER>/<REPO>/dispatches \
  -d '{
    "event_type": "sync-weights",
    "client_payload": {
      "poids": "74.5\n74.0\n72.7",
      "date": "2025-12-06\n2025-12-13\n2025-12-17"
    }
  }'
```

---

## 🧪 Testing

The repository uses **`pytest`** to execute a comprehensive unit test suite:
```bash
PYTHONPATH=. uv run pytest
```

---

## 🛠️ Development Workflow

The `Makefile` makes development simple and clean:

| Command | Description |
| :--- | :--- |
| `make install` | Installs all production and dev dependencies. |
| `make run` | Starts the demonstration script (`main.py` in demo mode). |
| `make lint` | Validates code standards using **Ruff**. |
| `make format` | Automatically formats the codebase using **Black** and fixes import ordering/style with **Ruff**. |
| `make clean` | Removes virtual environments and temporary caches (leaves credentials untouched). |

---

## 🛡️ License

Public Domain. Feel free to use, modify, and build upon this repository!
