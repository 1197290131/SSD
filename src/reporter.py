# SSD Test Log Analyzer — HTML 报告生成器
from collections import defaultdict
from datetime import datetime


def generate_report(result: dict, output_path: str):
    html = _build_html(result)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 报告已生成: {output_path}")


def _build_html(r: dict) -> str:
    s = r["summary"]
    anomalies = r["anomalies"]
    sessions = r["sessions"]
    records = [rr for s in r.get("raw_sessions", sessions) for rr in s["records"]]

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SSD 测试日志分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px 20px; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .subtitle {{ color: #94a3b8; margin-bottom: 32px; }}
  h2 {{ font-size: 20px; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; }}

  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 20px; text-align: center; }}
  .card .num {{ font-size: 32px; font-weight: 700; color: #38bdf8; }}
  .card .num.pass {{ color: #22c55e; }}
  .card .num.warn {{ color: #f59e0b; }}
  .card .num.fail {{ color: #ef4444; }}
  .card .label {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}

  .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
  .chart-box {{ background: #1e293b; border-radius: 12px; padding: 20px; }}
  .chart-box h3 {{ font-size: 14px; color: #94a3b8; margin-bottom: 12px; }}
  .chart-box canvas {{ max-height: 280px; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ text-align: left; padding: 10px 12px; background: #1e293b; color: #94a3b8; font-weight: 600; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; font-family: monospace; }}
  tr:hover td {{ background: #1e293b88; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; }}
  .badge.PASS {{ background: #052e16; color: #22c55e; }}
  .badge.WARN {{ background: #451a03; color: #f59e0b; }}
  .badge.FAIL {{ background: #450a0a; color: #ef4444; }}
  .badge.PASS_WARN {{ background: #451a03; color: #f59e0b; }}

  .anomaly-list {{ list-style: none; }}
  .anomaly-list li {{ padding: 12px 16px; background: #1e293b; border-left: 4px solid #ef4444; border-radius: 8px; margin-bottom: 8px; }}

  @media (max-width: 768px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">

<h1>SSD 测试日志分析报告</h1>
<p class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  {s['total_sessions']} 个会话 / {s['total_records']} 条记录</p>

<div class="cards">
  <div class="card"><div class="num">{s['total_sessions']}</div><div class="label">测试会话</div></div>
  <div class="card"><div class="num">{s['total_records']}</div><div class="label">测试记录</div></div>
  <div class="card"><div class="num pass">{s['pass_rate']}</div><div class="label">通过率</div></div>
  <div class="card"><div class="num {'warn' if s['anomaly_count'] > 0 else 'pass'}">{s['anomaly_count']}</div><div class="label">异常项</div></div>
  <div class="card"><div class="num" style="font-size:20px">{', '.join(s['models'])}</div><div class="label">固件型号</div></div>
</div>

<!-- 图表 -->
<div class="chart-grid">
  <div class="chart-box"><h3>顺序读写吞吐量 (MB/s)</h3><canvas id="chart-throughput"></canvas></div>
  <div class="chart-box"><h3>随机读写 IOPS</h3><canvas id="chart-iops"></canvas></div>
  <div class="chart-box"><h3>温度压力测试 (°C)</h3><canvas id="chart-temp"></canvas></div>
  <div class="chart-box"><h3>平均延迟 (us)</h3><canvas id="chart-latency"></canvas></div>
</div>

<!-- 异常 -->
<h2>异常检测 ({s['anomaly_count']})</h2>
{_anomaly_html(anomalies) if anomalies else '<p style="color:#22c55e">✓ 未检测到异常</p>'}

<!-- 统计 -->
<h2>统计明细</h2>
{_stats_html(r['by_type'])}

<!-- 会话列表 -->
<h2>会话概览</h2>
<table><thead><tr><th>#</th><th>型号</th><th>序列号</th><th>耗时</th><th>状态</th></tr></thead>
<tbody>
{''.join(f'<tr><td>{s["session"]}</td><td>{s["model"]}</td><td>{s["serial"]}</td><td>{s["elapsed"]}s</td><td><span class="badge {s["overall"]}">{s["overall"]}</span></td></tr>' for s in sessions)}
</tbody></table>

</div>

<script>
{_chart_js(records)}
</script>
</body>
</html>"""


def _mean(nums):
    return sum(nums) / len(nums) if nums else 0


def _chart_js(records: list) -> str:
    """从原始记录计算每个测试项的平均值用于图表"""
    def avg(items, key):
        vals = [r[key] for r in items]
        return round(_mean(vals), 1) if vals else 0

    sr = [r for r in records if "Sequential Read" in r["test_item"]]
    sw = [r for r in records if "Sequential Write" in r["test_item"]]
    rr = [r for r in records if "Random Read IOPS" in r["test_item"]]
    rw = [r for r in records if "Random Write IOPS" in r["test_item"]]
    tp = [r for r in records if "Temperature" in r["test_item"]]

    sr_spd, sw_spd = avg(sr, "speed_mbps"), avg(sw, "speed_mbps")
    rr_iops, rw_iops = avg(rr, "iops"), avg(rw, "iops")
    tp_max = avg(tp, "max_temp_c")
    rr_lat, rw_lat = avg(rr, "avg_latency_us"), avg(rw, "avg_latency_us")

    return f"""
new Chart(document.getElementById('chart-throughput'), {{
  type: 'bar',
  data: {{
    labels: ['顺序读', '顺序写'],
    datasets: [{{ data: [{sr_spd}, {sw_spd}], backgroundColor: ['#38bdf8', '#22c55e'], borderRadius: 6 }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: false }} }} }}
}});

new Chart(document.getElementById('chart-iops'), {{
  type: 'bar',
  data: {{
    labels: ['随机读', '随机写'],
    datasets: [{{ data: [{rr_iops}, {rw_iops}], backgroundColor: ['#a78bfa', '#f472b6'], borderRadius: 6 }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: false }} }} }}
}});

new Chart(document.getElementById('chart-temp'), {{
  type: 'bar',
  data: {{
    labels: ['最高温(平均)'],
    datasets: [{{ data: [{tp_max}], backgroundColor: ['#f59e0b'], borderRadius: 6 }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
}});

new Chart(document.getElementById('chart-latency'), {{
  type: 'bar',
  data: {{
    labels: ['随机读', '随机写'],
    datasets: [{{ data: [{rr_lat}, {rw_lat}], backgroundColor: ['#818cf8', '#e879f9'], borderRadius: 6 }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: false }} }} }}
}});
"""


def _anomaly_html(anomalies):
    items = "".join(
        f'<li>Session #{a["session"]} — <strong>{a["test_item"]}</strong> '
        f'(<span class="badge {a["status"]}">{a["status"]}</span>) — {a["rule"]}</li>'
        for a in anomalies
    )
    return f'<ul class="anomaly-list">{items}</ul>'


def _stats_html(by_type):
    parts = []
    for t, s in by_type.items():
        rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in s.items())
        parts.append(f"""
<h3 style="margin-top:16px;font-size:15px;">[{t}] PASS: {s.get('pass_count', 0)}/{s.get('count', 0)}</h3>
<table><tbody>{rows}</tbody></table>""")
    return "".join(parts)


if __name__ == "__main__":
    from parser import parse_log
    from analyzer import analyze
    import os

    os.makedirs("output", exist_ok=True)
    data = parse_log("samples/smi_test.log")
    result = analyze(data)
    generate_report(result, "output/report.html")
