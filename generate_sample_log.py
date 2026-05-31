"""
生成模拟 SSD 测试日志 (smi_test.log)
模拟 Silicon Motion 主控方案的固态硬盘产线测试日志格式
"""
import os
import random
from datetime import datetime, timedelta

random.seed(42)  # 固定种子，每次生成的日志一致

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "samples")


def log_line(ts, level="INFO", message=""):
    return f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}\n"


def generate(num_sessions=5):
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    now = datetime(2026, 5, 8, 9, 0, 0)
    lines = []

    for session in range(1, num_sessions + 1):
        model = random.choice(["SM2263XT", "SM2262EN", "SM2259X2", "SM2320"])
        fw = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
        serial = f"SM{20260000 + session:05d}"

        # === 会话头 ===
        lines.append(log_line(now, "INFO", "=" * 60))
        lines.append(log_line(now, "INFO", f"SSD Test Session #{session} Started"))
        lines.append(log_line(now, "INFO", f"Model: {model}"))
        lines.append(log_line(now, "INFO", f"FW Version: {fw}"))
        lines.append(log_line(now, "INFO", f"Serial Number: {serial}"))
        lines.append(log_line(now, "INFO", f"Test Program: SMI Production Test v{random.randint(2,4)}.{random.randint(0,9)}"))
        now += timedelta(seconds=1)

        # --- 1. Sequential Read (128KB) ---
        lines.append(log_line(now, "TEST", "Test Item: Sequential Read (128KB)"))
        now += timedelta(seconds=2)
        speed = round(random.uniform(3200, 3600), 2)
        temp = round(random.uniform(38, 48), 1)
        lines.append(log_line(now, "RESULT", f"Speed={speed} MB/s  Temperature={temp} C  Status=PASS"))
        now += timedelta(seconds=1)

        # --- 2. Sequential Write (128KB) ---
        lines.append(log_line(now, "TEST", "Test Item: Sequential Write (128KB)"))
        now += timedelta(seconds=3)
        speed = round(random.uniform(2800, 3200), 2)
        temp = round(random.uniform(42, 55), 1)
        lines.append(log_line(now, "RESULT", f"Speed={speed} MB/s  Temperature={temp} C  Status=PASS"))
        now += timedelta(seconds=1)

        # --- 3. Random Read IOPS (4KB) ---
        lines.append(log_line(now, "TEST", "Test Item: Random Read IOPS (4KB, QD32)"))
        now += timedelta(seconds=4)
        iops = random.randint(450000, 580000)
        latency = round(random.uniform(55, 95), 2)
        lines.append(log_line(now, "RESULT", f"IOPS={iops}  AvgLatency={latency} us  Status=PASS"))
        now += timedelta(seconds=1)

        # --- 4. Random Write IOPS (4KB) ---
        lines.append(log_line(now, "TEST", "Test Item: Random Write IOPS (4KB, QD32)"))
        now += timedelta(seconds=5)
        iops = random.randint(380000, 500000)
        latency = round(random.uniform(80, 140), 2)
        status = "PASS"
        # 第3个会话模拟一次写入性能轻微衰减
        if session in (3, 4) and random.random() < 0.4:
            iops = random.randint(200000, 300000)
            latency = round(random.uniform(200, 350), 2)
            status = "WARN"
        lines.append(log_line(now, "RESULT", f"IOPS={iops}  AvgLatency={latency} us  Status={status}"))
        now += timedelta(seconds=1)

        # --- 5. Temperature Stress Test ---
        lines.append(log_line(now, "TEST", "Test Item: Temperature Stress (60s burn)"))
        now += timedelta(seconds=3)
        max_temp = round(random.uniform(65, 78), 1)
        avg_temp = round(random.uniform(58, 70), 1)
        status = "PASS"
        # 第5个会话模拟过热
        if session == 5:
            max_temp = round(random.uniform(85, 95), 1)
            avg_temp = round(random.uniform(78, 88), 1)
            status = "FAIL"
        lines.append(log_line(now, "RESULT", f"MaxTemp={max_temp} C  AvgTemp={avg_temp} C  Status={status}"))
        now += timedelta(seconds=1)

        # --- 6. SMART Info ---
        lines.append(log_line(now, "TEST", "Test Item: SMART Attributes Check"))
        now += timedelta(seconds=1)
        reallocated = random.randint(0, 5)
        pending_sectors = random.randint(0, 3)
        wear_level = random.randint(0, 5)
        raw_read_err = random.randint(0, 10)

        if session == 2:  # 模拟坏块较多的盘
            reallocated = 28
            pending_sectors = 12
            raw_read_err = 57

        lines.append(log_line(now, "RESULT", f"ReallocatedSectors={reallocated}  PendingSectors={pending_sectors}  WearLevel={wear_level}%  RawReadErrors={raw_read_err}  Status={'PASS' if reallocated < 20 else 'WARN'}"))
        now += timedelta(seconds=1)

        # --- 7. Power Consumption ---
        lines.append(log_line(now, "TEST", "Test Item: Power Consumption"))
        now += timedelta(seconds=2)
        p_active = round(random.uniform(3.5, 6.0), 2)
        p_idle = round(random.uniform(0.3, 0.8), 2)
        lines.append(log_line(now, "RESULT", f"ActivePower={p_active} W  IdlePower={p_idle} W  Status=PASS"))
        now += timedelta(seconds=1)

        # === 会话汇总 ===
        elapsed = random.randint(85, 135)
        total_status = random.choices(["PASS", "PASS", "PASS", "PASS", "PASS_WARN", "FAIL"],
                                      weights=[50, 20, 15, 10, 4, 1])[0]
        lines.append(log_line(now, "INFO", f"--- Session #{session} Summary ---"))
        lines.append(log_line(now, "INFO", f"Elapsed: {elapsed}s  Overall: {total_status}"))
        lines.append(log_line(now, "INFO", "=" * 60))
        lines.append("\n")
        now += timedelta(seconds=5)

    filepath = os.path.join(SAMPLE_DIR, "smi_test.log")
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"[OK] 已生成模拟日志: {filepath}")
    print(f"     共 {num_sessions} 个测试会话, {len(lines)} 行日志")


if __name__ == "__main__":
    generate()
