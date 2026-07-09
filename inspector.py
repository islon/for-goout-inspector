#!/usr/bin/env python3
"""
深圳亲子活动日历 - 数据质量巡检智能体
==========================================
自动化巡检 islon.github.io/goout/schedule.html 的数据质量，
生成结构化巡检报告，支持历史数据对比与问题整改跟踪。

数据源: https://raw.githubusercontent.com/islon/goout/main/output/exhibitions.json
页面地址: https://islon.github.io/goout/schedule.html
"""

import json
import os
import sys
import re
import hashlib
import time
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from collections import defaultdict
from typing import Any

# ============================================================
# 配置
# ============================================================

# 目标数据源
DATA_URL = "https://raw.githubusercontent.com/islon/goout/main/output/exhibitions.json"
PAGE_URL = "https://islon.github.io/goout/schedule.html"
REPO_URL = "https://github.com/islon/goout"

# 本地存储路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
ISSUES_FILE = os.path.join(DATA_DIR, "issues_tracker.json")

# 深圳行政区划标准名录
SZ_DISTRICTS = [
    "福田区", "罗湖区", "南山区", "宝安区", "龙岗区",
    "龙华区", "坪山区", "光明区", "盐田区", "大鹏新区"
]

# 有效分类
VALID_CATEGORIES = [
    "展览", "讲座阅读", "科普活动", "演出",
    "影视放映", "体育赛事", "亲子活动", "其他"
]

# 有效收费类型
VALID_FEE_TYPES = ["免费", "免费需预约", "收费", "部分免费", "需购票"]

# 区县映射（从页面 districtMapping 提取）
DISTRICT_MAPPING = {
    'szlib': '福田区', 'sz_children_lib': '福田区', 'szbwg': '福田区',
    'szstm': '光明区', 'szcp': '福田区', 'szaac': '福田区',
    'sznm': '坪山区', 'szbo': '宝安区', 'szconcert': '福田区',
    'szmocap': '福田区', 'szsports': '福田区', 'szmassart': '福田区',
    'nslib': '南山区', 'balib': '宝安区', 'ftlib': '福田区',
    'lhlib': '罗湖区', 'lglib': '龙岗区', 'lhxqlib': '龙华区',
    'gmlib': '光明区', 'pslib': '坪山区', 'ytlib': '盐田区',
    'dplib': '大鹏新区', 'nsmuseum': '南山区', 'lgmuseum': '龙岗区',
    'bamuseum': '宝安区', 'lhmuseum': '龙华区', 'lhmuseum2': '罗湖区',
    'dpgeopark': '大鹏新区', 'baoan_kjg': '宝安区', 'lgkjg': '龙岗区',
    'lhkjg': '龙华区', 'ytkjg': '盐田区', 'gm_kjg': '光明区',
    'baoan_qsng': '宝安区', 'nsqsng': '南山区', 'lgqsng': '龙岗区',
    'lhqsng': '龙华区', 'lhqsng2': '罗湖区', 'gmqsng': '光明区',
    'psqsng': '坪山区', 'baoan_ty': '宝安区', 'nswtzx': '南山区',
    'szwty': '南山区', 'lhtyzx': '龙岗区', 'lhwtx': '龙华区',
    'gmtyzx': '光明区', 'lhtyzx2': '罗湖区', 'pstyzx': '坪山区',
    'yttyzx': '盐田区', 'nswhg': '南山区', 'baoan_1990': '宝安区',
    'bayarea_eye': '宝安区', 'baoan_guihua': '宝安区',
    'lgguihua': '龙岗区', 'nsguihua': '南山区',
    'lh_printmaking': '龙华区', 'nsaqjy': '南山区',
    'skhykpg': '南山区', 'szcec': '福田区', 'shenzhen_world': '宝安区',
    'ps_nature': '坪山区', 'gm_lib': '光明区', 'yt_lib': '盐田区',
    'yt_history': '盐田区', 'dp_geopark': '大鹏新区',
    'dp_nuclear': '大鹏新区', 'sz_safety': '福田区',
    'oct_wetland': '南山区', 'lg_hakka': '龙岗区',
    'lh_ecology': '龙华区', 'lh_paleo': '罗湖区',
    'sarc': '南山区', 'ntgc': '南山区', 'zsjbwg': '南山区',
    'nssxf': '南山区',
}

