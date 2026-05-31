"""
配置加载模块
从 YAML 文件加载解析规则和异常阈值，未找到文件时使用内置默认配置
"""
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[WARN] pyyaml 未安装，使用内置默认配置。安装: pip install pyyaml")
    yaml = None


def load_config(path: str | None = None) -> dict:
    """加载配置文件，返回配置字典"""
    if path:
        return _load_file(path)

    # 按优先级查找配置文件
    # 检查 src/config_smi.yaml
    src_cfg = Path(__file__).parent / "config_smi.yaml"
    if src_cfg.exists():
        return _load_file(str(src_cfg))
    else:
        return _default_config()


def get_config_path() -> str | None:
    """查找当前目录下的配置文件"""
    for name in ("config_smi.yaml", "config.yaml"):
        p = Path(name)
        if p.exists():
            return str(p)
    return None


def _load_file(path: str) -> dict:
    if yaml is None:
        print(f"[ERROR] 需要 pyyaml 才能加载配置文件: {path}")
        print("[INFO]  安装: pip install pyyaml")
        sys.exit(1)

    path = Path(path)
    if not path.exists():
        print(f"[WARN] 配置文件不存在: {path}，使用默认配置")
        return _default_config()

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    _validate(cfg)
    return cfg


def _validate(cfg: dict):
    """基本结构校验"""
    if not isinstance(cfg, dict):
        raise ValueError("配置文件必须是一个字典")

    required_top = ["parsing"]
    for key in required_top:
        if key not in cfg:
            raise ValueError(f"配置缺少必要字段: '{key}'")

    if "result_types" not in cfg.get("parsing", {}):
        raise ValueError("配置 parsing.result_types 不能为空")

    if "anomaly_rules" not in cfg:
        cfg["anomaly_rules"] = []

    # 补全 device 信息
    if "device" not in cfg:
        cfg["device"] = {"name": "Generic SSD", "vendor": "Unknown", "controller": "Unknown"}


def _default_config() -> dict:
    """内置默认配置（等同于 config_smi.yaml + v1 硬编码规则）"""
    return {
        "device": {
            "name": "SMI SSD",
            "vendor": "Silicon Motion",
            "controller": "SMI",
        },
        "parsing": {
            "session_header": (
                r"Session #(\d+) Started\n"
                r".*?Model: (\S+)\n"
                r".*?FW Version: (\S+)\n"
                r".*?Serial Number: (\S+)"
            ),
            "test_item": r"\[TEST\] Test Item: (.+)",
            "summary": r"Elapsed: (\d+)s  Overall: (\w+)",
            "result_types": {
                "throughput": {
                    "regex": r"Speed=([\d.]+) MB/s\s+Temperature=([\d.]+) C\s+Status=(\w+)",
                    "fields": ["speed_mbps", "temperature_c", "status"],
                    "field_types": ["float", "float", "str"],
                },
                "iops": {
                    "regex": r"IOPS=(\d+)\s+AvgLatency=([\d.]+) us\s+Status=(\w+)",
                    "fields": ["iops", "avg_latency_us", "status"],
                    "field_types": ["int", "float", "str"],
                },
                "temperature": {
                    "regex": r"MaxTemp=([\d.]+) C\s+AvgTemp=([\d.]+) C\s+Status=(\w+)",
                    "fields": ["max_temp_c", "avg_temp_c", "status"],
                    "field_types": ["float", "float", "str"],
                },
                "smart": {
                    "regex": r"ReallocatedSectors=(\d+)\s+PendingSectors=(\d+)\s+WearLevel=(\d+)%\s+RawReadErrors=(\d+)\s+Status=(\w+)",
                    "fields": ["reallocated_sectors", "pending_sectors", "wear_level_pct", "raw_read_errors", "status"],
                    "field_types": ["int", "int", "int", "int", "str"],
                },
                "power": {
                    "regex": r"ActivePower=([\d.]+) W\s+IdlePower=([\d.]+) W\s+Status=(\w+)",
                    "fields": ["active_power_w", "idle_power_w", "status"],
                    "field_types": ["float", "float", "str"],
                },
            },
        },
        "anomaly_rules": [
            {"name": "seq_read_slow", "label": "顺序读性能不足", "enabled": True,
             "record_type": "throughput",
             "conditions": [{"field": "speed_mbps", "operator": "<", "value": 3000},
                            {"field": "test_item", "operator": "contains", "value": "Read"}]},
            {"name": "seq_write_slow", "label": "顺序写性能不足", "enabled": True,
             "record_type": "throughput",
             "conditions": [{"field": "speed_mbps", "operator": "<", "value": 2600},
                            {"field": "test_item", "operator": "contains", "value": "Write"}]},
            {"name": "low_random_read_iops", "label": "随机读IOPS偏低", "enabled": True,
             "record_type": "iops",
             "conditions": [{"field": "iops", "operator": "<", "value": 350000},
                            {"field": "test_item", "operator": "contains", "value": "Read"}]},
            {"name": "low_random_write_iops", "label": "随机写IOPS偏低", "enabled": True,
             "record_type": "iops",
             "conditions": [{"field": "iops", "operator": "<", "value": 300000},
                            {"field": "test_item", "operator": "contains", "value": "Write"}]},
            {"name": "high_latency", "label": "延迟过高", "enabled": True,
             "record_type": "iops",
             "conditions": [{"field": "avg_latency_us", "operator": ">", "value": 200}]},
            {"name": "overheating", "label": "温度超标", "enabled": True,
             "record_type": "temperature",
             "conditions": [{"field": "max_temp_c", "operator": ">", "value": 80}]},
            {"name": "excessive_reallocated", "label": "坏块过多", "enabled": True,
             "record_type": "smart",
             "conditions": [{"field": "reallocated_sectors", "operator": ">", "value": 20}]},
            {"name": "pending_sectors_warn", "label": "待重映射扇区过多", "enabled": True,
             "record_type": "smart",
             "conditions": [{"field": "pending_sectors", "operator": ">", "value": 5}]},
        ],
    }


# ── 独立测试 ──
if __name__ == "__main__":
    cfg = load_config()
    print(f"设备: {cfg['device']['vendor']} {cfg['device']['name']}")
    print(f"解析规则: {len(cfg['parsing']['result_types'])} 种类型")
    print(f"异常规则: {len(cfg['anomaly_rules'])} 条")
