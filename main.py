#!/usr/bin/env python3
"""
SSD Test Log Analyzer — 命令行入口

V2 新特性: 支持配置文件驱动（YAML），可适配不同主控方案的日志格式和异常阈值。
用法:
    python main.py <日志文件>                          # 使用默认配置
    python main.py <日志文件> -c config_smi.yaml       # 指定配置文件
    python main.py <日志文件> -o output/report.html    # 指定输出路径
"""
import sys
import os
import argparse

# 确保能找到 src 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config_loader import load_config
from parser import parse_log
from analyzer import analyze
from reporter import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="SSD 产线测试日志分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python main.py samples/smi_test.log\n"
            "  python main.py samples/smi_test.log -c config_smi.yaml\n"
            "  python main.py samples/smi_test.log -o output/report.html -c my_config.yaml\n"
        ),
    )
    parser.add_argument("log_file", nargs="?", help="日志文件路径")
    parser.add_argument("-o", "--output", default="output/report.html", help="输出路径（默认: output/report.html）")
    parser.add_argument("-c", "--config", default=None, help="配置文件路径（默认: 查找 config*.yaml 或使用内置配置）")
    args = parser.parse_args()

    # ── 加载配置 ──────────────────────────────────
    cfg = load_config(args.config)
    device = cfg.get("device", {})
    parsing_cfg = cfg["parsing"]
    anomaly_rules = cfg.get("anomaly_rules", [])

    # ── 日志文件 ──────────────────────────────────
    if not args.log_file:
        print("[ERROR] 请指定日志文件路径")
        print("  用法: python main.py <日志文件> [-c 配置] [-o 输出]")
        sys.exit(1)

    log_path = args.log_file
    output_path = args.output
    output_dir = os.path.dirname(output_path) or "."

    if not os.path.exists(log_path):
        print(f"[ERROR] 文件不存在: {log_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # ── 执行流水线 ────────────────────────────────
    dev_info = f"{device.get('vendor', '')} {device.get('name', '')}".strip()
    print(f"设备: {dev_info or '通用 SSD'}")
    print(f"配置: {parsing_cfg['result_types'].keys()}")
    print()

    print(f"[1/3] 解析日志: {log_path}")
    sessions = parse_log(log_path, parsing_cfg)
    print(f"      -> {len(sessions)} 个测试会话")

    print(f"[2/3] 分析数据...")
    result = analyze(sessions, anomaly_rules)
    s = result["summary"]
    print(f"      -> 通过率: {s['pass_rate']}, 异常: {s['anomaly_count']} 项")

    print(f"[3/3] 生成报告: {output_path}")
    generate_report(result, output_path, config=device)

    print(f"\n[DONE] 报告已保存，用浏览器打开即可查看")


if __name__ == "__main__":
    main()