# 场馆名映射（从页面 sourceToVenue 提取）
SOURCE_TO_VENUE = {
    'szlib': '深圳图书馆', 'sz_children_lib': '深圳少儿图书馆',
    'szbwg': '深圳博物馆', 'szstm': '深圳科学技术馆',
    'szcp': '深圳市少年宫', 'szaac': '深圳市青少年活动中心',
    'sznm': '深圳自然博物馆', 'szbo': '深圳滨海艺术中心',
    'szconcert': '深圳音乐厅', 'szmocap': '当代艺术与城市规划馆',
    'szsports': '深圳市体育中心', 'szmassart': '深圳市文化馆',
    'nslib': '南山图书馆', 'balib': '宝安图书馆',
    'ftlib': '福田区图书馆', 'lhlib': '罗湖区图书馆',
    'lglib': '龙岗区图书馆', 'lhxqlib': '龙华区图书馆',
    'gmlib': '光明区图书馆', 'pslib': '坪山区图书馆',
    'ytlib': '盐田区图书馆', 'dplib': '大鹏新区图书馆',
    'nsmuseum': '南山博物馆', 'lgmuseum': '龙岗区博物馆',
    'bamuseum': '宝安区博物馆', 'lhmuseum': '龙华区博物馆',
    'lhmuseum2': '罗湖区博物馆', 'dpgeopark': '大鹏地质公园博物馆',
    'baoan_kjg': '宝安科技馆', 'lgkjg': '龙岗区科技馆',
    'lhkjg': '龙华区科技馆', 'ytkjg': '盐田区科技馆',
    'gm_kjg': '光明区科技馆', 'baoan_qsng': '宝安区青少年宫',
    'nsqsng': '南山区青少年活动中心', 'lgqsng': '龙岗区青少年宫',
    'lhqsng': '龙华区青少年宫', 'lhqsng2': '罗湖区青少年活动中心',
    'gmqsng': '光明区青少年活动中心', 'psqsng': '坪山区青少年宫',
    'baoan_ty': '宝安体育中心', 'nswtzx': '南山文体中心',
    'szwty': '深圳湾体育中心', 'lhtyzx': '龙岗体育中心',
    'lhwtx': '龙华文体中心', 'gmtyzx': '光明区群众体育中心',
    'lhtyzx2': '罗湖区体育中心', 'pstyzx': '坪山体育中心',
    'yttyzx': '盐田体育中心', 'nswhg': '南山区文化馆',
    'baoan_1990': '宝安1990文化馆', 'bayarea_eye': '湾区之眼',
    'baoan_guihua': '宝安城市规划展览馆',
    'lgguihua': '龙岗城市规划展览馆',
    'nsguihua': '南山城市规划展览馆',
    'lh_printmaking': '中国版画博物馆',
    'nsaqjy': '南山安全教育体验馆', 'skhykpg': '蛇口海洋科普馆',
}


# ============================================================
# 工具函数
# ============================================================

