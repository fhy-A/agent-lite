"""Read-only dependency manifests and preflight checks for Code Skills."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCHEMA_VERSION = 1
MANIFEST_NAME = "dependencies.json"
SUPPORTED_TYPES = {"python", "node", "command"}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9@._/+:-]{1,128}$")


class DependencyManifestError(ValueError):
    """Raised when a Skill dependency manifest is malformed."""


def _read_manifest(path: Path) -> dict:
    try:
        if path.stat().st_size > 128 * 1024:
            raise DependencyManifestError("dependency manifest is too large")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except DependencyManifestError:
        raise
    except Exception as exc:
        raise DependencyManifestError(f"invalid dependency manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise DependencyManifestError("dependency manifest must be an object")
    return payload


def _normalize_requirement(raw, *, optional=False):
    if not isinstance(raw, dict):
        raise DependencyManifestError("dependency requirement must be an object")
    dep_type = str(raw.get("type") or "").strip().lower()
    name = str(raw.get("name") or "").strip()
    if dep_type not in SUPPORTED_TYPES:
        raise DependencyManifestError(f"unsupported dependency type: {dep_type or 'empty'}")
    if not _SAFE_NAME.fullmatch(name):
        raise DependencyManifestError(f"invalid dependency name: {name or 'empty'}")
    normalized = {
        "id": f"{dep_type}:{name}",
        "type": dep_type,
        "name": name,
        "optional": bool(optional),
    }
    for field in ("version", "minimumVersion", "importName", "distribution"):
        value = str(raw.get(field) or "").strip()
        if value:
            if field in {"importName", "distribution"} and not _SAFE_NAME.fullmatch(value):
                raise DependencyManifestError(f"invalid {field}: {value}")
            normalized[field] = value
    return normalized


def normalize_manifest(payload, *, expected_skill=""):
    if int(payload.get("schemaVersion") or 0) != SCHEMA_VERSION:
        raise DependencyManifestError("unsupported dependency manifest schemaVersion")
    skill_name = str(payload.get("skill") or expected_skill or "").strip()
    if not skill_name or not _SAFE_NAME.fullmatch(skill_name):
        raise DependencyManifestError("dependency manifest requires a valid skill name")
    if expected_skill and skill_name != expected_skill:
        raise DependencyManifestError("dependency manifest skill does not match its directory")
    raw_capabilities = payload.get("capabilities")
    if not isinstance(raw_capabilities, dict) or not raw_capabilities:
        raise DependencyManifestError("dependency manifest requires capabilities")
    capabilities = []
    for capability_id, raw_capability in raw_capabilities.items():
        capability_id = str(capability_id or "").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", capability_id):
            raise DependencyManifestError(f"invalid capability id: {capability_id or 'empty'}")
        if not isinstance(raw_capability, dict):
            raise DependencyManifestError(f"capability {capability_id} must be an object")
        required = [
            _normalize_requirement(item)
            for item in (raw_capability.get("required") or [])
        ]
        optional = [
            _normalize_requirement(item, optional=True)
            for item in (raw_capability.get("optional") or [])
        ]
        capabilities.append({
            "id": capability_id,
            "required": required,
            "optional": optional,
        })
    return {
        "schemaVersion": SCHEMA_VERSION,
        "skill": skill_name,
        "capabilities": capabilities,
    }


def load_skill_manifest(skill_dir, bundled_skills_dir=None):
    """Load a local manifest, falling back to the current bundled Skill copy."""
    skill_dir = Path(skill_dir)
    candidates = [(skill_dir / MANIFEST_NAME, "local")]
    if bundled_skills_dir:
        bundled = Path(bundled_skills_dir) / skill_dir.name / MANIFEST_NAME
        try:
            is_same = bundled.resolve() == candidates[0][0].resolve()
        except OSError:
            is_same = False
        if not is_same:
            candidates.append((bundled, "bundled"))
    for path, source in candidates:
        if not path.is_file():
            continue
        manifest = normalize_manifest(_read_manifest(path), expected_skill=skill_dir.name)
        manifest["source"] = source
        return manifest
    return None


def _version_parts(value):
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(part) for part in parts[:4])


def _version_satisfies(detected, requirement):
    exact = requirement.get("version")
    minimum = requirement.get("minimumVersion")
    if exact:
        return str(detected or "") == exact
    if minimum:
        detected_parts = _version_parts(detected)
        minimum_parts = _version_parts(minimum)
        return bool(detected_parts and minimum_parts and detected_parts >= minimum_parts)
    return True


def _managed_python(data_dir):
    runtime_root = Path(data_dir) / "runtime" / "python"
    candidates = (
        runtime_root / "python.exe",
        runtime_root / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate), "managed"
    executable = shutil.which("python") or shutil.which("python3")
    if executable:
        return executable, "system"
    if not getattr(sys, "frozen", False) and Path(sys.executable).is_file():
        return sys.executable, "system"
    return "", "missing"


def _probe_python(requirements, data_dir):
    if not requirements:
        return {}
    executable, source = _managed_python(data_dir)
    if not executable:
        return {
            item["id"]: {"installed": False, "available": False, "reason": "python_runtime_missing"}
            for item in requirements
        }
    query = [
        {
            "id": item["id"],
            "importName": item.get("importName") or item["name"].replace("-", "_"),
            "distribution": item.get("distribution") or item["name"],
        }
        for item in requirements
    ]
    script = (
        "import importlib.util, importlib.metadata, json, sys\n"
        "result = {}\n"
        "for item in json.loads(sys.argv[1]):\n"
        "    found = importlib.util.find_spec(item['importName']) is not None\n"
        "    version = ''\n"
        "    if found:\n"
        "        try: version = importlib.metadata.version(item['distribution'])\n"
        "        except Exception: pass\n"
        "    result[item['id']] = {'installed': found, 'version': version}\n"
        "print(json.dumps(result))\n"
    )
    try:
        completed = subprocess.run(
            [executable, "-c", script, json.dumps(query, separators=(",", ":"))],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "python dependency probe failed")
        detected = json.loads(completed.stdout)
    except Exception:
        return {
            item["id"]: {"installed": False, "available": False, "reason": "probe_failed"}
            for item in requirements
        }
    result = {}
    for item in requirements:
        state = detected.get(item["id"]) or {}
        installed = bool(state.get("installed"))
        version = str(state.get("version") or "")
        available = installed and _version_satisfies(version, item)
        result[item["id"]] = {
            "installed": installed,
            "available": available,
            "detectedVersion": version,
            "source": source,
            "reason": "" if available else ("version_mismatch" if installed else "not_installed"),
        }
    return result


def _node_package_path(root, package_name):
    return Path(root).joinpath(*package_name.split("/"), "package.json")


def _probe_node(requirements, app_dir, data_dir):
    roots = (
        (Path(data_dir) / "runtime" / "node" / "node_modules", "managed"),
        (Path(app_dir) / "node_modules", "app"),
    )
    result = {}
    for item in requirements:
        detected_version = ""
        detected_source = ""
        for root, source in roots:
            package_json = _node_package_path(root, item["name"])
            if not package_json.is_file():
                continue
            try:
                detected_version = str(json.loads(package_json.read_text(encoding="utf-8"))["version"])
                detected_source = source
                break
            except Exception:
                continue
        installed = bool(detected_source)
        available = installed and _version_satisfies(detected_version, item)
        result[item["id"]] = {
            "installed": installed,
            "available": available,
            "detectedVersion": detected_version,
            "source": detected_source,
            "reason": "" if available else ("version_mismatch" if installed else "not_installed"),
        }
    return result


def _probe_commands(requirements, data_dir):
    runtime_bin = Path(data_dir) / "runtime" / "bin"
    result = {}
    for item in requirements:
        name = item["name"]
        managed = next((
            candidate for candidate in (
                runtime_bin / name,
                runtime_bin / f"{name}.exe",
                runtime_bin / f"{name}.cmd",
                runtime_bin / f"{name}.bat",
            ) if candidate.is_file()
        ), None)
        system = "" if managed else (shutil.which(name) or "")
        available = bool(managed or system)
        result[item["id"]] = {
            "installed": available,
            "available": available,
            "detectedVersion": "",
            "source": "managed" if managed else ("system" if system else ""),
            "reason": "" if available else "not_installed",
        }
    return result


def inspect_manifest(manifest, *, app_dir, data_dir):
    requirements = {}
    for capability in manifest["capabilities"]:
        for requirement in capability["required"] + capability["optional"]:
            requirements[requirement["id"]] = requirement
    by_type = {
        dep_type: [item for item in requirements.values() if item["type"] == dep_type]
        for dep_type in SUPPORTED_TYPES
    }
    detected = {}
    detected.update(_probe_python(by_type["python"], data_dir))
    detected.update(_probe_node(by_type["node"], app_dir, data_dir))
    detected.update(_probe_commands(by_type["command"], data_dir))

    capabilities = []
    for capability in manifest["capabilities"]:
        required = []
        optional = []
        for requirement in capability["required"]:
            required.append({**requirement, **detected[requirement["id"]]})
        for requirement in capability["optional"]:
            optional.append({**requirement, **detected[requirement["id"]]})
        capabilities.append({
            "id": capability["id"],
            "status": "ready" if all(item["available"] for item in required) else "unavailable",
            "required": required,
            "optional": optional,
            "missingOptional": sum(not item["available"] for item in optional),
        })
    ready_count = sum(capability["status"] == "ready" for capability in capabilities)
    if ready_count == len(capabilities):
        status = "ready"
    elif ready_count:
        status = "partial"
    else:
        status = "unavailable"
    return {
        "name": manifest["skill"],
        "status": status,
        "manifestSource": manifest.get("source", "local"),
        "capabilities": capabilities,
    }


def inspect_skill_dependencies(skills_dir, *, bundled_skills_dir, app_dir, data_dir):
    """Inspect every installed Skill that declares external dependencies."""
    skills_dir = Path(skills_dir)
    skills = []
    errors = []
    if not skills_dir.is_dir():
        return {"summary": {"declared": 0, "ready": 0, "partial": 0, "unavailable": 0}, "skills": [], "errors": []}
    for skill_dir in sorted(skills_dir.iterdir(), key=lambda path: path.name.lower()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").is_file():
            continue
        try:
            manifest = load_skill_manifest(skill_dir, bundled_skills_dir)
            if manifest:
                skills.append(inspect_manifest(manifest, app_dir=app_dir, data_dir=data_dir))
        except DependencyManifestError as exc:
            errors.append({"name": skill_dir.name, "error": str(exc)})
    summary = {
        "declared": len(skills),
        "ready": sum(skill["status"] == "ready" for skill in skills),
        "partial": sum(skill["status"] == "partial" for skill in skills),
        "unavailable": sum(skill["status"] == "unavailable" for skill in skills),
    }
    return {"summary": summary, "skills": skills, "errors": errors}
