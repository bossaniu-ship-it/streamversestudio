#!/usr/bin/env python3

import os
import sys
import zipfile
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXTRACT_DIR = ROOT / ".streamverse_app"


def find_zip():
    """Find the first ZIP file in the repository root."""
    zips = [
        p for p in ROOT.glob("*.zip")
        if p.is_file()
    ]

    if not zips:
        raise FileNotFoundError(
            "No .zip file found in the repository root."
        )

    if len(zips) > 1:
        print(
            "Multiple ZIP files found. Using:",
            zips[0].name
        )

    return zips[0]


def safe_extract(zip_path, destination):
    """Safely extract ZIP without allowing path traversal."""
    destination = destination.resolve()

    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()

            if not str(target).startswith(str(destination)):
                raise RuntimeError(
                    f"Unsafe ZIP entry detected: {member.filename}"
                )

        archive.extractall(destination)


def find_project_root(directory):
    """
    Find the actual Next.js project root.

    Handles ZIPs that contain either:

        package.json
        app/
        components/

    or:

        some-folder/
            package.json
            app/
            components/
    """

    # Direct project
    if (directory / "package.json").exists():
        return directory

    # Project nested one or more levels down
    candidates = list(directory.rglob("package.json"))

    if not candidates:
        raise FileNotFoundError(
            "Could not find package.json inside the ZIP."
        )

    # Prefer the package.json belonging to a Next.js project
    for package_json in candidates:
        try:
            import json

            data = json.loads(
                package_json.read_text(encoding="utf-8")
            )

            dependencies = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }

            if "next" in dependencies:
                return package_json.parent

        except Exception:
            continue

    return candidates[0].parent


def copy_project_to_root(project_root):
    """
    Copy extracted project files into the repository root.

    Existing deployment helper files are preserved.
    """

    protected = {
        ".git",
        ".gitignore",
        "unzip.py",
        "build.sh",
        "render.yaml",
    }

    for item in project_root.iterdir():
        destination = ROOT / item.name

        if item.name in protected:
            continue

        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()

        shutil.move(str(item), str(destination))


def main():
    print("=" * 70)
    print("StreamVerse Render ZIP Extractor")
    print("=" * 70)

    zip_path = find_zip()

    print(f"ZIP found: {zip_path.name}")

    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)

    EXTRACT_DIR.mkdir(parents=True)

    print("Extracting ZIP...")
    safe_extract(zip_path, EXTRACT_DIR)

    project_root = find_project_root(EXTRACT_DIR)

    print(f"Project root: {project_root}")

    copy_project_to_root(project_root)

    print("Extraction complete.")

    package_json = ROOT / "package.json"

    if not package_json.exists():
        raise RuntimeError(
            "package.json was not found after extraction."
        )

    print("Next.js project detected.")
    print("Ready for npm install / npm run build.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("DEPLOYMENT EXTRACTION FAILED")
        print(str(exc))
        sys.exit(1)