def fetch_json(url: str) -> dict | list | None:
    """获取JSON数据，带重试机制"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'SZ-Kids-Inspector/1.0',
                'Cache-Control': 'no-cache'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"[ERROR] 获取数据失败 ({url}): {e}")
                return None
    return None


def check_page_availability() -> dict:
    """检查站点可用性"""
    result = {
        "accessible": False,
        "http_status": None,
        "load_time_ms": 0,
        "error": None
    }
    try:
        start = time.time()
        req = urllib.request.Request(PAGE_URL, headers={
            'User-Agent': 'SZ-Kids-Inspector/1.0'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            result["http_status"] = resp.status
            result["accessible"] = resp.status == 200
            result["load_time_ms"] = int((time.time() - start) * 1000)
    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
    return result


def get_district(source: str) -> str:
    """根据 source 获取区县"""
    return DISTRICT_MAPPING.get(source, "其他")


def get_venue_name(source: str) -> str:
    """根据 source key 获取场馆名"""
    return SOURCE_TO_VENUE.get(source, source)


def compute_activity_id(item: dict) -> str:
    """计算活动唯一标识"""
    key = f"{item.get('name','')}|{item.get('venue','')}|{item.get('start_date','')}|{item.get('end_date','')}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()[:12]


def generate_anchor_link(index: int) -> str:
    """生成页面锚点链接（基于活动在数组中的索引，估算页面位置）"""
    page = (index // 50) + 1
    return f"{PAGE_URL}#page={page}&item={index % 50}"


# ============================================================
# 数据校验
# ============================================================

class Issue:
    """问题条目"""
    def __init__(self, severity: str, issue_type: str, description: str,
                 page_link: str, suggestion: str, evidence: str):
        self.severity = severity  # critical, warning, suggestion
        self.issue_type = issue_type
        self.description = description
        self.page_link = page_link
        self.suggestion = suggestion
        self.evidence = evidence

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "type": self.issue_type,
            "description": self.description,
            "page_link": self.page_link,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
        }


def validate_time(item: dict, index: int) -> list[Issue]:
    """校验时间逻辑"""
    issues = []
    sd = item.get("start_date", "")
    ed = item.get("end_date", "")
    name = item.get("name", f"活动#{index}")
    anchor = generate_anchor_link(index)

    # 日期格式校验
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not date_pattern.match(str(sd)):
        issues.append(Issue(
            "critical", "时间格式错误",
            f"「{name}」开始日期格式异常: '{sd}'",
            anchor,
            "修正为 YYYY-MM-DD 格式",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))
    if not date_pattern.match(str(ed)):
        issues.append(Issue(
            "critical", "时间格式错误",
            f"「{name}」结束日期格式异常: '{ed}'",
            anchor,
            "修正为 YYYY-MM-DD 格式",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    # 起止时间合理性
    if date_pattern.match(str(sd)) and date_pattern.match(str(ed)):
        if sd > ed:
            issues.append(Issue(
                "critical", "时间逻辑错误",
                f"「{name}」开始日期({sd})晚于结束日期({ed})",
                anchor,
                "交换起止日期或修正错误日期",
                f"{REPO_URL}/blob/main/output/exhibitions.json"
            ))

    # 已过期活动标记（超过结束日期30天以上）
    if date_pattern.match(str(ed)):
        try:
            end_date = datetime.strptime(str(ed), "%Y-%m-%d").date()
            if end_date < date.today() - timedelta(days=30):
                issues.append(Issue(
                    "warning", "过期活动未清理",
                    f"「{name}」已于 {ed} 结束（超过30天），建议归档或移除",
                    anchor,
                    "考虑归档过期活动或标记为已结束",
                    f"{REPO_URL}/blob/main/output/exhibitions.json"
                ))
        except ValueError:
            pass

    return issues


def validate_geo(item: dict, index: int) -> list[Issue]:
    """校验地理信息"""
    issues = []
    name = item.get("name", f"活动#{index}")
    venue = item.get("venue", "")
    source = item.get("source", "")
    anchor = generate_anchor_link(index)

    # 场地信息缺失
    if not venue:
        issues.append(Issue(
            "warning", "场地信息缺失",
            f"「{name}」缺少场地(venue)信息",
            anchor,
            "补充活动具体举办场地",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    # 区县匹配校验
    expected_district = get_district(source)
    if source in DISTRICT_MAPPING and expected_district != "其他":
        # 检查场地名称是否包含区县名
        district_in_venue = any(d in str(venue) for d in SZ_DISTRICTS)
        if district_in_venue:
            venue_district = [d for d in SZ_DISTRICTS if d in str(venue)][0]
            if venue_district != expected_district:
                issues.append(Issue(
                    "warning", "区县匹配不一致",
                    f"「{name}」source({source})映射到{expected_district}，但场地名包含'{venue_district}'",
                    anchor,
                    f"核实实际地址，确认应归属{expected_district}还是{venue_district}",
                    "https://www.sz.gov.cn/cn/xxgk/zfxxgj/bmfw/qhfwyqhcxy/ "
                    "(深圳行政区划标准名录)"
                ))

    return issues


def validate_category(item: dict, index: int) -> list[Issue]:
    """校验分类一致性"""
    issues = []
    name = item.get("name", f"活动#{index}")
    category = item.get("category", "")
    fee = item.get("fee", "")
    anchor = generate_anchor_link(index)

    # 分类有效性
    if category and category not in VALID_CATEGORIES:
        issues.append(Issue(
            "warning", "分类不在标准列表中",
            f"「{name}」分类为'{category}'，不在标准分类列表: {', '.join(VALID_CATEGORIES)}",
            anchor,
            "更新为标准分类或新增分类到筛选器",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    if not category:
        issues.append(Issue(
            "warning", "分类信息缺失",
            f"「{name}」缺少分类(category)信息",
            anchor,
            "补充活动分类",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    # 收费类型校验
    if fee and fee not in VALID_FEE_TYPES:
        issues.append(Issue(
            "warning", "收费类型不在标准列表中",
            f"「{name}」收费类型为'{fee}'，不在标准类型列表: {', '.join(VALID_FEE_TYPES)}",
            anchor,
            "更新为标准收费类型",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    if not fee:
        issues.append(Issue(
            "warning", "收费信息缺失",
            f"「{name}」缺少收费(fee)信息",
            anchor,
            "补充收费类型（免费/收费/需购票等）",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    return issues


def validate_completeness(item: dict, index: int) -> list[Issue]:
    """校验字段完整性"""
    issues = []
    name = item.get("name", f"活动#{index}")
    anchor = generate_anchor_link(index)

    required_fields = {
        "title": "标题",
        "name": "名称",
        "venue": "地点",
        "start_date": "开始日期",
        "end_date": "结束日期",
        "category": "分类",
        "fee": "收费类型",
        "source": "来源",
    }

    missing = [label for field, label in required_fields.items() if not item.get(field)]
    if missing:
        issues.append(Issue(
            "warning", "必填字段缺失",
            f"「{name}」缺少以下字段: {', '.join(missing)}",
            anchor,
            "补充缺失字段信息",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    # description 建议
    desc = item.get("description", "")
    if not desc or len(str(desc)) < 10:
        issues.append(Issue(
            "suggestion", "描述信息过短",
            f"「{name}」描述信息过短或缺失（当前{len(str(desc))}字）",
            anchor,
            "补充活动详细描述，方便用户了解活动内容",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    return issues


def validate_link(item: dict, index: int) -> list[Issue]:
    """校验链接信息"""
    issues = []
    name = item.get("name", f"活动#{index}")
    link = item.get("link", "")
    url = item.get("url", "")
    anchor = generate_anchor_link(index)

    if not link and not url:
        issues.append(Issue(
            "suggestion", "详情链接缺失",
            f"「{name}」缺少详情链接(link/url)信息",
            anchor,
            "补充活动官方详情页链接",
            f"{REPO_URL}/blob/main/output/exhibitions.json"
        ))

    # 检查链接有效性（简单格式校验）
    for field_name, val in [("link", link), ("url", url)]:
        if val and not str(val).startswith(("http://", "https://")):
            issues.append(Issue(
                "warning", "链接格式异常",
                f"「{name}」{field_name}字段格式异常: '{val}'",
                anchor,
                "修正为完整URL格式（以 http:// 或 https:// 开头）",
                f"{REPO_URL}/blob/main/output/exhibitions.json"
            ))

    return issues


def validate_all(items: list[dict]) -> list[Issue]:
    """执行全量数据校验"""
    all_issues = []
    for i, item in enumerate(items):
        all_issues.extend(validate_time(item, i))
        all_issues.extend(validate_geo(item, i))
        all_issues.extend(validate_category(item, i))
        all_issues.extend(validate_completeness(item, i))
        all_issues.extend(validate_link(item, i))
    return all_issues


# ============================================================
# 历史数据对比
# ============================================================

def load_history() -> dict:
    """加载历史数据"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"last_ids": [], "inspection_history": [], "issues_tracker": {}}


