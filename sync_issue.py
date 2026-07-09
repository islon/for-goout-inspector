#!/usr/bin/env python3
"""同步巡检报告为 GitHub Issue 到 goout 仓库"""
import json, os, urllib.request
from datetime import datetime

TOKEN = os.environ["GOOUT_PAT"]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json"
}
GOOUT_REPO = "islon/goout"
PAGE_URL = "https://islon.github.io/goout/schedule.html"
DATA_URL = "https://raw.githubusercontent.com/islon/goout/main/output/exhibitions.json"
INSPECTOR_REPO = "islon/for-goout-inspector"
TODAY = datetime.now().strftime("%Y-%m-%d")

def api(method, path, data=None):
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.read().decode()[:300]}")
        return None

with open("reports/latest.md", "r") as f:
    report = f.read()

lines = report.split("\n")
stats = {}
for line in lines:
    parts = line.split("|")
    if len(parts) < 3:
        continue
    val = parts[2].strip()
    if "全量活动数据" in line: stats["total"] = val
    if "新增活动" in line: stats["new"] = val
    if "问题总数" in line: stats["issues"] = val
    if "严重错误" in line: stats["critical"] = val
    if "一般问题" in line: stats["warnings"] = val
    if "优化建议" in line: stats["suggestions"] = val

summary = f"""## 巡检摘要 ({TODAY})

| 指标 | 数值 |
|------|------|
| 活动总数 | {stats.get('total', '?')} |
| 新增活动 | {stats.get('new', '?')} |
| 问题总数 | {stats.get('issues', '?')} |
| 严重错误 | {stats.get('critical', '?')} |
| 一般问题 | {stats.get('warnings', '?')} |
| 优化建议 | {stats.get('suggestions', '?')} |

### 站点状态
- 页面: [{PAGE_URL}]({PAGE_URL})
- 数据源: [{DATA_URL}]({DATA_URL})
- 完整报告: [{INSPECTOR_REPO}/blob/main/reports/latest.md](https://github.com/{INSPECTOR_REPO}/blob/main/reports/latest.md)

---

"""

in_warnings = False
warn_lines = []
for line in lines:
    if "## 三、一般问题" in line:
        in_warnings = True
        continue
    if in_warnings:
        if line.startswith("## 四、") or line.startswith("## 五、"):
            break
        warn_lines.append(line)

if warn_lines:
    summary += "### 一般问题\n\n"
    summary += "\n".join(warn_lines[:60])
    if len(warn_lines) > 60:
        summary += "\n\n> ... 更多问题详见完整报告。\n"

summary += f"""
---
> 本 Issue 由 [数据质量巡检智能体](https://github.com/{INSPECTOR_REPO}) 每日自动生成
> 报告时间: {TODAY}
"""

existing = api("GET", f"/repos/{GOOUT_REPO}/issues?labels=data-quality&state=open&per_page=10")
today_issue = None
if existing:
    for iss in existing:
        if f"巡检报告 ({TODAY}" in iss.get("title", ""):
            today_issue = iss
            break

if today_issue:
    print(f"Updating existing issue #{today_issue['number']}")
    api("PATCH", f"/repos/{GOOUT_REPO}/issues/{today_issue['number']}", {"body": summary})
else:
    result = api("POST", f"/repos/{GOOUT_REPO}/issues", {
        "title": f"[巡检报告] {TODAY} 深圳亲子活动日历数据质量巡检",
        "body": summary,
        "labels": ["data-quality", "automated"]
    })
    if result:
        print(f"Issue created: {result['html_url']}")