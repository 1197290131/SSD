# SSD Test Log Analyzer

固态硬盘产线测试日志分析工具 —— 模拟慧荣（Silicon Motion）SMI 主控方案的 FT/QA 测试场景，从日志中自动提取测试指标、检测异常、生成可视化报告。

V2 新增 **配置文件驱动** 架构，日志解析规则和异常阈值通过 YAML 配置外部化，不修改代码即可适配不同主控方案。

## 项目背景

在 SSD 产线测试（FT / QA）环节，每片盘会经过多个测试工位，产生大量结构化日志。人工翻查日志效率低、易遗漏异常。本工具的目标是：

- **自动化**读取产测日志，提取关键性能指标
- **规则引擎**检测良率异常，定位问题会话
- **可视化报告**汇总测试结果，方便产线巡检
- **配置驱动**日志模板和阈值外置，适配不同主控方案

## 功能概览

```
SSD Test Log Analyzer
├── ▸ 配置        从 YAML 加载解析规则和异常阈值
├── ▸ 解析        按配置模板提取 5 类测试项的结构化数据
├── ▸ 分析        聚合统计 + 可配置规则引擎异常检测
└── ▸ 报告        生成深色主题 HTML 报告（Chart.js 图表）
```

### 支持解析的测试项

| 测试类型 | 提取字段 | 标签 |
|---------|---------|------|
| Sequential Read / Write (128KB) | Speed (MB/s), Temperature (°C) | `throughput` |
| Random Read / Write IOPS (4KB QD32) | IOPS, AvgLatency (us) | `iops` |
| Temperature Stress (60s burn) | MaxTemp, AvgTemp (°C) | `temperature` |
| SMART Attributes | ReallocatedSectors, PendingSectors, WearLevel, RawReadErrors | `smart` |
| Power Consumption | ActivePower (W), IdlePower (W) | `power` |

### 异常检测规则

| 规则 | 阈值 | 触发场景 |
|------|------|----------|
| `seq_read_slow` | < 3000 MB/s | 顺序读性能不足 |
| `seq_write_slow` | < 2600 MB/s | 顺序写性能不足 |
| `low_random_read_iops` | < 350,000 | 随机读 IOPS 偏低 |
| `low_random_write_iops` | < 300,000 | 随机写 IOPS 偏低 |
| `high_latency` | > 200 us | 延迟过高 |
| `overheating` | > 80°C | 温度超标 |
| `excessive_reallocated` | > 20 | 坏块过多 |
| `pending_sectors_warn` | > 5 | 待重映射扇区过多 |

> 以上阈值为 SMI 主控方案的默认值，可在 `config_smi.yaml` 中按需修改。

## 快速开始

```bash
# 安装依赖
pip install pyyaml

# 1. 生成样本日志（模拟 5 个测试会话）
python generate_sample_log.py

# 2. 运行分析并生成报告
python main.py samples/smi_test.log

# 3. 打开报告
# output/report.html → 用浏览器打开
```

命令行选项：

```bash
python main.py <日志文件> [-c 配置文件] [-o 输出路径]

# 使用默认配置
python main.py samples/smi_test.log

# 指定配置文件
python main.py samples/smi_test.log -c config_smi.yaml

# 指定输出路径
python main.py samples/smi_test.log -o output/my_report.html
```

## 输出示例

生成的 HTML 报告包含：

- **概览卡片**：会话数、记录数、通过率、异常数
- **图表面板**：顺序读写吞吐量、随机 IOPS、温度峰值、平均延迟
- **异常列表**：触发的异常规则及对应会话（显示规则中文名）
- **会话表格**：每个测试会话的汇总状态

## 架构

```
config_smi.yaml         配置    日志正则模板 + 异常阈值
    │
main.py  ── 命令行入口
    │
    ├── src/config_loader.py   配置加载   读取 YAML，校验结构，内置默认值兜底
    ├── src/parser.py          日志解析   按配置模板提取 → 结构化记录
    ├── src/analyzer.py        数据分析   分组统计 + 配置化规则引擎
    └── src/reporter.py        报告生成   HTML + Chart.js

generate_sample_log.py  样本生成  模拟 SMI 产测日志格式
```

## 配置文件结构

```yaml
device:
  vendor: "Silicon Motion"           # 厂商名称（显示在报告标题）
  controller: "SMI"                  # 主控方案

parsing:
  session_header: "..."              # 提取会话信息的正则
  test_item: "..."                   # 测试项行正则
  summary: "..."                     # 会话汇总行正则
  result_types:                      # 各类测试结果的正则与字段映射
    throughput:
      regex: "..."                   # 匹配正则（capture group 按 fields 顺序）
      fields: [speed_mbps, ...]      # 字段名列表
      field_types: [float, ...]      # 类型列表（int/float/str）

anomaly_rules:                       # 异常规则列表
  - name: overheating
    label: "温度超标"                  # 报告中的中文名
    enabled: true                    # 是否启用
    record_type: temperature         # 作用于哪类测试
    conditions:                      # AND 条件列表
      - { field: max_temp_c, operator: ">", value: 80 }
```

## 扩展配置示例

将本工具适配其他主控（如联芸 Maxio）只需新建一个配置文件：

```yaml
device:
  vendor: "Maxio"
  controller: "联芸"
parsing:
  result_types:
    throughput:
      regex: "ReadSpeed=([\\d.]+).*?WriteSpeed=([\\d.]+).*?Temp=([\\d.]+)"
      fields: [read_speed, write_speed, temp]
      field_types: [float, float, float]
anomaly_rules:
  - name: read_slow
    label: "读速不足"
    ...
```

## 技术栈

- Python 3.10+
- PyYAML 6+（配置文件解析）
- Chart.js 4（CDN 方式引入，报告页面需要网络）

## 迭代路线

| 版本 | 特性 |
|------|------|
| v1 | 基础功能：日志解析、统计、报告（硬编码规则） |
| **v2** | **配置文件驱动：正则模板和异常阈值外置到 YAML** |
| v3 (规划) | 多主控配置文件库 + 批量并行解析 |

## 许可证

GUST