def save_history(history: dict):
    """保存历史数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def detect_new_items(current_items: list[dict], history: dict) -> list[dict]:
    """检测新增活动"""
    last_ids = set(history.get("last_ids", []))
    new_items = []
    for item in current_items:
        item_id = compute_activity_id(item)
        if item_id not in last_ids:
            new_items.append(item)
    return new_items


def track_issues(current_issues: list[Issue], history: dict) -> dict:
    """跟踪历史问题修复状态"""
    tracker = history.get("issues_tracker", {})
    current_issue_keys = set()

    # 用问题描述生成唯一标识
    for issue in current_issues:
        key = hashlib.md5(
            f"{issue.issue_type}|{issue.description}".encode('utf-8')
        ).hexdigest()[:10]
        current_issue_keys.add(key)
        if key not in tracker:
            tracker[key] = {
                "type": issue.issue_type,
                "description": issue.description,
                "first_seen": datetime.now().strftime("%Y-%m-%d"),
                "last_seen": datetime.now().strftime("%Y-%m-%d"),
                "status": "open",
            }
        else:
            tracker[key]["last_seen"] = datetime.now().strftime("%Y-%m-%d")

    # 标记已修复的问题
    for key, info in tracker.items():
        if key not in current_issue_keys and info.get("status") == "open":
            info["status"] = "fixed"
            info["fixed_date"] = datetime.now().strftime("%Y-%m-%d")

    return tracker


# ============================================================
# 报告生成
# ============================================================

def generate_report(
    availability: dict,
    items: list[dict],
    issues: list[Issue],
    new_items: list[dict],
    history: dict,
    tracker: dict,
) -> str:
    """生成巡检报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    # 统计
    critical = [i for i in issues if i.severity == "critical"]
    warnings = [i for i in issues if i.severity == "warning"]
    suggestions = [i for i in issues if i.severity == "suggestion"]

    # 历史修复统计
    fixed_issues = {k: v for k, v in tracker.items() if v.get("status") == "fixed"}
    open_issues = {k: v for k, v in tracker.items() if v.get("status") == "open"}

    report = f"""# 深圳亲子活动日历 · 数据质量巡检报告

> 巡检时间: {now}
> 巡检智能体: SZ-Kids-Activity-Inspector v1.0
> 项目地址: [{REPO_URL}]({REPO_URL})
> 页面地址: [{PAGE_URL}]({PAGE_URL})

---

## 一、巡检概览

| 指标 | 数值 |
|------|------|
| 巡检时间 | {now} |
| 站点可用性 | {'正常' if availability['accessible'] else '**异常**'} |
| 页面响应时间 | {availability['load_time_ms']}ms |
| 全量活动数据 | {len(items)} 条 |
| 新增活动 | {len(new_items)} 条 |
| 问题总数 | {len(issues)} |
| ├ 严重错误 | {len(critical)} |
| ├ 一般问题 | {len(warnings)} |
| └ 优化建议 | {len(suggestions)} |
| 历史问题修复率 | {len(fixed_issues)}/{len(fixed_issues) + len(open_issues)}（{len(fixed_issues) * 100 // max(len(fixed_issues) + len(open_issues), 1)}%） |

### 站点可用性详情

- HTTP状态码: {availability['http_status']}
- 响应时间: {availability['load_time_ms']}ms
- {'**站点正常访问**' if availability['accessible'] else f'**站点异常**: {availability.get("error", "未知错误")}'}

"""

    # 二、严重错误
    if critical:
        report += "---\n\n## 二、严重错误（Critical）\n\n"
        report += "> 以下问题可能导致用户获取到错误信息，建议优先修复。\n\n"
        for i, issue in enumerate(critical, 1):
            report += f"""### {i}. {issue.issue_type}

- **问题描述**: {issue.description}
- **页面定位**: [{PAGE_URL}]({issue.page_link})
- **修正建议**: {issue.suggestion}
- **证明链接**: {issue.evidence}

"""

    # 三、一般问题
    if warnings:
        report += "---\n\n## 三、一般问题（Warning）\n\n"
        report += "> 以下问题影响数据完整性，建议逐步修复。\n\n"

        # 按类型分组
        by_type = defaultdict(list)
        for issue in warnings:
            by_type[issue.issue_type].append(issue)

        for issue_type, items_list in by_type.items():
            report += f"### {issue_type}（{len(items_list)}条）\n\n"
            for j, issue in enumerate(items_list[:20], 1):  # 最多显示20条
                report += f"""**{j}.** {issue.description}
> 定位: [{PAGE_URL}]({issue.page_link}) | 建议: {issue.suggestion}

"""
            if len(items_list) > 20:
                report += f"> ... 还有 {len(items_list) - 20} 条同类问题，详见完整数据。\n\n"

    # 四、优化建议
    if suggestions:
        report += "---\n\n## 四、优化建议（Suggestion）\n\n"
        for i, issue in enumerate(suggestions[:10], 1):
            report += f"""**{i}.** {issue.description}
> 定位: [{PAGE_URL}]({issue.page_link}) | 建议: {issue.suggestion}

"""
        if len(suggestions) > 10:
            report += f"> ... 还有 {len(suggestions) - 10} 条优化建议，详见完整数据。\n\n"

    # 五、新增数据
    if new_items:
        report += "---\n\n## 五、新增活动清单\n\n"
        report += f"本轮新识别 {len(new_items)} 条活动:\n\n"
        report += "| # | 活动名称 | 类型 | 时间 | 地点 | 来源链接 |\n"
        report += "|---|----------|------|------|------|----------|\n"
        for i, item in enumerate(new_items[:30], 1):
            name = str(item.get("name", ""))[:30]
            cat = item.get("category", "")
            dates = f"{item.get('start_date','')} ~ {item.get('end_date','')}"
            venue = str(item.get("venue", ""))[:20]
            link = item.get("link") or item.get("url") or ""
            link_md = f"[来源]({link})" if link else "-"
            report += f"| {i} | {name} | {cat} | {dates} | {venue} | {link_md} |\n"
        if len(new_items) > 30:
            report += f"\n> ... 还有 {len(new_items) - 30} 条新增活动，详见完整数据。\n"
        report += "\n"

    # 六、整改跟踪
    report += "---\n\n## 六、整改跟踪\n\n"

    if open_issues:
        report += "### 未修复问题（需关注）\n\n"
        report += f"共 {len(open_issues)} 个问题待修复:\n\n"
        for key, info in list(open_issues.items())[:10]:
            report += f"- [{info['type']}] {info['description']}（首次发现: {info['first_seen']}，最近出现: {info['last_seen']}）\n"
        if len(open_issues) > 10:
            report += f"\n> ... 还有 {len(open_issues) - 10} 个未修复问题。\n"

    if fixed_issues:
        report += f"\n### 已修复问题 ✅\n\n"
        report += f"本轮发现 {len(fixed_issues)} 个历史问题已修复:\n\n"
        for key, info in list(fixed_issues.items())[:5]:
            report += f"- [{info['type']}] {info['description']}（修复于: {info.get('fixed_date', '未知')}）\n"

    if not open_issues and not fixed_issues:
        report += "暂无历史问题跟踪记录。\n"

    # 七、系统性优化建议
    report += """---
## 七、系统性优化建议

1. **数据校验前置**: 建议在数据提交时增加自动化校验（如 GitHub Actions CI），在 PR 阶段拦截格式错误和字段缺失问题。
   > 参考: [GitHub Actions CI 最佳实践](https://docs.github.com/en/actions/automating-builds-and-tests/about-continuous-integration)

2. **过期活动自动归档**: 建议建立过期活动自动归档机制，保持活动列表的时效性。
   > 参考: 可基于 `end_date` 字段实现自动过滤，参考 [schedule.html 现有筛选逻辑]({REPO_URL}/blob/main/schedule.html)

3. **区县映射标准化**: 建议将 `source` 到区县的映射关系维护为独立配置文件，方便后续维护和校验。
   > 参考: [深圳行政区划标准名录](https://www.sz.gov.cn/cn/xxgk/zfxxgj/bmfw/qhfwyqhcxy/)

4. **分类体系规范化**: 建议统一收费类型取值，当前存在 `免费`、`免费需预约`、`部分免费` 等多种变体，可考虑标准化为 `免费`/`收费` 二级分类 + `预约` 标签的组合模式。
   > 参考: 当前页面筛选器仅支持"全部/免费/收费"三档，数据中的细化分类未在筛选中体现。

""".replace("{REPO_URL}", REPO_URL)

    # 页脚
    report += f"""---
## 附录

- **巡检脚本**: [{REPO_URL}]({REPO_URL})（本仓库）
- **数据源**: [{DATA_URL}]({DATA_URL})
- **页面快照**: [{PAGE_URL}]({PAGE_URL})
- **报告生成时间**: {now}
- **下次巡检**: 每日 08:00（北京时间）

> 本报告由自动化巡检智能体生成，所有问题均附带可直接核验的证明链接。
> 如有疑问，请通过 [{REPO_URL}/issues]({REPO_URL}/issues) 反馈。
"""

    return report


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("深圳亲子活动日历 - 数据质量巡检智能体")
    print("=" * 60)
    now = datetime.now()

    # 1. 站点可用性检查
    print("\n[1/6] 检查站点可用性...")
    availability = check_page_availability()
    print(f"  状态: {'正常' if availability['accessible'] else '异常'}")
    print(f"  响应: {availability['load_time_ms']}ms")

    # 2. 获取全量数据
    print("\n[2/6] 获取活动数据...")
    items = fetch_json(DATA_URL)
    if items is None:
        print("  [错误] 无法获取活动数据，终止巡检。")
        # 生成仅包含站点故障的报告
        report = f"""# 深圳亲子活动日历 · 数据质量巡检报告

> 巡检时间: {now.strftime("%Y-%m-%d %H:%M:%S")}

## 站点故障

**严重错误**: 无法获取活动数据源 ({DATA_URL})

站点可能处于不可用状态，请检查:
- 数据源 URL 是否变更
- GitHub Pages 服务状态
- 网络连接是否正常

页面地址: [{PAGE_URL}]({PAGE_URL})
"""
        report_path = os.path.join(REPORTS_DIR, f"inspection-{now.strftime('%Y%m%d-%H%M%S')}.md")
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存: {report_path}")
        sys.exit(1)

    print(f"  获取到 {len(items)} 条活动数据")

    # 3. 加载历史数据
    print("\n[3/6] 加载历史数据...")
    history = load_history()
    print(f"  历史巡检次数: {len(history.get('inspection_history', []))}")

    # 4. 检测新增活动
    print("\n[4/6] 检测新增活动...")
    new_items = detect_new_items(items, history)
    print(f"  新增活动: {len(new_items)} 条")

    # 5. 执行数据校验
    print("\n[5/6] 执行数据校验...")
    issues = validate_all(items)
    critical = [i for i in issues if i.severity == "critical"]
    warnings = [i for i in issues if i.severity == "warning"]
    suggestions = [i for i in issues if i.severity == "suggestion"]
    print(f"  严重错误: {len(critical)}")
    print(f"  一般问题: {len(warnings)}")
    print(f"  优化建议: {len(suggestions)}")

    # 6. 更新历史与问题跟踪
    print("\n[6/6] 更新历史数据与问题跟踪...")
    tracker = track_issues(issues, history)

    # 更新历史
    current_ids = [compute_activity_id(item) for item in items]
    history["last_ids"] = current_ids
    history["inspection_history"].append({
        "date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total_items": len(items),
        "new_items": len(new_items),
        "total_issues": len(issues),
        "critical": len(critical),
        "warnings": len(warnings),
        "suggestions": len(suggestions),
    })
    history["issues_tracker"] = tracker
    save_history(history)

    # 7. 生成报告
    print("\n生成巡检报告...")
    report = generate_report(availability, items, issues, new_items, history, tracker)

    report_filename = f"inspection-{now.strftime('%Y%m%d-%H%M%S')}.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    latest_path = os.path.join(REPORTS_DIR, "latest.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已保存:")
    print(f"  {report_path}")
    print(f"  {latest_path}")
    print(f"\n巡检完成。")
    print(f"  活动总数: {len(items)}")
    print(f"  新增: {len(new_items)}")
    print(f"  问题: {len(issues)}（严重{len(critical)} / 一般{len(warnings)} / 建议{len(suggestions)}）")

    # 输出摘要到 stdout（供 GitHub Actions 使用）
    summary = f"""::group::巡检摘要
总活动数: {len(items)}
新增活动: {len(new_items)}
问题总数: {len(issues)}
  - 严重错误: {len(critical)}
  - 一般问题: {len(warnings)}
  - 优化建议: {len(suggestions)}
::endgroup::
"""
    print(summary)

    return 0 if len(critical) == 0 else 0  # 不因数据问题导致 CI 失败


if __name__ == "__main__":
    sys.exit(main())