#!/usr/bin/env python3
"""Generate the two custom OpenClash subconverter templates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GROUP_PREFIX = "custom_proxy_group="
GROUP_START = ";设置节点分组标志位"
GROUP_END = ";设置分组标志位"
GENERAL_FALLBACK = "🚀 故障转移"
AI_FALLBACK = "🤖 AI故障转移"
PROBE = "https://cp.cloudflare.com/generate_204"
TEMPLATES = {
    "Custom_Clash.ini": ("🤖 ChatGPT", "🤖 AI服务"),
    "Custom_Clash_Full.ini": ("🤖 ChatGPT", "🤖 Copilot", "🤖 国外AI服务"),
}


def group_name(line: str) -> str | None:
    if not line.startswith(GROUP_PREFIX):
        return None
    return line[len(GROUP_PREFIX) :].split("`", 1)[0]


def only_group(lines: list[str], start: int, end: int, name: str) -> int:
    matches = [i for i in range(start + 1, end) if group_name(lines[i]) == name]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one active {name!r} group, found {len(matches)}")
    return matches[0]


def transform(text: str, ai_groups: tuple[str, ...]) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    trailing_newline = text.endswith(("\n", "\r"))
    lines = text.splitlines()

    if lines.count(GROUP_START) != 1 or lines.count(GROUP_END) != 1:
        raise ValueError("node group markers are missing or duplicated")
    start = lines.index(GROUP_START)
    end = lines.index(GROUP_END, start + 1)

    us_index = only_group(lines, start, end, "🇺🇸 美国节点")
    us_fields = lines[us_index].split("`")
    if len(us_fields) < 3 or not us_fields[2]:
        raise ValueError("the US node group has no node-matching expression")
    us_pattern = us_fields[2]

    manual_index = only_group(lines, start, end, "🚀 手动选择")
    manual_fields = lines[manual_index].split("`")
    fallback_member = f"[]{GENERAL_FALLBACK}"
    if fallback_member not in manual_fields[2:]:
        try:
            auto_member_index = manual_fields.index("[]♻️ 自动选择", 2)
        except ValueError as error:
            raise ValueError("the manual group has no auto-select member") from error
        manual_fields.insert(auto_member_index + 1, fallback_member)
        lines[manual_index] = "`".join(manual_fields)

    for name in ai_groups:
        index = only_group(lines, start, end, name)
        if f"[]{AI_FALLBACK}" not in lines[index]:
            fields = lines[index].split("`")
            if len(fields) < 3:
                raise ValueError(f"cannot add the AI fallback to {name!r}")
            fields.insert(2, f"[]{AI_FALLBACK}")
            lines[index] = "`".join(fields)

    existing_groups = {
        name for line in lines[start + 1 : end] if (name := group_name(line)) is not None
    }
    additions = []
    if GENERAL_FALLBACK not in existing_groups:
        additions.append(
            f"{GROUP_PREFIX}{GENERAL_FALLBACK}`fallback`.*`{PROBE}`300,5"
        )
    if AI_FALLBACK not in existing_groups:
        additions.append(
            f"{GROUP_PREFIX}{AI_FALLBACK}`fallback`(?:{us_pattern}|CF官方)`{PROBE}`300,5"
        )

    if additions:
        auto_index = only_group(lines, start, end, "♻️ 自动选择")
        lines[auto_index + 1 : auto_index + 1] = additions

    result = newline.join(lines)
    return result + newline if trailing_newline else result


def generate(source: Path, destination: Path, ai_groups: tuple[str, ...]) -> None:
    raw = source.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    generated = transform(text, ai_groups).encode("utf-8")
    destination.write_bytes((b"\xef\xbb\xbf" if has_bom else b"") + generated)


def main() -> None:
    for source_name, ai_groups in TEMPLATES.items():
        source = ROOT / "cfg" / source_name
        destination = source.with_name(f"my_{source.name}")
        generate(source, destination, ai_groups)
        print(f"generated {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
