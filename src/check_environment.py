"""Verify the recorded Python and pinned packages without modifying the environment."""

import argparse
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def check_environment(development=False):
    expected_python = (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()
    actual_python = platform.python_version()
    errors = []
    if actual_python != expected_python:
        errors.append(f"python: expected {expected_python}, found {actual_python}")
    files = [PROJECT_ROOT / "requirements.txt"]
    if development:
        files.append(PROJECT_ROOT / "requirements-dev.txt")
    packages = {}
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-r ")):
                continue
            name, expected = line.split("==")
            try:
                actual = version(name)
            except PackageNotFoundError:
                actual = "not installed"
            packages[name] = actual
            if actual != expected:
                errors.append(f"{name}: expected {expected}, found {actual}")
    if errors:
        raise ValueError("Environment differs from the validated versions: " + "; ".join(errors))
    return {"python": actual_python, "packages": packages, "development": development}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(check_environment(args.development), indent=2))
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
