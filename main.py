#!/usr/bin/env python3
"""SSD Test Log Analyzer — 命令行入口"""
import sys
import os

# 确保能找到 src 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from parser import parse_log
from analyzer import analyze
from reporter import generate_report


def main():
    if len(sys.argv) < 2:
        print("用法: python main.py <日志文件> [-o 输出路径]")
        print("示例: python main.py samples/smi_test.log -o output/report.html")
        sys.exit(1)

    log_path = sys.argv[1]
    output_dir = "output"
    output_path = "output/report.html"

    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]
            output_dir = os.path.dirname(output_path)

    if not os.path.exists(log_path):
        print(f"[ERROR] 文件不存在: {log_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"[1/3] 解析日志: {log_path}")
    sessions = parse_log(log_path)
    print(f"      -> {len(sessions)} 个测试会话")

    print(f"[2/3] 分析数据...")
    result = analyze(sessions)
    s = result["summary"]
    print(f"      -> 通过率: {s['pass_rate']}, 异常: {s['anomaly_count']} 项")

    print(f"[3/3] 生成报告: {output_path}")
    generate_report(result, output_path)

    print(f"\n[DONE] 报告已保存，用浏览器打开即可查看")


if __name__ == "__main__":
    main()
