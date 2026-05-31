# SSD Test Log Analyzer

固态硬盘产线测试日志分析工具 —— 模拟慧荣（Silicon Motion）SMI 主控方案的 FT/QA 测试场景，从日志中自动提取测试指标、检测异常、生成可视化报告。

## 项目背景

在 SSD 产线测试（FT / QA）环节，每片盘会经过多个测试工位，产生大量结构化日志。人工翻查日志效率低、易遗漏异常。本工具的目标是：

- **自动化**读取产测日志，提取关键性能指标
- **规则引擎**检测良率异常，定位问题会话
- **可视化报告**汇总测试结果，方便产线巡检

## 功能概览

```
SSD Test Log Analyzer
├── ▸ 解析        提取 5 类测试项的结构化数据
├── ▸ 分析        聚合统计 + 业务规则异常检测
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

## 快速开始

```bash
# 1. 生成样本日志（模拟 5 个测试会话）
python generate_sample_log.py

# 2. 运行分析并生成报告
python main.py samples/smi_test.log

# 3. 打开报告
# output/report.html → 用浏览器打开
```

命令行选项：

```bash
python main.py <日志文件> [-o 输出路径]
python main.py samples/smi_test.log -o output/my_report.html
```

## 输出示例

生成的 HTML 报告包含：

- **概览卡片**：会话数、记录数、通过率、异常数
- **图表面板**：顺序读写吞吐量、随机 IOPS、温度峰值、平均延迟
- **异常列表**：触发的异常规则及对应会话
- **会话表格**：每个测试会话的汇总状态

## 架构

```
main.py  ── 命令行入口
  │
  ├── src/parser.py     日志解析   正则提取 → 结构化记录
  ├── src/analyzer.py   数据分析   分组统计 + 规则引擎
  └── src/reporter.py   报告生成   HTML + Chart.js

generate_sample_log.py  样本生成  模拟 SMI 产测日志格式
```

## 技术栈

- Python 3.10+ (标准库，无第三方依赖)
- Chart.js 4 (CDN 方式引入，报告页面需要网络)

## 扩展方向

- **配置文件驱动**：将日志格式模板和异常阈值外置到 YAML / TOML 配置，不修改代码即可适配不同主控方案
- **多主控支持**：增加联芸、瑞昱、英韧等主控厂商的日志格式适配器
- **批量处理**：并行解析多盘同测日志，汇总批次良率
- **数据库存储**：持久化测试记录，支持历史趋势分析

## 许可证

MIT
