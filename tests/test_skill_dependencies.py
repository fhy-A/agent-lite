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
                    {"type": "command", "name": "demo-cli"},
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
