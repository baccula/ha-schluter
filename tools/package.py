"""Build the Marketplace package from the reviewed Core implementation."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(core: Path) -> None:
    """Copy sources and bundle the standalone client until its PyPI publication."""
    source = core / "homeassistant/components/schluter"
    destination = ROOT / "custom_components/schluter"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE", destination / "LICENSE")
    shutil.copyfile(ROOT / "THIRD_PARTY.md", destination / "THIRD_PARTY.md")
    for path in source.glob("*.py"):
        destination.joinpath(path.name).write_text(
            path.read_text().replace(
                "from schluter_wifi import", "from ._vendor.schluter_wifi import"
            )
        )
    manifest = json.loads((source / "manifest.json").read_text())
    manifest.update(
        version="0.1.0rc2",
        codeowners=["@baccula"],
        requirements=[],
        documentation="https://github.com/baccula/ha-schluter",
        issue_tracker="https://github.com/baccula/ha-schluter/issues",
    )
    manifest.pop("quality_scale", None)
    manifest.pop("loggers", None)
    manifest = {
        key: manifest[key]
        for key in ["domain", "name"] + sorted(manifest.keys() - {"domain", "name"})
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    translations = destination / "translations"
    translations.mkdir(exist_ok=True)
    shutil.copyfile(source / "strings.json", translations / "en.json")
    vendor = destination / "_vendor"
    vendor.mkdir(exist_ok=True)
    (vendor / "__init__.py").write_text(
        '"""Bundled standalone dependencies; see THIRD_PARTY.md."""\n'
    )
    shutil.copytree(
        ROOT / "library/src/schluter_wifi",
        vendor / "schluter_wifi",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copyfile(ROOT / "library/LICENSE", vendor / "schluter_wifi/LICENSE")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "I",
            "--fix",
            str(destination),
        ],
        check=True,
    )
    tests = ROOT / "tests"
    tests.mkdir(exist_ok=True)
    for path in (core / "tests/components/schluter").glob("*.py"):
        tests.joinpath(path.name).write_text(
            path.read_text()
            .replace("homeassistant.components.schluter", "custom_components.schluter")
            .replace(
                "from schluter_wifi import",
                "from custom_components.schluter._vendor.schluter_wifi import",
            )
        )
    tests.joinpath("test_client.py").write_text(
        (ROOT / "library/tests/test_client.py")
        .read_text()
        .replace(
            "from schluter_wifi import",
            "from custom_components.schluter._vendor.schluter_wifi import",
        )
        .replace(
            '"schluter_wifi.monotonic"',
            '"custom_components.schluter._vendor.schluter_wifi.monotonic"',
        )
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--select", "I", "--fix", str(tests)],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", str(destination), str(tests)],
        check=True,
    )
    artifacts = ROOT / "dist"
    artifacts.mkdir(exist_ok=True)
    with zipfile.ZipFile(
        artifacts / "schluter.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for path in sorted(destination.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(destination))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("core", type=Path, help="Home Assistant Core checkout")
    build(parser.parse_args().core)
