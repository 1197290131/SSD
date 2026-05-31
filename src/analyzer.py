# SSD Test Log Analyzer — 业务逻辑层
# 数据清洗、统计计算、异常标记
from collections import defaultdict


def analyze(sessions: list[dict]) -> dict:
    """对解析后的会话数据做统计分析，返回汇总结果"""
    records = [{**r, "session": s["session"]} for s in sessions for r in s["records"]]
    return {
        "sessions": _session_summary(sessions),
        "raw_sessions": sessions,
        "by_type": _group_stats(records),
        "anomalies": _find_anomalies(records),
        "summary": _overall_summary(sessions, records),
    }


# ── 会话汇总 ──────────────────────────────────────
def _session_summary(sessions: list[dict]) -> list[dict]:
    return [
        {
            "session": s["session"],
            "model": s["model"],
            "serial": s["serial"],
            "overall": s["overall"],
            "elapsed": s["elapsed"],
        }
        for s in sessions
    ]


# ── 按类型分组统计 ─────────────────────────────────
def _group_stats(records: list[dict]) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[r["type"]].append(r)

    stats = {}
    for t, items in groups.items():
        stats[t] = _compute(t, items)
    return stats


def _compute(type_: str, items: list[dict]) -> dict:
    """对某个测试类型计算聚合统计"""
    base = {"count": len(items), "pass_count": sum(1 for r in items if r["status"] == "PASS")}

    if type_ == "throughput":
        speeds = [r["speed_mbps"] for r in items]
        temps = [r["temperature_c"] for r in items]
        base.update({
            "avg_speed_mbps": _mean(speeds), "max_speed_mbps": max(speeds), "min_speed_mbps": min(speeds),
            "avg_temperature_c": _mean(temps), "max_temperature_c": max(temps),
        })

    elif type_ == "iops":
        iops = [r["iops"] for r in items]
        lats = [r["avg_latency_us"] for r in items]
        base.update({
            "avg_iops": int(_mean(iops)), "max_iops": max(iops), "min_iops": min(iops),
            "avg_latency_us": _mean(lats), "max_latency_us": max(lats),
        })

    elif type_ == "temperature":
        maxs = [r["max_temp_c"] for r in items]
        avgs = [r["avg_temp_c"] for r in items]
        base.update({
            "avg_max_temp_c": _mean(maxs), "peak_temp_c": max(maxs),
            "avg_avg_temp_c": _mean(avgs),
        })

    elif type_ == "smart":
        base.update({
            "total_reallocated": sum(r["reallocated_sectors"] for r in items),
            "total_pending": sum(r["pending_sectors"] for r in items),
            "total_read_errors": sum(r["raw_read_errors"] for r in items),
        })

    elif type_ == "power":
        base.update({
            "avg_active_power_w": _mean([r["active_power_w"] for r in items]),
            "avg_idle_power_w": _mean([r["idle_power_w"] for r in items]),
        })

    return base


# ── 异常检测 ──────────────────────────────────────
_ANOMALY_RULES = {
    "throughput": [
        ("seq_read_slow", lambda r: "Read" in r["test_item"] and r["speed_mbps"] < 3000),
        ("seq_write_slow", lambda r: "Write" in r["test_item"] and r["speed_mbps"] < 2600),
    ],
    "iops": [
        ("low_random_read_iops", lambda r: "Read" in r["test_item"] and r["iops"] < 350000),
        ("low_random_write_iops", lambda r: "Write" in r["test_item"] and r["iops"] < 300000),
        ("high_latency", lambda r: r["avg_latency_us"] > 200),
    ],
    "temperature": [
        ("overheating", lambda r: r["max_temp_c"] > 80),
    ],
    "smart": [
        ("excessive_reallocated", lambda r: r["reallocated_sectors"] > 20),
        ("pending_sectors_warn", lambda r: r["pending_sectors"] > 5),
    ],
}


def _find_anomalies(records: list[dict]) -> list[dict]:
    anomalies = []
    for r in records:
        rules = _ANOMALY_RULES.get(r["type"], [])
        for rule_name, fn in rules:
            if fn(r):
                anomalies.append({
                    "session": r.get("session"),
                    "test_item": r["test_item"],
                    "type": r["type"],
                    "rule": rule_name,
                    "status": r["status"],
                })
    return anomalies


# ── 总体概况 ──────────────────────────────────────
def _overall_summary(sessions: list[dict], records: list[dict]) -> dict:
    return {
        "total_sessions": len(sessions),
        "total_records": len(records),
        "pass_rate": f"{sum(1 for r in records if r['status'] == 'PASS') / len(records) * 100:.1f}%",
        "anomaly_count": len(_find_anomalies(records)),
        "models": sorted({s["model"] for s in sessions}),
    }


def _mean(nums: list[float]) -> float:
    return round(sum(nums) / len(nums), 2)


# ── 独立测试 ──────────────────────────────────────
if __name__ == "__main__":
    from parser import parse_log
    data = parse_log("samples/smi_test.log")
    result = analyze(data)
    print(f"会话数: {result['summary']['total_sessions']}")
    print(f"记录数: {result['summary']['total_records']}")
    print(f"通过率: {result['summary']['pass_rate']}")
    print(f"异常数: {result['summary']['anomaly_count']}")
    print(f"型号:   {', '.join(result['summary']['models'])}")
    print()
    for t, s in result["by_type"].items():
        print(f"[{t}] {s}")
    print()
    if result["anomalies"]:
        print("=== 异常列表 ===")
        for a in result["anomalies"]:
            print(f"  Session #{a['session']} | {a['rule']} | {a['test_item']}")
