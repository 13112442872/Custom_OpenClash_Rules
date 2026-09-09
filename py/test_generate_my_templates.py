import re
import unittest

from generate_my_templates import AI_FALLBACK, GENERAL_FALLBACK, transform


AI_GROUPS = ("🤖 ChatGPT", "🤖 AI服务")
SAMPLE = """[custom]
;设置节点分组标志位
custom_proxy_group=🚀 手动选择`select`[]♻️ 自动选择`.*
custom_proxy_group=♻️ 自动选择`url-test`.*`https://example.test`300
custom_proxy_group=🤖 ChatGPT`select`[]🚀 手动选择`.*
custom_proxy_group=🤖 AI服务`select`[]♻️ 自动选择`.*
custom_proxy_group=🤖 国内AI服务`select`[]🎯 全球直连`.*
custom_proxy_group=🇺🇸 美国节点`url-test`(🇺🇸|美国|\\bUS\\b|USA|洛杉矶)`https://example.test`300
;设置分组标志位
"""


def find_group(text: str, name: str) -> str:
    prefix = f"custom_proxy_group={name}`"
    return next(line for line in text.splitlines() if line.startswith(prefix))


class GenerateMyTemplatesTest(unittest.TestCase):
    def test_adds_groups_and_routes_overseas_ai_first(self) -> None:
        result = transform(SAMPLE, AI_GROUPS)

        self.assertEqual(result.count(f"custom_proxy_group={GENERAL_FALLBACK}`"), 1)
        self.assertEqual(result.count(f"custom_proxy_group={AI_FALLBACK}`"), 1)
        manual_members = find_group(result, "🚀 手动选择").split("`")[2:]
        self.assertEqual(manual_members.count(f"[]{GENERAL_FALLBACK}"), 1)
        self.assertEqual(manual_members[:2], ["[]♻️ 自动选择", f"[]{GENERAL_FALLBACK}"])
        for name in AI_GROUPS:
            self.assertEqual(find_group(result, name).split("`")[2], f"[]{AI_FALLBACK}")
        self.assertEqual(find_group(result, "🤖 国内AI服务"), find_group(SAMPLE, "🤖 国内AI服务"))

        pattern = re.compile(find_group(result, AI_FALLBACK).split("`")[2])
        for node in ("美国 01", "🇺🇸 节点", "US 02", "洛杉矶专线", "香港 CF官方 01", "CF官方-专线"):
            self.assertIsNotNone(pattern.search(node), node)
        for node in ("日本节点", "香港 CF 01", "Cloudflare 香港"):
            self.assertIsNone(pattern.search(node), node)

    def test_keeps_existing_fallbacks_and_is_idempotent(self) -> None:
        existing_general = "custom_proxy_group=🚀 故障转移`fallback`[]保留此配置`https://old.test`60"
        existing_ai = "custom_proxy_group=🤖 AI故障转移`fallback`CF官方`https://old.test`60"
        source = SAMPLE.replace(
            ";设置节点分组标志位\n",
            f";设置节点分组标志位\n{existing_general}\n{existing_ai}\n",
        )

        result = transform(source, AI_GROUPS)
        self.assertIn(existing_general, result)
        self.assertIn(existing_ai, result)
        self.assertEqual(result.count(f"custom_proxy_group={GENERAL_FALLBACK}`"), 1)
        self.assertEqual(result.count(f"custom_proxy_group={AI_FALLBACK}`"), 1)
        self.assertEqual(transform(result, AI_GROUPS), result)

    def test_rejects_changed_template_structure(self) -> None:
        with self.assertRaises(ValueError):
            transform(SAMPLE.replace("🇺🇸 美国节点", "🇺🇸 北美节点"), AI_GROUPS)
        with self.assertRaises(ValueError):
            transform(SAMPLE.replace(";设置分组标志位", ""), AI_GROUPS)


if __name__ == "__main__":
    unittest.main()
