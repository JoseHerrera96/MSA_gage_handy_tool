from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tests"))
from browser_poc_server import SOURCES, pyodide_runtime_allowlist, validate_pyodide_runtime

CORE_SHA256 = "9bc8f127db6c590b191b9aee754022cb41b1a36c7bac233776c11c5ecb541be8"
UCRT_MANIFEST_SHA256 = "0f2b5d13d9524a3329f9aefe793cb7355c1a79ac2f9a316e7d4110a0e1fadde3"
SDK_LICENSE_SHA256 = "0f4a26ac9dc50066f8a1bfeaaf3f092d1b9e4791df5487b9f3c31e7c3dc4d7f5"
VCRUNTIME_SHA256 = {
    "VCRUNTIME140.dll": "052ad6a20d375957e82aa6a3c441ea548d89be0981516ca7eb306e063d5027f4",
    "VCRUNTIME140_1.dll": "6a99bc0128e0c7d6cbbf615fcc26909565e17d4ca3451b97f8987f9c6acbc6c8",
}
CORE_FILES = ("pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json")
UI_FILES = ("browser_app.html", "browser_app.js", "browser_runtime.js", "type1_browser_poc.html", "type1_browser_poc.js", "msa_browser_poc.html", "msa_browser_poc.js")


def stage_application_source(destination: Path) -> Path:
    sources = [source for route, source in SOURCES.items() if route != "/tests/browser_poc.py"]
    sources.extend(PROJECT / "tests" / name for name in UI_FILES)
    sources.extend(PROJECT / name for name in (
        "LICENSE", "README.md", "pyproject.toml", "requirements.txt",
        "desktop/launcher.py", "desktop/build.py", "desktop/THIRD_PARTY_NOTICES.md",
        "desktop/hooks/hook-pystray.py", "desktop/licenses/OPENBLAS-0.3.26.txt",
        "tests/browser_poc_server.py",
    ))
    for source in sources:
        target = destination / source.relative_to(PROJECT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    archive_path = destination.parent / "application-source.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            relative = source.relative_to(PROJECT)
            archive.write(destination / relative, relative.as_posix())
    return archive_path


def stage_runtime(core_archive: Path, packages_directory: Path, destination: Path) -> None:
    hasher = hashlib.sha256()
    with core_archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != CORE_SHA256:
        raise ValueError("Pyodide core archive checksum does not match the official release.")
    destination.mkdir()
    with tarfile.open(core_archive, "r:bz2") as archive:
        for name in CORE_FILES:
            member = archive.getmember(f"pyodide/{name}")
            if not member.isfile():
                raise ValueError(f"Invalid Pyodide core file: {name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Missing Pyodide core file: {name}")
            with source, (destination / name).open("xb") as target:
                shutil.copyfileobj(source, target)
    lock = json.loads((destination / "pyodide-lock.json").read_text(encoding="utf-8"))
    allowed = pyodide_runtime_allowlist(lock)
    packages_directory = packages_directory.resolve(strict=True)
    pending = ["numpy", "pandas", "scipy", "matplotlib"]
    checked = set()
    while pending:
        name = pending.pop()
        if name in checked:
            continue
        checked.add(name)
        package = lock.get("packages", {}).get(name)
        if not package or package.get("file_name") not in allowed:
            raise ValueError(f"Invalid Pyodide package: {name}")
        filename = package["file_name"]
        source = (packages_directory / filename).resolve(strict=True)
        if source.parent != packages_directory or not source.is_file():
            raise ValueError(f"Invalid package location: {name}")
        target = destination / filename
        if not target.exists():
            shutil.copyfile(source, target)
        pending.extend(package.get("depends", []))
    validate_pyodide_runtime(destination)


def stage_sdk_license(source: Path, destination: Path) -> None:
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != SDK_LICENSE_SHA256:
        raise ValueError("Windows SDK license does not match the verified 10.0.22621.2428 installer.")
    (destination / "WINDOWS-SDK.rtf").write_bytes(content)


def stage_licenses(runtime: Path, destination: Path, sdk_license: Path | None, source_root: Path = PROJECT) -> None:
    destination.mkdir()
    if sdk_license is not None:
        stage_sdk_license(sdk_license, destination)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise FileNotFoundError(f"Python runtime license not found: {python_license}")
    shutil.copyfile(python_license, destination / "PYTHON.txt")
    shutil.copyfile(source_root / "desktop" / "licenses" / "OPENBLAS-0.3.26.txt", destination / "OPENBLAS-0.3.26.txt")
    lock = json.loads((runtime / "pyodide-lock.json").read_text(encoding="utf-8"))
    wheel = runtime / lock["packages"]["matplotlib-pyodide"]["file_name"]
    with zipfile.ZipFile(wheel) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/LICENSE")]
        if len(names) != 1:
            raise ValueError("Missing or ambiguous Pyodide MPL license")
        license_text = archive.read(names[0])
        if not license_text.startswith(b"Mozilla Public License Version 2.0"):
            raise ValueError("Unexpected Pyodide MPL license")
        (destination / "MPL-2.0.txt").write_bytes(license_text)
    manifest = {
        "python": sys.version,
        "openssl": ssl.OPENSSL_VERSION,
        "windows_sdk_ucrt": "10.0.22621.2428" if sdk_license is not None else "system",
        "windows_sdk_ucrt_manifest_sha256": UCRT_MANIFEST_SHA256 if sdk_license is not None else None,
        "build_packages": {name: importlib.metadata.version(name) for name in ("PyInstaller", "pystray", "Pillow", "six", "numpy")},
        "pyodide_packages": {name: package["version"] for name, package in lock["packages"].items() if (runtime / package.get("file_name", "")).is_file()},
    }
    (destination / "build-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def replace_ucrt_dlls(bundle: Path, sdk: Path) -> None:
    files = list(bundle.glob("api-ms-win-*.dll"))
    ucrt = bundle / "ucrtbase.dll"
    if not ucrt.is_file():
        raise FileNotFoundError(f"Bundled UCRT not found: {ucrt}")
    files.append(ucrt)
    files.sort(key=lambda path: path.name.lower())
    manifest = hashlib.sha256()
    for target in files:
        source = sdk / target.name
        if not source.is_file():
            raise FileNotFoundError(f"SDK redistributable not found: {source}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest.update(f"{target.name.lower()}:{digest}\n".encode("ascii"))
    if manifest.hexdigest() != UCRT_MANIFEST_SHA256:
        raise ValueError("UCRT files do not match the verified Windows SDK 10.0.22621.2428 redistributable.")
    for target in files:
        shutil.copyfile(sdk / target.name, target)


def remove_local_ucrt(bundle: Path) -> None:
    if not bundle.is_dir():
        raise FileNotFoundError(f"Bundle directory not found: {bundle}")
    for target in bundle.glob("api-ms-win-*.dll"):
        target.unlink()
    ucrt = bundle / "ucrtbase.dll"
    if ucrt.exists():
        ucrt.unlink()


def verify_vcruntime(bundle: Path) -> None:
    for name, expected in VCRUNTIME_SHA256.items():
        path = bundle / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Visual C++ runtime does not match the verified redistributable: {name}")


def build(core_archive: Path, packages_directory: Path, output: Path, ucrt_directory: Path | None, sdk_license: Path | None, *, system_ucrt: bool = False) -> Path:
    output = output.resolve()
    result = output / "MSA-Handy-Tool"
    if result.exists():
        raise FileExistsError(f"Refusing to overwrite existing distribution: {result}")
    if system_ucrt:
        if ucrt_directory is not None or sdk_license is not None:
            raise ValueError("System UCRT cannot be combined with SDK inputs.")
    elif ucrt_directory is None or sdk_license is None:
        raise ValueError("SDK UCRT builds require both an SDK directory and license.")
    with tempfile.TemporaryDirectory(prefix="msa-desktop-build-") as temporary:
        temporary = Path(temporary)
        snapshot = temporary / "application"
        source_archive = stage_application_source(snapshot)
        runtime = temporary / "pyodide"
        stage_runtime(core_archive, packages_directory, runtime)
        licenses = temporary / "licenses"
        stage_licenses(runtime, licenses, sdk_license, snapshot)
        command = [sys.executable, "-m", "PyInstaller", "--onedir", "--windowed", "--name", "MSA-Handy-Tool", "--additional-hooks-dir", str(snapshot / "desktop" / "hooks"), "--hidden-import", "pystray._win32", "--copy-metadata", "Pillow", "--copy-metadata", "pystray", "--copy-metadata", "six", "--paths", str(snapshot / "tests"), "--distpath", str(output), "--workpath", str(temporary / "work"), "--specpath", str(temporary)]
        files = [source for route, source in SOURCES.items() if route != "/tests/browser_poc.py"]
        files.extend(PROJECT / "tests" / name for name in UI_FILES)
        files.append(PROJECT / "LICENSE")
        files.append(PROJECT / "desktop" / "THIRD_PARTY_NOTICES.md")
        for source in files:
            target = Path(".") if source.name == "THIRD_PARTY_NOTICES.md" else source.relative_to(PROJECT).parent
            command.extend(["--add-data", f"{snapshot / source.relative_to(PROJECT)};{target}"])
        command.extend(["--add-data", f"{runtime};pyodide", "--add-data", f"{licenses};licenses", "--add-data", f"{source_archive};source", str(snapshot / "desktop" / "launcher.py")])
        subprocess.run(command, cwd=PROJECT, check=True)
        verify_vcruntime(result / "_internal")
        if system_ucrt:
            remove_local_ucrt(result / "_internal")
        else:
            replace_ucrt_dlls(result / "_internal", ucrt_directory)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the offline Windows browser application.")
    parser.add_argument("--core-archive", type=Path, required=True)
    parser.add_argument("--packages-dir", type=Path, required=True)
    parser.add_argument("--ucrt-dir", type=Path, help="Windows SDK UCRT redistributable directory for x64.")
    parser.add_argument("--sdk-license", type=Path, help="License extracted from the Windows SDK installer.")
    parser.add_argument("--system-ucrt", action="store_true", help="Use the Windows 10 or later system UCRT instead of bundling it.")
    parser.add_argument("--output", type=Path, default=PROJECT / "dist")
    arguments = parser.parse_args()
    print(f"Distribution created: {build(arguments.core_archive, arguments.packages_dir, arguments.output, arguments.ucrt_dir, arguments.sdk_license, system_ucrt=arguments.system_ucrt)}")


if __name__ == "__main__":
    main()