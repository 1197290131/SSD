"""
SSD Test Log Analyzer — 业务逻辑层

数据清洗、统计计算、异常标记。
异常规则从 config 加载（field / operator / value 结构），
未提供配置时使用内置默认规则（与 v1 一致）。
"""
from collections import defaultdict

from config_loader import _default_config


def analyze(sessions: list[dict], anomaly_rules: list | None = None) -> dict:
    """对解析后的会话数据做统计分析，返回汇总结果

    Args:
        sessions: 解析后的会话列表
        anomaly_rules: 异常规则列表（config['anomaly_rules']），为 None 时使用默认规则
    """
    if anomaly_rules is None:
        anomaly_rules = _default_config()["anomaly_rules"]

    records = [{**r, "session": s["session"]} for s in sessions for r in s["records"]]
    enabled_rules = [r for r in anomaly_rules if r.get("enabled", True)]

    return {
        "sessions": _session_summary(sessions),
        "raw_sessions": sessions,
        "by_type": _group_stats(records),
        "anomalies": _find_anomalies(records, enabled_rules),
        "summary": _overall_summary(sessions, records, enabled_rules),
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


def _mean(nums: list[float]) -> float:
    return round(sum(nums) / len(nums), 2) if nums else 0.0


def _compute(type_: str, items: list[dict]) -> dict:
    """对某个测试类型计算聚合统计"""
    base = {
        "count": len(items),
        "pass_count": sum(1 for r in items if r["status"] == "PASS"),
        "warn_count": sum(1 for r in items if r["status"] == "WARN"),
        "fail_count": sum(1 for r in items if r["status"] == "FAIL"),
    }

    if type_ == "throughput":
        speeds = [r["speed_mbps"] for r in items]
        temps = [r["temperature_c"] for r in items]
        base.update({
            "avg_speed_mbps": _mean(speeds),
            "max_speed_mbps": max(speeds),
            "min_speed_mbps": min(speeds),
            "avg_temperature_c": _mean(temps),
            "max_temperature_c": max(temps),
        })

    elif type_ == "iops":
        iops = [r["iops"] for r in items]
        lats = [r["avg_latency_us"] for r in items]
        base.update({
            "avg_iops": int(_mean(iops)),
            "max_iops": max(iops),
            "min_iops": min(iops),
            "avg_latency_us": _mean(lats),
            "max_latency_us": max(lats),
        })

    elif type_ == "temperature":
        maxs = [r["max_temp_c"] for r in items]
        avgs = [r["avg_temp_c"] for r in items]
        base.update({
            "avg_max_temp_c": _mean(maxs),
            "peak_temp_c": max(maxs),
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


# ── 配置驱动的异常检测 ──────────────────────────────


def _evaluate_condition(record: dict, condition: dict) -> bool:
    """求值一条条件: field operator value

    支持的运算符: <, >, <=, >=, ==, !=, contains
    """
    field = condition["field"]
    operator = condition["operator"]
    value = condition["value"]

    field_val = record.get(field)

    if operator == "<":
        return field_val is not None and field_val < value
    elif operator == ">":
        return field_val is not None and field_val > value
    elif operator == "<=":
        return field_val is not None and field_val <= value
    elif operator == ">=":
        return field_val is not None and field_val >= value
    elif operator == "==":
        return field_val is not None and field_val == value
    elif operator == "!=":
        return field_val is not None and field_val != value
    elif operator == "contains":
        return value in str(field_val)
    else:
        raise ValueError(f"不支持的运算符: {operator}")


def _match_rule(record: dict, rule: dict) -> bool:
    """判断一条记录是否命中规则（所有 conditions 同时满足 → AND 语义）"""
    if record.get("type") != rule.get("record_type"):
        return False
    for cond in rule.get("conditions", []):
        if not _evaluate_condition(record, cond):
            return False
    return True


def _find_anomalies(records: list[dict], rules: list[dict]) -> list[dict]:
    """遍历所有记录和规则，返回命中的异常列表"""
    anomalies = []
    for r in records:
        for rule in rules:
            if _match_rule(r, rule):
                anomalies.append({
                    "session": r.get("session"),
                    "test_item": r["test_item"],
                    "type": r["type"],
                    "rule": rule["name"],
                    "label": rule.get("label", rule["name"]),
                    "status": r["status"],
                })
    return anomalies


# ── 总体概况 ──────────────────────────────────────


def _overall_summary(sessions: list[dict], records: list[dict], rules: list[dict]) -> dict:
    total = len(records)
    return {
        "total_sessions": len(sessions),
        "total_records": total,
        "pass_rate": f"{sum(1 for r in records if r['status'] == 'PASS') / total * 100:.1f}%" if total else "N/A",
        "anomaly_count": len(_find_anomalies(records, rules)),
        "models": sorted({s["model"] for s in sessions}),
    }


# ── 独立测试 ──────────────────────────────────────
if __name__ == "__main__":
    from parser import parse_log

    data = parse_log("samples/smi_test.log")
    result = analyze(data)
    s = result["summary"]
    print(f"会话数: {s['total_sessions']}")
    print(f"记录数: {s['total_records']}")
    print(f"通过率: {s['pass_rate']}")
    print(f"异常数: {s['anomaly_count']}")
    print(f"型号:   {', '.join(s['models'])}")
    print()
    for t, st in result["by_type"].items():
        print(f"[{t}] {st}")
    print()
    if result["anomalies"]:
        print("=== 异常列表 ===")
        for a in result["anomalies"]:
            print(f"  Session #{a['session']} | {a['rule']} | {a['test_item']}")
