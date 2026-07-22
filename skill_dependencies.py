"""Read-only dependency manifests and preflight checks for Code Skills."""

from __future__ import annotations

import ast
import json
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


SCHEMA_VERSION = 1
MANIFEST_NAME = "dependencies.json"
SUPPORTED_TYPES = {"python", "node", "command"}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9@._/+:-]{1,128}$")
_DISCOVERY_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist",
}
_DISCOVERY_MAX_FILES = 256
_DISCOVERY_MAX_FILE_BYTES = 256 * 1024
_PYTHON_DISTRIBUTION_BY_IMPORT = {
    "PIL": "Pillow",
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "dateutil": "python-dateutil",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
}
_PYTHON_IMPORT_BY_DISTRIBUTION = {
    distribution.lower(): import_name
    for import_name, distribution in _PYTHON_DISTRIBUTION_BY_IMPORT.items()
}
_NODE_BUILTINS = {
    "assert", "buffer", "child_process", "cluster", "console", "constants", "crypto",
    "dgram", "diagnostics_channel", "dns", "domain", "events", "fs", "http", "http2",
    "https", "module", "net", "os", "path", "perf_hooks", "process", "punycode",
    "querystring", "readline", "repl", "stream", "string_decoder", "sys", "timers",
    "tls", "trace_events", "tty", "url", "util", "v8", "vm", "wasi", "worker_threads",
    "zlib",
}


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
    install_hint = re.sub(r"\s+", " ", str(raw.get("installHint") or "").strip())
    if install_hint:
        if len(install_hint) > 500:
            raise DependencyManifestError("installHint must be at most 500 characters")
        normalized["installHint"] = install_hint
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


def _iter_discovery_files(skill_dir):
    skill_dir = Path(skill_dir)
    files = []
    for path in sorted(skill_dir.rglob("*"), key=lambda item: str(item).lower()):
        if len(files) >= _DISCOVERY_MAX_FILES:
            break
        try:
            relative = path.relative_to(skill_dir)
        except ValueError:
            continue
        if any(part.startswith(".") or part in _DISCOVERY_SKIP_DIRS for part in relative.parts[:-1]):
            continue
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            if path.stat().st_size > _DISCOVERY_MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _requirement_version_fields(spec):
    exact = re.search(r"(?:^|,)\s*==\s*([A-Za-z0-9._+-]+)", spec)
    if exact:
        return {"version": exact.group(1)}
    minimum = re.search(r"(?:^|,)\s*(?:>=|~=|\^|~)\s*([A-Za-z0-9._+-]+)", spec)
    if minimum:
        return {"minimumVersion": minimum.group(1)}
    if re.fullmatch(r"\s*[0-9][A-Za-z0-9._+-]*\s*", spec):
        return {"version": spec.strip()}
    return {}


def _python_requirement_from_spec(spec):
    spec = str(spec or "").split(";", 1)[0].strip()
    if not spec or spec.startswith(("-", ".", "/", "\\", "git+", "http:", "https:")):
        return None
    match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?\s*(.*)$", spec)
    if not match:
        return None
    distribution = match.group(1)
    import_name = _PYTHON_IMPORT_BY_DISTRIBUTION.get(distribution.lower(), distribution.replace("-", "_"))
    requirement = {
        "type": "python",
        "name": distribution,
        "importName": import_name,
        "distribution": distribution,
    }
    requirement.update(_requirement_version_fields(match.group(2)))
    return requirement


def _node_requirement(name, version_spec=""):
    name = str(name or "").strip()
    if not name or not _SAFE_NAME.fullmatch(name):
        return None
    requirement = {"type": "node", "name": name}
    requirement.update(_requirement_version_fields(str(version_spec or "")))
    return requirement


def _merge_detected_requirement(target, requirement, *, optional=False):
    if not requirement:
        return
    dep_id = f"{requirement['type']}:{requirement['name']}"
    existing = target.get(dep_id)
    if not existing or (existing[1] and not optional):
        target[dep_id] = (requirement, bool(optional))


