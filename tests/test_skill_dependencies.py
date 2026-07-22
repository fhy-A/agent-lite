import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import skill_dependencies as dependencies


def _manifest(skill="demo"):
    return {
        "schemaVersion": 1,
        "skill": skill,
        "capabilities": {
            "create": {
                "required": [
                    {"type": "python", "name": "demo-python", "importName": "demo_python"},
                    {"type": "node", "name": "demo-node", "version": "1.2.3"},
                ],
                "optional": [
                    {"type": "command", "name": "demo-cli"},
                ],
            },
            "inspect": {
                "required": [
                    {
                        "type": "command",
                        "name": "demo-cli",
                        "installHint": "Windows PowerShell: winget install --id Demo.Cli --exact",
                    },
                ],
            },
        },
    }


class TestDependencyManifest(unittest.TestCase):
    def test_normalizes_capabilities_and_requirements(self):
        manifest = dependencies.normalize_manifest(_manifest(), expected_skill="demo")
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["skill"], "demo")
        self.assertEqual([item["id"] for item in manifest["capabilities"]], ["create", "inspect"])
        self.assertEqual(manifest["capabilities"][0]["required"][0]["id"], "python:demo-python")
        self.assertTrue(manifest["capabilities"][0]["optional"][0]["optional"])
        self.assertEqual(
            manifest["capabilities"][1]["required"][0]["installHint"],
            "Windows PowerShell: winget install --id Demo.Cli --exact",
        )


