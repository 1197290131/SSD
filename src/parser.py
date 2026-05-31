"""
SSD Test Log Parser

从产测日志中提取结构化测试数据。
支持配置驱动——正则模板和字段映射从 config 获取，未提供配置时使用内置默认值。
"""
import re
from typing import Callable, Iterator

from config_loader import _default_config


def parse_log(filepath: str, parsing_config: dict | None = None) -> list[dict]:
    """解析 .log 文件，返回测试会话列表

    Args:
        filepath: 日志文件路径
        parsing_config: 解析配置字典（config['parsing']），为 None 时使用默认配置
    """
    if parsing_config is None:
        parsing_config = _default_config()["parsing"]

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    return list(_parse_sessions(text, parsing_config))


# ── 内部实现 ──────────────────────────────────────────


def _parse_sessions(text: str, cfg: dict) -> Iterator[dict]:
    session_re = re.compile(cfg["session_header"], re.DOTALL)
    summary_re = re.compile(cfg["summary"])
    test_re = re.compile(cfg["test_item"])

    # 预编译每种 result_type 的正则
    type_matchers: list[tuple[str, dict, re.Pattern]] = []
    for tname, tcfg in cfg["result_types"].items():
        type_matchers.append((tname, tcfg, re.compile(tcfg["regex"])))

    for m in session_re.finditer(text):
        session_num = int(m.group(1))
        model = m.group(2)
        fw = m.group(3)
        serial = m.group(4)

        start = m.start()
        end = text.find("\n\n", start)
        block = text[start:end] if end > start else text[start:]

        records = list(_parse_records(block, test_re, type_matchers))
        summary_m = summary_re.search(block)

        yield {
            "session": session_num,
            "model": model,
            "fw": fw,
            "serial": serial,
            "records": records,
            "elapsed": int(summary_m.group(1)) if summary_m else None,
            "overall": summary_m.group(2) if summary_m else None,
        }


def _parse_records(
    block: str,
    test_re: re.Pattern,
    type_matchers: list[tuple[str, dict, re.Pattern]],
) -> Iterator[dict]:
    """逐行匹配，遇到 [TEST] 记录当前测试项，下一行尝试匹配各 result_type"""
    lines = block.split("\n")
    current_test: str | None = None

    for line in lines:
        test_m = test_re.search(line)
        if test_m:
            current_test = test_m.group(1)
            continue

        if current_test is None:
            continue

        for type_name, type_cfg, pattern in type_matchers:
            m = pattern.search(line)
            if m:
                yield _extract_fields(type_name, type_cfg, m, current_test)
                current_test = None
                break


def _extract_fields(type_name: str, type_cfg: dict, m: re.Match, test_name: str) -> dict:
    """根据配置的字段名和类型，从正则匹配结果中提取数据"""
    record: dict = {
        "test_item": test_name,
        "type": type_name,
    }

    fields: list[str] = type_cfg["fields"]
    ftypes: list[str] = type_cfg.get("field_types", ["str"] * len(fields))

    _cast_map: dict[str, Callable] = {
        "int": int,
        "float": float,
        "str": str,
    }

    for i, field_name in enumerate(fields):
        raw_val = m.group(i + 1)  # capture groups 从 1 开始
        caster = _cast_map.get(ftypes[i] if i < len(ftypes) else "str", str)
        record[field_name] = caster(raw_val)

    return record


# ── 独立测试 ──────────────────────────────────────────
if __name__ == "__main__":
    data = parse_log("samples/smi_test.log")
    print(f"解析到 {len(data)} 个测试会话\n")
    for s in data:
        print(f"Session #{s['session']} | {s['model']} | {s['serial']} | Overall: {s['overall']}")
        for r in s["records"]:
            print(f"  {r['test_item']:40s} | {r['type']:15s} | {r.get('status', '?')}")
        print()