def _discover_requirements_files(files, detected, sources):
    for path in files:
        lower_name = path.name.lower()
        if not (lower_name.startswith("requirements") and lower_name.endswith(".txt")):
            continue
        optional = any(token in lower_name for token in ("dev", "test", "docs", "optional"))
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except Exception:
            continue
        sources.add(path.name)
        for line in lines:
            cleaned = line.split("#", 1)[0].strip()
            _merge_detected_requirement(
                detected,
                _python_requirement_from_spec(cleaned),
                optional=optional,
            )


def _discover_pyproject(files, detected, sources):
    for path in files:
        if path.name.lower() != "pyproject.toml":
            continue
        try:
            project = tomllib.loads(path.read_text(encoding="utf-8-sig")).get("project") or {}
        except Exception:
            continue
        sources.add(path.name)
        for spec in project.get("dependencies") or []:
            _merge_detected_requirement(detected, _python_requirement_from_spec(spec))
        optional_groups = project.get("optional-dependencies") or {}
        if isinstance(optional_groups, dict):
            for specs in optional_groups.values():
                for spec in specs or []:
                    _merge_detected_requirement(
                        detected,
                        _python_requirement_from_spec(spec),
                        optional=True,
                    )


def _discover_package_json(files, detected, sources):
    for path in files:
        if path.name.lower() != "package.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        sources.add(path.name)
        for name, version in (payload.get("dependencies") or {}).items():
            _merge_detected_requirement(detected, _node_requirement(name, version))
        for name, version in (payload.get("optionalDependencies") or {}).items():
            _merge_detected_requirement(
                detected,
                _node_requirement(name, version),
                optional=True,
            )


def _discover_python_imports(skill_dir, files, detected, sources):
    python_files = [path for path in files if path.suffix.lower() == ".py"]
    if not python_files:
        return
    local_modules = {path.stem for path in python_files}
    for path in python_files:
        relative = path.relative_to(skill_dir)
        local_modules.update(relative.parts[:-1])
    found = set()
    for path in python_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".", 1)[0])
    external = sorted(
        name for name in found
        if name not in local_modules and name not in sys.stdlib_module_names
    )
    if not external:
        return
    sources.add("Python imports")
    known_imports = {
        (item[0].get("importName") or item[0]["name"].replace("-", "_"))
        for item in detected.values()
        if item[0]["type"] == "python"
    }
    for import_name in external:
        if import_name in known_imports:
            continue
        distribution = _PYTHON_DISTRIBUTION_BY_IMPORT.get(import_name, import_name)
        _merge_detected_requirement(detected, {
            "type": "python",
            "name": distribution,
            "importName": import_name,
            "distribution": distribution,
        })


def _node_package_from_import(value):
    value = str(value or "").strip()
    if not value or value.startswith((".", "/", "node:")):
        return ""
    package = "/".join(value.split("/")[:2]) if value.startswith("@") else value.split("/", 1)[0]
    if package in _NODE_BUILTINS:
        return ""
    return package


