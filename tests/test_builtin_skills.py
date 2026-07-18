import unittest

import server as server_mod


class TestBuiltInSkillRouting(unittest.TestCase):
    def skill_names_for(self, prompt):
        return [skill["name"] for skill in server_mod.match_skills(prompt)]

    def test_description_words_do_not_trigger_automatic_loading(self):
        self.assertEqual(
            self.skill_names_for("解释一下 Python 装饰器的工作原理"),
            [],
        )

    def test_representative_prompts_route_to_one_specific_skill(self):
        cases = {
            "帮我审查 server.py 的改动，找出潜在 bug": ["code-review"],
            "为 parser.py 补充 pytest 单元测试并运行": ["python-testing"],
            "读取 docs/report.pdf 并提取前三页内容": ["office-files"],
            "生成一份正式的 Word 项目周报": ["document-design"],
            "用 matplotlib 画一张月度销量折线图": ["image-generation"],
            "重新设计欢迎页的布局和视觉样式": ["design-aesthetics"],
            "根据截图分析按钮为什么错位，只需要诊断": ["design-aesthetics"],
            "这条代码审查意见建议删除兼容层，帮我判断是否合理": ["receiving-code-review"],
            "有没有适合做 React 性能优化的 Skill": ["find-skills"],
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(self.skill_names_for(prompt), expected)

    def test_action_requests_do_not_load_review_or_chart_skills(self):
        prompts = (
            "server.py 有个 bug，帮我直接修复",
            "修复上传接口的路径遍历漏洞",
            "生成一张未来城市的 AI 海报",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertEqual(self.skill_names_for(prompt), [])


class TestBuiltInSkillMetadata(unittest.TestCase):
    def test_declared_tools_are_available_in_code(self):
        available = set(server_mod.SERVER_TOOL_REGISTRY)
        for skill in server_mod.list_skills(brief=True):
            with self.subTest(skill=skill["name"]):
                self.assertLessEqual(set(skill.get("tools") or []), available)

    def test_skill_name_matches_directory(self):
        for skill in server_mod.list_skills(brief=True):
            with self.subTest(skill=skill["name"]):
                self.assertEqual(skill["name"], skill["dir"])


if __name__ == "__main__":
    unittest.main()
