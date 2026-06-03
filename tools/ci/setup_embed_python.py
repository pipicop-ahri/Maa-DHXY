"""Download and configure Windows embeddable Python into install/python/."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PYTHON_VERSION = "3.12.10"
DEST_DIR = Path("install") / "python"


def download_file(url: str, dest_path: Path) -> None:
    print(f"Downloading: {url}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, dest_path.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)
    print("Download complete.")


def get_win_arch_suffix() -> str:
    machine = platform.machine().upper()
    processor = os.environ.get("PROCESSOR_IDENTIFIER", "")
    if machine in ("ARM64", "AARCH64") or "ARM64" in processor or "ARMv8" in processor:
        return "arm64"
    return "amd64"


def find_pth_file(dest_dir: Path) -> Path | None:
    version_prefix = f"python{PYTHON_VERSION.replace('.', '')[:3]}"
    candidate = dest_dir / f"{version_prefix}._pth"
    if candidate.exists():
        return candidate
    for name in dest_dir.glob("python*._pth"):
        return name
    return None


def configure_pth(pth_file: Path) -> None:
    print(f"Patching: {pth_file}")
    content = pth_file.read_text(encoding="utf-8")
    content = content.replace("#import site", "import site")
    content = content.replace("# import site", "import site")
    for line in (".", "Lib", "Lib\\site-packages", "DLLs"):
        if line not in content.splitlines():
            content += f"\n{line}"
    pth_file.write_text(content, encoding="utf-8")


def ensure_pip(python_exe: Path) -> bool:
    get_pip = DEST_DIR / "get-pip.py"
    download_file("https://bootstrap.pypa.io/get-pip.py", get_pip)
    try:
        subprocess.run([str(python_exe), str(get_pip)], check=True)
        print("pip installed.")
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"pip install failed: {exc}")
        return False
    finally:
        get_pip.unlink(missing_ok=True)


def main() -> None:
    if platform.system() != "Windows":
        print("setup_embed_python.py only supports Windows.")
        sys.exit(1)

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Target: {DEST_DIR.resolve()}")

    python_exe = DEST_DIR / "python.exe"
    if python_exe.exists():
        print(f"Python already present at {python_exe}, ensuring pip.")
        if ensure_pip(python_exe):
            return
        sys.exit(1)

    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)

    arch = get_win_arch_suffix()
    print(f"Windows embed arch: {arch}")
    zip_name = f"python-{PYTHON_VERSION}-embed-{arch}.zip"
    url = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{zip_name}"
    zip_path = DEST_DIR / zip_name
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    try:
        download_file(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(DEST_DIR)
    finally:
        zip_path.unlink(missing_ok=True)

    pth_file = find_pth_file(DEST_DIR)
    if not pth_file:
        print("Error: no python*._pth found after extract.")
        sys.exit(1)
    configure_pth(pth_file)

    if not python_exe.exists():
        print("Error: python.exe not found after extract.")
        sys.exit(1)

    if not ensure_pip(python_exe):
        sys.exit(1)

    print("Embedded Python ready.")


if __name__ == "__main__":
    main()
