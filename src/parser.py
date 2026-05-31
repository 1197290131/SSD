# SSD Test Log Parser
# 解析 smi_test.log 格式，提取结构化测试数据
import re
from datetime import datetime
from typing import Iterator


def parse_log(filepath: str) -> list[dict]:
    """解析 .log 文件，返回测试记录列表"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return list(_parse_sessions(text))


# ── 正则 ──────────────────────────────────────────
_RE_SESSION = re.compile(
    r"Session #(\d+) Started\n"
    r".*?Model: (\S+)\n"
    r".*?FW Version: (\S+)\n"
    r".*?Serial Number: (\S+)",
    re.DOTALL,
)
_RE_TIMESTAMP = re.compile(r"\[(.+?)\]")
_RE_TEST = re.compile(r"\[TEST\] Test Item: (.+)")
_RE_RESULT = re.compile(
    r"\[RESULT\] ("
    r"Speed=([\d.]+) MB/s  Temperature=([\d.]+) C  Status=(\w+)"
    r"|"
    r"IOPS=(\d+)  AvgLatency=([\d.]+) us  Status=(\w+)"
    r"|"
    r"MaxTemp=([\d.]+) C  AvgTemp=([\d.]+) C  Status=(\w+)"
    r"|"
    r"ReallocatedSectors=(\d+)  PendingSectors=(\d+)  WearLevel=(\d+)%  RawReadErrors=(\d+)  Status=(\w+)"
    r"|"
    r"ActivePower=([\d.]+) W  IdlePower=([\d.]+) W  Status=(\w+)"
    r")"
)
_RE_SUMMARY = re.compile(r"Elapsed: (\d+)s  Overall: (\w+)")


def _parse_sessions(text: str) -> Iterator[dict]:
    sessions = _RE_SESSION.finditer(text)
    for m in sessions:
        session_num = int(m.group(1))
        model = m.group(2)
        fw = m.group(3)
        serial = m.group(4)

        # 定位该 session 的文本块
        start = m.start()
        end = text.find("\n\n", start)
        block = text[start : end] if end > start else text[start:]

        records = list(_parse_records(block))
        summary = _RE_SUMMARY.search(block)

        yield {
            "session": session_num,
            "model": model,
            "fw": fw,
            "serial": serial,
            "records": records,
            "elapsed": int(summary.group(1)) if summary else None,
            "overall": summary.group(2) if summary else None,
        }


def _parse_records(block: str) -> Iterator[dict]:
    lines = block.split("\n")
    current_test = None
    for line in lines:
        test_m = _RE_TEST.search(line)
        if test_m:
            current_test = test_m.group(1)
            continue
        result_m = _RE_RESULT.search(line)
        if result_m and current_test:
            yield _extract_fields(result_m, current_test)
            current_test = None


def _extract_fields(m: re.Match, test_name: str) -> dict:
    raw = m.group(1)
    record = {"test_item": test_name}

    if "Speed=" in raw:
        record["type"] = "throughput"
        record["speed_mbps"] = float(m.group(2))
        record["temperature_c"] = float(m.group(3))
        record["status"] = m.group(4)

    elif "IOPS=" in raw:
        record["type"] = "iops"
        record["iops"] = int(m.group(5))
        record["avg_latency_us"] = float(m.group(6))
        record["status"] = m.group(7)

    elif "MaxTemp=" in raw:
        record["type"] = "temperature"
        record["max_temp_c"] = float(m.group(8))
        record["avg_temp_c"] = float(m.group(9))
        record["status"] = m.group(10)

    elif "ReallocatedSectors=" in raw:
        record["type"] = "smart"
        record["reallocated_sectors"] = int(m.group(11))
        record["pending_sectors"] = int(m.group(12))
        record["wear_level_pct"] = int(m.group(13))
        record["raw_read_errors"] = int(m.group(14))
        record["status"] = m.group(15)

    elif "ActivePower=" in raw:
        record["type"] = "power"
        record["active_power_w"] = float(m.group(16))
        record["idle_power_w"] = float(m.group(17))
        record["status"] = m.group(18)

    return record


# ── 独立运行测试 ──────────────────────────────────
if __name__ == "__main__":
    data = parse_log("samples/smi_test.log")
    print(f"解析到 {len(data)} 个测试会话\n")
    for s in data:
        print(f"Session #{s['session']} | {s['model']} | {s['serial']} | Overall: {s['overall']}")
        for r in s["records"]:
            print(f"  {r['test_item']:40s} | {r['type']:15s} | {r['status']}")
        print()