def _discover_javascript_imports(files, detected, sources):
    javascript_files = [
        path for path in files
        if path.suffix.lower() in {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
    ]
    found = set()
    patterns = (
        re.compile(r"\b(?:import|export)\s+(?:[^'\"]+?\s+from\s+)?['\"]([^'\"]+)['\"]"),
        re.compile(r"\brequire\(\s*['\"]([^'\"]+)['\"]\s*\)"),
        re.compile(r"\bimport\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    )
    for path in javascript_files:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        for pattern in patterns:
            found.update(filter(None, (_node_package_from_import(item) for item in pattern.findall(text))))
    if not found:
        return
    sources.add("JavaScript imports")
    known = {
        item[0]["name"] for item in detected.values() if item[0]["type"] == "node"
    }
    for name in sorted(found - known):
        _merge_detected_requirement(detected, _node_requirement(name))


def _markdown_install_fragments(text):
    """Return only code-like Markdown fragments that may contain install commands."""
    fragments = list(re.findall(r"`([^`\r\n]{1,1000})`", text))
    for block in re.findall(r"```[^\r\n]*\r?\n(.*?)```", text, flags=re.DOTALL):
        fragments.extend(block.splitlines())
    command_prefix = re.compile(
        r"^(?:[-*+]\s+)?(?:[$>]\s*)?(?:"
        r"(?:python(?:3)?(?:\.exe)?\s+-m\s+|uv\s+)?pip3?(?:\.exe)?\s+install\b|"
        r"npm(?:\.cmd)?\s+(?:install|i)\b|pnpm\s+(?:add|install)\b|"
        r"yarn\s+add\b|bun\s+add\b"
        r")",
        flags=re.IGNORECASE,
    )
    requires_prefix = re.compile(r"^(?:#+\s*)?requires?\s*:\s*(.+)$", flags=re.IGNORECASE)
    for line in text.splitlines():
        stripped = line.strip()
        required = requires_prefix.match(stripped)
        if required:
            stripped = required.group(1).strip()
        if command_prefix.match(stripped):
            fragments.append(stripped)
    return list(dict.fromkeys(fragment.strip() for fragment in fragments if fragment.strip()))


def _install_argument_tokens(raw):
    try:
        tokens = shlex.split(str(raw or ""), posix=True)
    except ValueError:
        tokens = str(raw or "").split()
    result = []
    skip_next = False
    options_with_values = {
        "-r", "--requirement", "-c", "--constraint", "-e", "--editable",
        "--index-url", "--extra-index-url", "--find-links", "--prefix",
    }
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token in {"&&", "||", ";", "|"} or token.startswith("#"):
            break
        if token in options_with_values:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        cleaned = token.rstrip(",.;:")
        if cleaned and cleaned.lower() not in {"package", "packages", "dependency", "dependencies", "missing"}:
            result.append(cleaned)
    return result


def _node_requirement_from_spec(spec):
    spec = str(spec or "").strip()
    if not spec or spec.startswith((".", "/", "\\", "git+", "http:", "https:")):
        return None
    name = spec
    version = ""
    if spec.startswith("@"):
        separator = spec.rfind("@")
        if separator > spec.find("/"):
            name, version = spec[:separator], spec[separator + 1:]
    elif "@" in spec:
        name, version = spec.rsplit("@", 1)
    return _node_requirement(name, version)


def _discover_skill_markdown(skill_dir, detected, sources):
    skill_md = Path(skill_dir) / "SKILL.md"
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except Exception:
        return
    found = False
    pip_pattern = re.compile(
        r"\b(?:(?:python(?:3)?(?:\.exe)?\s+-m|uv)\s+)?pip3?(?:\.exe)?\s+install\s+(.+)$",
        flags=re.IGNORECASE,
    )
    node_pattern = re.compile(
        r"\b(?:npm(?:\.cmd)?\s+(?:install|i)|pnpm\s+(?:add|install)|yarn\s+add|bun\s+add)\s+(.+)$",
        flags=re.IGNORECASE,
    )
    for fragment in _markdown_install_fragments(text):
        pip_match = pip_pattern.search(fragment)
        if pip_match:
            for spec in _install_argument_tokens(pip_match.group(1)):
                before = len(detected)
                _merge_detected_requirement(detected, _python_requirement_from_spec(spec))
                found = found or len(detected) > before
            continue
        node_match = node_pattern.search(fragment)
        if node_match:
            for spec in _install_argument_tokens(node_match.group(1)):
                before = len(detected)
                _merge_detected_requirement(detected, _node_requirement_from_spec(spec))
                found = found or len(detected) > before
    if found:
        sources.add("SKILL.md install commands")


def discover_skill_manifest(skill_dir):
    """Synthesize an in-memory manifest from standard files and static imports."""
    skill_dir = Path(skill_dir)
    files = _iter_discovery_files(skill_dir)
    detected = {}
    sources = set()
    _discover_requirements_files(files, detected, sources)
    _discover_pyproject(files, detected, sources)
    _discover_package_json(files, detected, sources)
    _discover_python_imports(skill_dir, files, detected, sources)
    _discover_javascript_imports(files, detected, sources)
    _discover_skill_markdown(skill_dir, detected, sources)
    if not detected:
        return None
    capabilities = {}
    for dep_type, capability_id in (("python", "python-runtime"), ("node", "node-runtime"), ("command", "command-runtime")):
        required = []
        optional = []
        for requirement, is_optional in detected.values():
            if requirement["type"] != dep_type:
                continue
            (optional if is_optional else required).append(requirement)
        if required or optional:
            capabilities[capability_id] = {
                "required": sorted(required, key=lambda item: item["name"].lower()),
                "optional": sorted(optional, key=lambda item: item["name"].lower()),
            }
    manifest = normalize_manifest({
        "schemaVersion": SCHEMA_VERSION,
        "skill": skill_dir.name,
        "capabilities": capabilities,
    }, expected_skill=skill_dir.name)
    manifest["source"] = "detected"
    manifest["detectedFrom"] = sorted(sources)
    return manifest


def resolve_skill_manifest(skill_dir, bundled_skills_dir=None):
    """Prefer explicit manifests, otherwise adapt a copied Skill automatically."""
    manifest = load_skill_manifest(skill_dir, bundled_skills_dir)
    return manifest or discover_skill_manifest(skill_dir)


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
        "detectedFrom": manifest.get("detectedFrom", []),
        "capabilities": capabilities,
    }


def _powershell_command(arguments):
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    return "& " + " ".join(quote(value) for value in arguments)


def _requirement_install_spec(requirement):
    name = requirement["name"]
    if requirement["type"] == "python":
        if requirement.get("version"):
            return f"{name}=={requirement['version']}"
        if requirement.get("minimumVersion"):
            return f"{name}>={requirement['minimumVersion']}"
    if requirement["type"] == "node" and requirement.get("version"):
        return f"{name}@{requirement['version']}"
    return name


def _missing_requirements(inspection):
    missing = {}
    for capability in inspection.get("capabilities") or []:
        for optional, key in ((False, "required"), (True, "optional")):
            for requirement in capability.get(key) or []:
                if requirement.get("available"):
                    continue
                dep_id = requirement["id"]
                existing = missing.get(dep_id)
                if existing and not existing["optional"]:
                    continue
                missing[dep_id] = {
                    **requirement,
                    "optional": optional,
                    "capabilities": sorted(set(
                        (existing or {}).get("capabilities", []) + [capability["id"]]
                    )),
                }
    return sorted(
        missing.values(),
        key=lambda item: (item["optional"], item["type"], item["name"].lower()),
    )


def build_install_guidance(inspection, *, data_dir, capability_id=""):
    """Build a bounded install/cooperation plan without changing the environment."""
    all_capabilities = list(inspection.get("capabilities", []))
    available_capabilities = [item.get("id", "") for item in all_capabilities if item.get("id")]
    selected_capability = str(capability_id or "").strip()
    if selected_capability:
        selected = [item for item in all_capabilities if item.get("id") == selected_capability]
        if not selected:
            raise DependencyManifestError(
                f"unknown capability '{selected_capability}'; available: {', '.join(available_capabilities) or 'none'}"
            )
    elif len(all_capabilities) == 1:
        selected = all_capabilities
        selected_capability = available_capabilities[0]
    else:
        return {
            "needed": False,
            "selectionRequired": True,
            "selectedCapability": "",
            "availableCapabilities": available_capabilities,
            "requiredMissing": [],
            "optionalMissing": [],
            "steps": [],
            "runtime": {},
            "instructions": (
                "Choose only the capability needed for the current task and call "
                "check_skill_dependencies again with that capability. Do not install dependencies "
                "for every capability. If the user only requested a dependency report, summarize "
                "the capability statuses and stop."
            ),
        }
    scoped_inspection = {**inspection, "capabilities": selected}
    missing = _missing_requirements(scoped_inspection)
    required = [item for item in missing if not item["optional"]]
    optional = [item for item in missing if item["optional"]]
    steps = []
    requirement_types = {
        requirement["type"]
        for capability in selected
        for group in ("required", "optional")
        for requirement in capability.get(group, [])
    }
    runtime = {}

    if "python" in requirement_types:
        python_executable, python_source = _managed_python(data_dir)
        runtime["python"] = {
            "executable": str(python_executable or ""),
            "source": python_source,
        }

    if "node" in requirement_types:
        managed_node_modules = Path(data_dir) / "runtime" / "node" / "node_modules"
        node_sources = {
            requirement.get("source", "")
            for capability in selected
            for group in ("required", "optional")
            for requirement in capability.get(group, [])
            if requirement.get("type") == "node"
        }
        runtime["node"] = {
            "nodePath": str(managed_node_modules),
            "source": "managed" if "managed" in node_sources else ("app" if "app" in node_sources else "missing"),
        }

    python_items = [item for item in required if item["type"] == "python"]
    if python_items:
        runtime_root = Path(data_dir) / "runtime" / "python"
        managed_python = runtime_root / ("python.exe" if sys.platform == "win32" else "bin/python")
        current_python, source = _managed_python(data_dir)
        commands = []
        if source != "managed" and current_python:
            commands.append({
                "purpose": "create_managed_python_runtime",
                "command": _powershell_command([current_python, "-m", "venv", runtime_root]),
            })
        if current_python:
            commands.append({
                "purpose": "install_python_packages",
                "command": _powershell_command([
                    managed_python,
                    "-m",
                    "pip",
                    "install",
                    *(_requirement_install_spec(item) for item in python_items),
                ]),
            })
        steps.append({
            "type": "python",
            "strategy": "managed_runtime",
            "requirements": [item["id"] for item in python_items],
            "commands": commands,
            "manualReason": "python_runtime_missing" if not current_python else "",
            "runWith": str(managed_python),
        })

    node_items = [item for item in required if item["type"] == "node"]
    if node_items:
        runtime_root = Path(data_dir) / "runtime" / "node"
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        commands = []
        if npm:
            commands.append({
                "purpose": "install_node_packages",
                "command": _powershell_command([
                    npm,
                    "install",
                    "--prefix",
                    runtime_root,
                    "--no-save",
                    *(_requirement_install_spec(item) for item in node_items),
                ]),
            })
        steps.append({
            "type": "node",
            "strategy": "managed_runtime",
            "requirements": [item["id"] for item in node_items],
            "commands": commands,
            "manualReason": "npm_runtime_missing" if not npm else "",
            "nodePath": str(runtime_root / "node_modules"),
        })

    command_items = [item for item in required if item["type"] == "command"]
    if command_items:
        steps.append({
            "type": "command",
            "strategy": "user_cooperation",
            "requirements": [item["id"] for item in command_items],
            "installHints": [
                {"requirement": item["id"], "text": item["installHint"]}
                for item in command_items
                if item.get("installHint")
            ],
            "commands": [],
            "manualReason": "system_command_requires_user_installation",
        })

    return {
        "needed": bool(required),
        "selectionRequired": False,
        "selectedCapability": selected_capability,
        "availableCapabilities": available_capabilities,
        "requiredMissing": required,
        "optionalMissing": optional,
        "steps": steps,
        "runtime": runtime,
        "instructions": (
            "Install only required items declared in this result. Use the proposed managed-runtime "
            "commands through run_command when the current permission mode allows it; otherwise "
            "explain the missing items and cooperate with the user. System-command dependencies "
            "must be installed by the user outside Code: do not call run_command or write_file to "
            "install them, modify PATH, or create global command wrappers. Present installHints "
            "verbatim when supplied; never execute them and never guess a package ID when absent. "
            "Explain the missing commands and wait for the user, then re-run "
            "check_skill_dependencies after installation without changing the environment. "
            "When executing the Skill, use the Python executable or NODE_PATH returned in runtime "
            "whenever its dependencies come from the managed runtime."
        ) if required else (
            "Required dependencies are ready. Optional gaps do not block the Skill. When executing "
            "the Skill, use the Python executable or NODE_PATH returned in runtime whenever its "
            "dependencies come from the managed runtime."
        ),
    }


def inspect_skill_directory(skill_dir, *, bundled_skills_dir, app_dir, data_dir, capability_id=""):
    skill_dir = Path(skill_dir)
    manifest = resolve_skill_manifest(skill_dir, bundled_skills_dir)
    if not manifest:
        return {
            "name": skill_dir.name,
            "status": "undeclared",
            "manifestSource": "",
            "detectedFrom": [],
            "capabilities": [],
            "installGuidance": {
                "needed": False,
                "selectionRequired": False,
                "selectedCapability": "",
                "availableCapabilities": [],
                "requiredMissing": [],
                "optionalMissing": [],
                "steps": [],
                "runtime": {},
                "instructions": "No external dependencies were declared or detected.",
            },
        }
    inspection = inspect_manifest(manifest, app_dir=app_dir, data_dir=data_dir)
    inspection["installGuidance"] = build_install_guidance(
        inspection,
        data_dir=data_dir,
        capability_id=capability_id,
    )
    return inspection


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
            manifest = resolve_skill_manifest(skill_dir, bundled_skills_dir)
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