class TestDependencyDiscovery(unittest.TestCase):
    def test_discovers_python_requirements_and_static_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "copied-python"
            scripts = skill_dir / "scripts"
            scripts.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Copied Skill", encoding="utf-8")
            (skill_dir / "requirements.txt").write_text(
                "requests>=2.28\nPillow~=10.0\n",
                encoding="utf-8",
            )
            (skill_dir / "requirements-dev.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
            (skill_dir / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
            helpers = scripts / "office" / "helpers"
            helpers.mkdir(parents=True)
            (helpers / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
            (scripts / "run.py").write_text(
                "import json\nimport requests\nimport yaml\nfrom PIL import Image\nimport helper\nfrom helpers import VALUE\n",
                encoding="utf-8",
            )

            manifest = dependencies.discover_skill_manifest(skill_dir)

        self.assertEqual(manifest["source"], "detected")
        self.assertIn("requirements.txt", manifest["detectedFrom"])
        self.assertIn("Python imports", manifest["detectedFrom"])
        capability = next(item for item in manifest["capabilities"] if item["id"] == "python-runtime")
        required = {item["name"]: item for item in capability["required"]}
        optional = {item["name"]: item for item in capability["optional"]}
        self.assertEqual(required["requests"]["minimumVersion"], "2.28")
        self.assertEqual(required["Pillow"]["minimumVersion"], "10.0")
        self.assertEqual(required["PyYAML"]["importName"], "yaml")
        self.assertEqual(optional["pytest"]["version"], "9.1.1")
        self.assertNotIn("json", required)
        self.assertNotIn("helper", required)
        self.assertNotIn("helpers", required)

    def test_discovers_package_json_and_javascript_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "copied-node"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Copied Skill", encoding="utf-8")
            (skill_dir / "package.json").write_text(json.dumps({
                "dependencies": {"lodash": "^4.17.0"},
                "optionalDependencies": {"sharp": "0.33.0"},
            }), encoding="utf-8")
            (skill_dir / "index.js").write_text(
                "import chalk from 'chalk';\nimport fs from 'node:fs';\nconst helper = require('./helper');\n",
                encoding="utf-8",
            )
            (skill_dir / "widget.tsx").write_text(
                "import React from 'react';\nimport localWidget from './widget';\n",
                encoding="utf-8",
            )

            manifest = dependencies.discover_skill_manifest(skill_dir)

        capability = next(item for item in manifest["capabilities"] if item["id"] == "node-runtime")
        required = {item["name"]: item for item in capability["required"]}
        optional = {item["name"]: item for item in capability["optional"]}
        self.assertEqual(required["lodash"]["minimumVersion"], "4.17.0")
        self.assertIn("chalk", required)
        self.assertIn("react", required)
        self.assertEqual(optional["sharp"]["version"], "0.33.0")
        self.assertNotIn("fs", required)

    def test_discovers_explicit_install_commands_from_copied_skill_markdown(self):
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "documented-installer"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                """# Documented installer

## Installation

`python -m pip install requests>=2.31 PyYAML`

```bash
npm install @scope/tool@1.2.0 sharp
```

This paragraph discusses dependencies but does not declare another package.
""",
                encoding="utf-8",
            )

            manifest = dependencies.discover_skill_manifest(skill_dir)

        self.assertEqual(manifest["source"], "detected")
        self.assertIn("SKILL.md install commands", manifest["detectedFrom"])
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        python_required = {item["name"]: item for item in capabilities["python-runtime"]["required"]}
        node_required = {item["name"]: item for item in capabilities["node-runtime"]["required"]}
        self.assertEqual(python_required["requests"]["minimumVersion"], "2.31")
        self.assertEqual(python_required["PyYAML"]["importName"], "yaml")
        self.assertEqual(node_required["@scope/tool"]["version"], "1.2.0")
        self.assertIn("sharp", node_required)

    def test_plain_markdown_dependency_discussion_is_not_auto_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "workflow-only"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "# Workflow\n\nReview the project's dependencies and installation plan.\n",
                encoding="utf-8",
            )

            manifest = dependencies.discover_skill_manifest(skill_dir)

        self.assertIsNone(manifest)

    def test_explicit_manifest_remains_the_highest_priority(self):
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "explicit"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Explicit Skill", encoding="utf-8")
            (skill_dir / "requirements.txt").write_text("requests\n", encoding="utf-8")
            (skill_dir / "dependencies.json").write_text(json.dumps({
                "schemaVersion": 1,
                "skill": "explicit",
                "capabilities": {
                    "default": {"required": [{"type": "command", "name": "git"}]},
                },
            }), encoding="utf-8")

            manifest = dependencies.resolve_skill_manifest(skill_dir)

        self.assertEqual(manifest["source"], "local")
        requirement = manifest["capabilities"][0]["required"][0]
        self.assertEqual(requirement["id"], "command:git")

    def test_builds_managed_install_and_user_cooperation_guidance(self):
        inspection = {
            "capabilities": [{
                "id": "runtime",
                "required": [
                    {"id": "python:requests", "type": "python", "name": "requests", "minimumVersion": "2.28", "available": False},
                    {
                        "id": "command:pdftoppm",
                        "type": "command",
                        "name": "pdftoppm",
                        "available": False,
                        "installHint": "Windows PowerShell: winget install --id Poppler.Exact --exact",
                    },
                ],
                "optional": [],
            }],
        }
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            dependencies,
            "_managed_python",
            return_value=(r"C:\Python\python.exe", "system"),
        ):
            guidance = dependencies.build_install_guidance(inspection, data_dir=temp)

        self.assertTrue(guidance["needed"])
        self.assertEqual(guidance["runtime"]["python"]["source"], "system")
        self.assertEqual(guidance["runtime"]["python"]["executable"], r"C:\Python\python.exe")
        python_step = next(item for item in guidance["steps"] if item["type"] == "python")
        command_step = next(item for item in guidance["steps"] if item["type"] == "command")
        self.assertEqual(len(python_step["commands"]), 2)
        self.assertIn("venv", python_step["commands"][0]["command"])
        self.assertIn("requests>=2.28", python_step["commands"][1]["command"])
        self.assertEqual(command_step["strategy"], "user_cooperation")
        self.assertEqual(command_step["commands"], [])
        self.assertEqual(command_step["installHints"], [{
            "requirement": "command:pdftoppm",
            "text": "Windows PowerShell: winget install --id Poppler.Exact --exact",
        }])

    def test_ready_managed_dependency_keeps_runtime_execution_context(self):
        inspection = {
            "capabilities": [{
                "id": "runtime",
                "required": [{
                    "id": "python:demo",
                    "type": "python",
                    "name": "demo",
                    "available": True,
                    "source": "managed",
                }],
                "optional": [],
            }],
        }
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            dependencies,
            "_managed_python",
            return_value=(str(Path(temp) / "runtime" / "python" / "python.exe"), "managed"),
        ):
            guidance = dependencies.build_install_guidance(inspection, data_dir=temp)

        self.assertFalse(guidance["needed"])
        self.assertEqual(guidance["runtime"]["python"]["source"], "managed")
        self.assertTrue(guidance["runtime"]["python"]["executable"].endswith("python.exe"))

    def test_multi_capability_report_requires_one_explicit_selection(self):
        inspection = {
            "capabilities": [
                {
                    "id": "create",
                    "required": [{
                        "id": "node:docx",
                        "type": "node",
                        "name": "docx",
                        "available": True,
                    }],
                    "optional": [],
                },
                {
                    "id": "read",
                    "required": [{
                        "id": "command:pandoc",
                        "type": "command",
                        "name": "pandoc",
                        "available": False,
                    }],
                    "optional": [],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            report = dependencies.build_install_guidance(inspection, data_dir=temp)
            create = dependencies.build_install_guidance(
                inspection,
                data_dir=temp,
                capability_id="create",
            )
            read = dependencies.build_install_guidance(
                inspection,
                data_dir=temp,
                capability_id="read",
            )

        self.assertTrue(report["selectionRequired"])
        self.assertFalse(report["needed"])
        self.assertEqual(report["availableCapabilities"], ["create", "read"])
        self.assertEqual(report["steps"], [])
        self.assertFalse(create["selectionRequired"])
        self.assertFalse(create["needed"])
        self.assertEqual(create["selectedCapability"], "create")
        self.assertTrue(read["needed"])
        self.assertEqual(read["selectedCapability"], "read")
        self.assertEqual(read["requiredMissing"][0]["id"], "command:pandoc")
        self.assertEqual(read["steps"][0]["strategy"], "user_cooperation")

    def test_rejects_unknown_dependency_capability(self):
        inspection = {
            "capabilities": [{"id": "create", "required": [], "optional": []}],
        }
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(
            dependencies.DependencyManifestError
        ):
            dependencies.build_install_guidance(
                inspection,
                data_dir=temp,
                capability_id="render",
            )

    def test_rejects_wrong_schema_skill_and_dependency_type(self):
        cases = []
        wrong_schema = _manifest()
        wrong_schema["schemaVersion"] = 2
        cases.append(wrong_schema)
        wrong_skill = _manifest("other")
        cases.append(wrong_skill)
        wrong_type = _manifest()
        wrong_type["capabilities"]["create"]["required"][0]["type"] = "installer"
        cases.append(wrong_type)
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(dependencies.DependencyManifestError):
                dependencies.normalize_manifest(payload, expected_skill="demo")

    def test_bundled_manifest_is_fallback_for_existing_user_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local = root / "local" / "demo"
            bundled = root / "bundled" / "demo"
            local.mkdir(parents=True)
            bundled.mkdir(parents=True)
            (local / "SKILL.md").write_text("# existing user copy", encoding="utf-8")
            (bundled / "dependencies.json").write_text(json.dumps(_manifest()), encoding="utf-8")

            manifest = dependencies.load_skill_manifest(local, root / "bundled")

        self.assertEqual(manifest["source"], "bundled")
        self.assertEqual(manifest["skill"], "demo")


class TestDependencyInspection(unittest.TestCase):
    def test_reports_partial_status_and_optional_gaps(self):
        manifest = dependencies.normalize_manifest(_manifest(), expected_skill="demo")
        manifest["source"] = "local"
        with (
            mock.patch.object(dependencies, "_probe_python", return_value={
                "python:demo-python": {
                    "installed": True, "available": True, "detectedVersion": "1.0", "source": "system", "reason": "",
                }
            }),
            mock.patch.object(dependencies, "_probe_node", return_value={
                "node:demo-node": {
                    "installed": True, "available": True, "detectedVersion": "1.2.3", "source": "managed", "reason": "",
                }
            }),
            mock.patch.object(dependencies, "_probe_commands", return_value={
                "command:demo-cli": {
                    "installed": False, "available": False, "detectedVersion": "", "source": "", "reason": "not_installed",
                }
            }),
        ):
            result = dependencies.inspect_manifest(manifest, app_dir=".", data_dir=".")

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["capabilities"][0]["status"], "ready")
        self.assertEqual(result["capabilities"][0]["missingOptional"], 1)
        self.assertEqual(result["capabilities"][1]["status"], "unavailable")

    def test_managed_node_package_precedes_app_copy_and_checks_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            managed = root / "data" / "runtime" / "node" / "node_modules" / "demo-node"
            app_copy = root / "app" / "node_modules" / "demo-node"
            managed.mkdir(parents=True)
            app_copy.mkdir(parents=True)
            (managed / "package.json").write_text('{"version":"1.2.3"}', encoding="utf-8")
            (app_copy / "package.json").write_text('{"version":"9.9.9"}', encoding="utf-8")
            requirement = dependencies._normalize_requirement({
                "type": "node", "name": "demo-node", "version": "1.2.3",
            })

            result = dependencies._probe_node([requirement], root / "app", root / "data")

        self.assertTrue(result["node:demo-node"]["available"])
        self.assertEqual(result["node:demo-node"]["detectedVersion"], "1.2.3")
        self.assertEqual(result["node:demo-node"]["source"], "managed")

    def test_invalid_manifest_is_reported_without_hiding_valid_skills(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skills = root / "skills"
            valid = skills / "demo"
            invalid = skills / "broken"
            valid.mkdir(parents=True)
            invalid.mkdir(parents=True)
            for directory in (valid, invalid):
                (directory / "SKILL.md").write_text("# skill", encoding="utf-8")
            (valid / "dependencies.json").write_text(json.dumps(_manifest()), encoding="utf-8")
            (invalid / "dependencies.json").write_text("{bad json", encoding="utf-8")
            ready = {
                "name": "demo", "status": "ready", "manifestSource": "local", "capabilities": [],
            }
            with mock.patch.object(dependencies, "inspect_manifest", return_value=ready):
                result = dependencies.inspect_skill_dependencies(
                    skills,
                    bundled_skills_dir=root / "bundled",
                    app_dir=root,
                    data_dir=root / "data",
                )

        self.assertEqual(result["summary"], {"declared": 1, "ready": 1, "partial": 0, "unavailable": 0})
        self.assertEqual(result["skills"], [ready])
        self.assertEqual(result["errors"][0]["name"], "broken")


if __name__ == "__main__":
    unittest.main()
