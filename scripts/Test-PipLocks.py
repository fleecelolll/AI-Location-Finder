"""Review/regenerate wheel locks and test dependency resolution without installing.

The online phase reads PyPI JSON and hash-verified PEP 658 metadata only. The
offline resolver phase uses metadata-only test wheels with TEST hashes, never
installs or imports tool packages, and is not a real installer/runtime test.
Use --emit-patch to print (not apply) requirements/installer/build-list updates.
"""
from __future__ import annotations

import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import compatible_tags, cpython_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version

TARGET_PYTHON = (3, 14)
CACHE = {}
RESOLVER_PYTHON = sys.executable


def fetch(url, accept=None):
    request = urllib.request.Request(url, headers={"Accept": accept or "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def package_info(name, version):
    key = (name, version)
    if key not in CACHE:
        CACHE[key] = json.loads(fetch(f"https://pypi.org/pypi/{name}/{version}/json"))
    return CACHE[key]


def installer_pins(root, arch):
    source = (root / "Installer.bat").read_text(encoding="utf-8")
    values = {m.group(1): m.group(2) for m in re.finditer(r'^set "([A-Z0-9_]+)=(.*)"$', source, re.M)}
    runtime = re.search(r'^set YTDLP_RUNTIME_PACKAGES=(.*)$', source, re.M)
    if runtime:
        values["YTDLP_RUNTIME_PACKAGES"] = runtime.group(1)
    values["YTDLP_ARCH_PACKAGE"] = '"Brotli==%BROTLI_VERSION%"' if arch == "x64" and runtime else ""
    # Keep existing dependency versions, even after installation uses a lockfile.
    if "PYTHON_PACKAGES" in values:
        expression = values["PYTHON_PACKAGES"]
    elif runtime:
        expression = '"%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION%" "yt-dlp==%YTDLP_VERSION%" "yt-dlp-ejs==%YTDLP_EJS_VERSION%" %YTDLP_RUNTIME_PACKAGES% %YTDLP_ARCH_PACKAGE%'
    else:
        expression = "%PYSIDE_DISTRIBUTION%==%PYSIDE_VERSION%"
    for _ in range(5):
        expression = re.sub(r"%([A-Z0-9_]+)%", lambda match: values[match.group(1)], expression)
    if "%" in expression:
        raise ValueError("An installer package variable could not be resolved")
    pins = {}
    for token in expression.replace('"', "").split():
        name, version = token.split("==", 1)
        pins[canonicalize_name(name)] = version
    return pins


def wheel_record(name, version, arch):
    platform = "win_amd64" if arch == "x64" else "win_arm64"
    tags = list(cpython_tags(TARGET_PYTHON, ["cp314"], [platform]))
    tags += list(compatible_tags(TARGET_PYTHON, "cp314", [platform]))
    ranks = {tag: position for position, tag in enumerate(tags)}
    info = package_info(name, version)
    candidates = []
    for artifact in info["urls"]:
        if artifact["packagetype"] != "bdist_wheel" or artifact.get("yanked"):
            continue
        _, parsed_version, _, wheel_tags = parse_wheel_filename(artifact["filename"])
        if parsed_version != Version(version) or not wheel_tags.intersection(ranks):
            continue
        candidates.append((min(ranks[tag] for tag in wheel_tags if tag in ranks), artifact))
    if not candidates:
        raise ValueError(f"No compatible {platform} CPython 3.14 wheel: {name}=={version}")
    artifact = min(candidates, key=lambda item: (item[0], item[1]["filename"]))[1]
    if not artifact["url"].startswith("https://files.pythonhosted.org/"):
        raise ValueError("Wheel URL is not on the official PyPI artifact host")
    simple_key = ("simple", name)
    if simple_key not in CACHE:
        CACHE[simple_key] = json.loads(fetch(f"https://pypi.org/simple/{name}/", "application/vnd.pypi.simple.v1+json"))
    listed = next(item for item in CACHE[simple_key]["files"] if item["filename"] == artifact["filename"])
    if listed["hashes"]["sha256"] != artifact["digests"]["sha256"]:
        raise ValueError("PyPI release and simple-index wheel hashes disagree")
    metadata_hash = listed.get("core-metadata", listed.get("data-dist-info-metadata"))
    if not isinstance(metadata_hash, dict) or "sha256" not in metadata_hash:
        raise ValueError(f"Hash-verified PEP 658 metadata unavailable: {artifact['filename']}")
    metadata = fetch(artifact["url"] + ".metadata")
    if hashlib.sha256(metadata).hexdigest() != metadata_hash["sha256"]:
        raise ValueError("Official wheel metadata SHA-256 mismatch")
    parsed = email.message_from_bytes(metadata)
    if canonicalize_name(parsed["Name"]) != name or Version(parsed["Version"]) != Version(version):
        raise ValueError("Wheel metadata distribution identity mismatch")
    return {"name": name, "version": version, "artifact": artifact, "metadata": metadata, "parsed": parsed}


def resolve_records(root, arch):
    pins = installer_pins(root, arch)
    records = {}
    environment = default_environment()
    environment.update(python_version="3.14", python_full_version="3.14.7", sys_platform="win32", platform_system="Windows", platform_machine="AMD64" if arch == "x64" else "ARM64", extra="")
    while len(records) < len(pins):
        name = next(name for name in pins if name not in records)
        record = wheel_record(name, pins[name], arch)
        records[name] = record
        requires_python = record["parsed"].get("Requires-Python")
        if requires_python:
            from pip._vendor.packaging.specifiers import SpecifierSet
            if not SpecifierSet(requires_python).contains("3.14.7"):
                raise ValueError(f"Unsupported runtime Python: {name}")
        for value in record["parsed"].get_all("Requires-Dist", []):
            requirement = Requirement(value)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            dependency = canonicalize_name(requirement.name)
            if requirement.extras or requirement.url:
                raise ValueError("Unexpected extra or direct URL dependency needs review")
            if dependency not in pins:
                exact = [item.version for item in requirement.specifier if item.operator == "==" and "*" not in item.version]
                if len(exact) != 1:
                    raise ValueError(f"Unpinned transitive dependency needs explicit review: {name} -> {requirement}")
                pins[dependency] = exact[0]
            if not requirement.specifier.contains(pins[dependency]):
                raise ValueError(f"Incompatible dependency: {name} -> {requirement}")
    return records


def lock_text(records, arch):
    lines = ["# Reviewed PyPI wheel allowlist for Windows CPython 3.14.7 (" + arch + ").", "# Keep LF line endings. Includes the complete runtime dependency closure.", "# Generated/reviewed with scripts/Test-PipLocks.py; no source distributions."]
    for name, record in sorted(records.items()):
        lines.extend([f"# https://pypi.org/pypi/{name}/{record['version']}/json", "# " + record["artifact"]["filename"], f"{name}=={record['version']} --hash=sha256:{record['artifact']['digests']['sha256']}"])
    return "\n".join(lines) + "\n"


def offline_tests(records, arch, directory):
    # These minimal fixtures preserve official METADATA and wheel tags, but have
    # TEST hashes. They verify pip resolution without downloading large runtimes.
    wheelhouse = directory / arch
    wheelhouse.mkdir()
    requirements = []
    for name, record in sorted(records.items()):
        artifact = record["artifact"]
        wheel = wheelhouse / artifact["filename"]
        distribution = name.replace("-", "_") + "-" + record["version"] + ".dist-info"
        _, _, _, tags = parse_wheel_filename(wheel.name)
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(distribution + "/METADATA", record["metadata"])
            archive.writestr(distribution + "/WHEEL", "Wheel-Version: 1.0\nGenerator: metadata-only-test\nRoot-Is-Purelib: true\n" + "".join("Tag: " + str(tag) + "\n" for tag in sorted(tags, key=str)))
            archive.writestr(distribution + "/RECORD", "")
        requirements.append(f"{name}=={record['version']} --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}")
    lock = wheelhouse / "test-requirements.txt"
    lock.write_text("\n".join(requirements) + "\n", encoding="utf-8")
    base = [RESOLVER_PYTHON, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "install", "--dry-run", "--ignore-installed", "--no-cache-dir", "--no-index", "--find-links", str(wheelhouse), "--only-binary=:all:", "--require-hashes", "--platform", "win_amd64" if arch == "x64" else "win_arm64", "--python-version", "3.14.7", "--implementation", "cp", "--abi", "cp314", "-r", str(lock)]
    run = subprocess.run(base, capture_output=True, text=True, timeout=60)
    if run.returncode:
        raise ValueError("Offline pip resolution failed:\n" + run.stdout + run.stderr)
    lock.write_text("\n".join(requirements).replace("--hash=sha256:", "--hash=sha256:00", 1) + "\n", encoding="utf-8")
    failed = subprocess.run(base, capture_output=True, text=True, timeout=60)
    if failed.returncode == 0 or "HASHES" not in failed.stderr.upper():
        raise ValueError("Tampered-hash dry run did not fail closed")
    lock.write_text("\n".join(line for line in requirements if not line.startswith("shiboken6==")) + "\n", encoding="utf-8")
    missing = subprocess.run(base, capture_output=True, text=True, timeout=60)
    if missing.returncode == 0 or "HASH" not in missing.stderr.upper():
        raise ValueError("Missing transitive dependency did not fail closed")


def verify_installer(root, arch, expected, directory):
    source = (root / "Installer.bat").read_text(encoding="utf-8")
    wanted = hashlib.sha256(expected.encode("utf-8")).hexdigest()
    if f'if /I "%ARCH%"=="{arch}" set "PIP_REQUIREMENTS_SHA256={wanted}"' not in source:
        raise ValueError("Installer lock digest is absent or stale")
    commands = [line for line in source.splitlines() if "from pip._internal" in line and " install " in line]
    if len(commands) != 2 or any('--require-hashes' not in line or '-r "%PIP_REQUIREMENTS%"' not in line for line in commands):
        raise ValueError("Every initial/repair pip install must require the selected hashed lock")
    sequence = ':InstallEmbeddedPackages\ncall :ValidateEmbeddedPython\nif errorlevel 1 exit /b 1\ncall :ValidatePipRequirements\nif errorlevel 1 exit /b 1'
    if sequence not in source:
        raise ValueError("Dependency lock validation must precede package reuse or replacement")
    earliest = ':InstallPythonPackages\nif not defined APP_PY exit /b 1\nif not exist "%APP_PY%" exit /b 1\ncall :ValidatePipRequirements\nif errorlevel 1 exit /b 1\ncall :CurrentPackagesFullyHealthy'
    if earliest not in source:
        raise ValueError("Dependency lock validation must precede the earliest healthy-runtime fast path")
    helper = next(line for line in source.splitlines() if line.startswith('"%APP_PY%" -I -c "import hashlib, os, stat;'))
    code = helper.split(' -c "', 1)[1].rsplit('" >>', 1)[0]
    environment = dict(os.environ, PIP_REQUIREMENTS=str(root / f"requirements-win-{arch}.txt"), PIP_REQUIREMENTS_SHA256=wanted)
    command = [RESOLVER_PYTHON, "-B", "-I", "-c", code]
    checked = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
    if checked.returncode:
        raise ValueError("Actual installer lock-validation command rejected the original lock")
    changed = directory / f"changed-{arch}.txt"
    changed.write_bytes(expected.encode("utf-8") + b"# changed\n")
    environment["PIP_REQUIREMENTS"] = str(changed)
    rejected = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
    if rejected.returncode == 0 or "SHA-256 mismatch" not in rejected.stderr:
        raise ValueError("Actual installer command did not reject a changed lock")


def main():
    global RESOLVER_PYTHON
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--emit-lock-patch", action="store_true")
    parser.add_argument("--offline-python", type=Path, help="Isolated Python 3.14.7 with pinned pip available; never installs packages")
    args = parser.parse_args()
    root = args.root.resolve()
    RESOLVER_PYTHON = str(args.offline_python.resolve()) if args.offline_python else sys.executable
    if not args.emit_lock_patch:
        runtime = subprocess.run([RESOLVER_PYTHON, "-I", "-c", "import json,sys; print(json.dumps(list(sys.version_info[:3])))"], capture_output=True, text=True, check=True, timeout=10)
        if json.loads(runtime.stdout) != [3, 14, 7]:
            raise ValueError("Offline pip marker tests require Python 3.14.7; use --offline-python for a disposable runtime")
    result = {}
    patch = ["*** Begin Patch"]
    with tempfile.TemporaryDirectory(prefix="fleece-pip-lock-test-") as temporary:
        source = (root / "Installer.bat").read_text(encoding="utf-8")
        architectures = ("x64", "arm64") if ":ArchitectureArm64\n" in source else ("x64",)
        for arch in architectures:
            records = resolve_records(root, arch)
            expected = lock_text(records, arch)
            path = root / f"requirements-win-{arch}.txt"
            if args.emit_lock_patch:
                if path.exists():
                    raise ValueError("Refusing to emit a new-file patch over an existing lock")
                patch.extend(["*** Add File: " + path.as_posix()] + ["+" + line for line in expected.splitlines()])
            else:
                if path.read_bytes() != expected.encode("utf-8"):
                    raise ValueError(f"Reviewed wheel lock differs from official metadata: {path.name}")
                offline_tests(records, arch, Path(temporary))
                verify_installer(root, arch, expected, Path(temporary))
            result[arch] = {"packages": len(records), "wheel_bytes_not_downloaded": sum(record["artifact"]["size"] for record in records.values()), "lock_sha256": hashlib.sha256(expected.encode()).hexdigest()}
    if args.emit_lock_patch:
        patch.append("*** End Patch")
        print("\n".join(patch))
    else:
        print(json.dumps({"root": root.name, "verified": result, "test_scope": "official hash-verified metadata; offline metadata-only pip dry runs; no tool installs"}, indent=2))


if __name__ == "__main__":
    main()
