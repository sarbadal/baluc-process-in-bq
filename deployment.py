"""Deploy this Cloud Function using configuration from an env file."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path


RESERVED_DEPLOY_KEYS = {
    "FUNCTION_NAME",
    "RUNTIME",
    "REGION",
    "SOURCE",
    "ENTRY_POINT",
    "ALLOW_UNAUTHENTICATED",
    "GEN2",
    "PROJECT_ID",
    "GOOGLE_CLOUD_PROJECT",
    "SERVICE_ACCOUNT",
    "MEMORY",
    "TIMEOUT",
    "MAX_INSTANCES",
    "MIN_INSTANCES",
    "INGRESS_SETTINGS",
    "VPC_CONNECTOR",
    "EGRESS_SETTINGS",
    "APP_ENV_KEYS",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy process_in_bq Cloud Function")
    parser.add_argument(
        "--env-file",
        default="deploy.env",
        help="Path to env file with deploy and app settings (default: deploy.env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the gcloud command without executing it",
    )
    return parser.parse_args()


def parse_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")

    env: dict[str, str] = {}
    for line_no, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise ValueError(f"Invalid env line {line_no}: {raw_line}")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Invalid env key on line {line_no}: {key}")

        if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
            value = value[1:-1]

        env[key] = value

    return env


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def pick_app_env_vars(env: dict[str, str]) -> dict[str, str]:
    app_env_keys = env.get("APP_ENV_KEYS", "").strip()
    if app_env_keys:
        keys = [item.strip() for item in app_env_keys.split(",") if item.strip()]
        missing = [key for key in keys if key not in env]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"APP_ENV_KEYS contains missing keys: {missing_text}")
        return {key: env[key] for key in keys}

    return {key: value for key, value in env.items() if key not in RESERVED_DEPLOY_KEYS}


def build_command(env: dict[str, str]) -> list[str]:
    function_name = env.get("FUNCTION_NAME", "process-in-bq").strip()
    runtime = env.get("RUNTIME", "python312").strip()
    region = env.get("REGION", "us-central1").strip()
    source = env.get("SOURCE", ".").strip()
    entry_point = env.get("ENTRY_POINT", "process_report_request").strip()

    if not function_name:
        raise ValueError("FUNCTION_NAME cannot be empty")
    if not runtime:
        raise ValueError("RUNTIME cannot be empty")
    if not region:
        raise ValueError("REGION cannot be empty")
    if not source:
        raise ValueError("SOURCE cannot be empty")
    if not entry_point:
        raise ValueError("ENTRY_POINT cannot be empty")

    command: list[str] = [
        "gcloud",
        "functions",
        "deploy",
        function_name,
    ]

    if parse_bool(env.get("GEN2"), True):
        command.append("--gen2")

    command.extend(
        [
            "--runtime",
            runtime,
            "--region",
            region,
            "--source",
            source,
            "--entry-point",
            entry_point,
            "--trigger-http",
        ]
    )

    if parse_bool(env.get("ALLOW_UNAUTHENTICATED"), True):
        command.append("--allow-unauthenticated")

    project = (env.get("PROJECT_ID", "").strip() or env.get("GOOGLE_CLOUD_PROJECT", "").strip())
    if project:
        command.extend(["--project", project])

    app_env = pick_app_env_vars(env)
    if app_env:
        env_arg = ",".join(f"{key}={value}" for key, value in sorted(app_env.items()))
        command.extend(["--set-env-vars", env_arg])

    optional_map = {
        "SERVICE_ACCOUNT": "--service-account",
        "MEMORY": "--memory",
        "TIMEOUT": "--timeout",
        "MAX_INSTANCES": "--max-instances",
        "MIN_INSTANCES": "--min-instances",
        "INGRESS_SETTINGS": "--ingress-settings",
        "VPC_CONNECTOR": "--vpc-connector",
        "EGRESS_SETTINGS": "--egress-settings",
    }
    for env_key, flag in optional_map.items():
        value = env.get(env_key, "").strip()
        if value:
            command.extend([flag, value])

    return command


def main() -> int:
    args = parse_args()
    env_path = Path(args.env_file)

    try:
        env = parse_env_file(env_path)
        command = build_command(env)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    printable = " ".join(shlex.quote(part) for part in command)
    print(f"Deploy command:\n{printable}")

    if args.dry_run:
        return 0

    try:
        completed = subprocess.run(command, check=False)
    except FileNotFoundError:
        print("Error: gcloud command not found. Install Google Cloud SDK and authenticate first.", file=sys.stderr)
        return 127

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
