#!/usr/bin/env python3
"""
新活动发现脚本 —— 基于 Web 搜索发现 goout 数据中缺失的活动，提交 Issue 提醒维护者更新。
每条 Issue 都附带证据链接，便于维护者核对和录入。
"""
import json, os, urllib.request, hashlib
from datetime import datetime

TOKEN = os.environ["GOOUT_PAT"]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json"
}
GOOUT_REPO = "islon/goout"
INSPECTOR_REPO = "islon/for-goout-inspector"
DATA_URL = "https://raw.githubusercontent.com/islon/goout/main/output/exhibitions.json"
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

def fetch_goout_data():
    """获取 goout 现有活动数据"""
    try:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Failed to fetch goout data: {e}")
        # 尝试本地缓存
        for path in ["data/current.json", "exhibitions.json"]:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        return []

def normalize(s):
    """归一化字符串用于比较"""
    return "".join(c for c in s if c.isalnum()).lower()

def event_exists(data, title):
    """检查活动标题是否已存在于 goout 数据中"""
    norm_title = normalize(title)
    for item in data:
        existing = normalize(item.get("title", ""))
        if norm_title in existing or existing in norm_title:
            return True
    return False

# ============================================================
# 已发现的新活动（基于 Web 搜索，附带证据链接）
# 每个活动包含: title, venue, district, date_range, address, 
#               category, evidence_url, description, source_name
# ============================================================
DISCOVERED_EVENTS = [
    # --- 深圳博物馆新展 ---
    {
        "title": "宠·爱——猫猫狗狗的世界",
        "venue": "深圳博物馆金田路馆（历史民俗）",
        "district": "福田区",
        "date_range": "即日起至2026年7月（具体日期待定）",
        "address": "深圳市福田区金田路市民中心A区",
        "category": "展览",
        "evidence_url": "http://www.sznews.com/news/content/mb/2026-07/03/content_32110315.htm",
        "description": "汇集80件/套展品，梳理人与猫狗跨越万年的相伴羁绊。引入20余项法国原版科学互动展项，依托动物行为学、遗传学、神经学研究，让科普可看、可玩、可体验。暑期延时开放至21:00。",
        "source_name": "深圳特区报/深圳新闻网"
    },
    # --- 深圳音乐厅亲子演出 ---
    {
        "title": "歌剧双生的烈焰与星辰《乡村骑士》×《丑角》音乐会版歌剧——深圳交响乐团2025-2026音乐季闭幕音乐会",
        "venue": "深圳音乐厅",
        "district": "福田区",
        "date_range": "2026年7月17日（周五）19:30",
        "address": "深圳市福田区福中一路2016号",
        "category": "演出",
        "evidence_url": "https://www.szyyt.com/performance/show_100000937342526.html",
        "description": "深圳交响乐团2025-2026音乐季闭幕音乐会，两大经典歌剧同台。",
        "source_name": "深圳音乐厅官网"
    },
    {
        "title": "漫步古典夜 时光的折痕——长笛与吉他二重奏音乐会",
        "venue": "深圳音乐厅",
        "district": "福田区",
        "date_range": "2026年7月18日（周六）19:30",
        "address": "深圳市福田区福中一路2016号",
        "category": "演出",
        "evidence_url": "https://www.szyyt.com/performance/show_100000954193225.html",
        "description": "漫步古典夜系列，长笛与吉他二重奏，演绎时光的折痕。",
        "source_name": "深圳音乐厅官网"
    },
    {
        "title": "第二十四届中外艺术精品演出季 柴可夫斯基《天鹅湖》主题音乐会",
        "venue": "深圳音乐厅五楼小剧场",
        "district": "福田区",
        "date_range": "2026年7月25日（周六）19:30",
        "address": "深圳市福田区福中一路2016号",
        "category": "演出",
        "evidence_url": "https://www.szyyt.com/performance/show_100000984262811.html",
        "description": "广州市同曲异工乐团演绎，以新世纪音乐风格呈现柴可夫斯基《天鹅湖》经典曲目。2周岁以上儿童可入场。票价80-280元。",
        "source_name": "深圳音乐厅官网"
    },
    {
        "title": "第二十四届中外艺术精品演出季 '跟着音乐去旅行'暑期亲子音乐会",
        "venue": "深圳音乐厅",
        "district": "福田区",
        "date_range": "2026年8月7日（周五）19:30",
        "address": "深圳市福田区福中一路2016号",
        "category": "演出",
        "evidence_url": "https://www.szyyt.com/",
        "description": "暑期亲子音乐会，适合带孩子一起感受音乐的魅力，在旋律中环游世界。",
        "source_name": "深圳音乐厅官网"
    },
    # --- 光明文化艺术中心 ---
    {
        "title": "气泡王国——比利时国宝漫画百年巡礼",
        "venue": "光明文化艺术中心美术馆",
        "district": "光明区",
        "date_range": "2026年7月2日至9月19日",
        "address": "深圳市光明区光明街道创投路与观光路交汇处",
        "category": "展览",
        "evidence_url": "http://m.toutiao.com/group/7658235446731784744/",
        "description": "汇聚《丁丁历险记》《蓝精灵》等九大比利时国宝级漫画IP，百余件珍贵手稿、版画、雕塑。免费开放，适合全年龄段。蓝精灵户外装置同步展出。",
        "source_name": "光明文化艺术中心/今日头条"
    },
    {
        "title": "北京人艺话剧《寻找春柳社》",
        "venue": "光明文化艺术中心·演艺中心·音乐厅",
        "district": "光明区",
        "date_range": "2026年7月10日（周五）20:00",
        "address": "深圳市光明区光明街道创投路与观光路交汇处",
        "category": "演出",
        "evidence_url": "http://m.toutiao.com/group/7659324778305684020/",
        "description": "北京人艺倾情演出，以'戏中戏'结构讲述当代大学生还原百年前中国第一个话剧团体春柳社的故事。",
        "source_name": "光明文化艺术中心"
    },
    {
        "title": "北京舞蹈学院原创舞剧《巍巍正阳》",
        "venue": "光明文化艺术中心·演艺中心·大剧场",
        "district": "光明区",
        "date_range": "2026年7月18日-19日",
        "address": "深圳市光明区光明街道创投路与观光路交汇处",
        "category": "演出",
        "evidence_url": "http://m.toutiao.com/group/7659324778305684020/",
        "description": "阿云嘎献唱主题曲《守望》，马蛟龙、孙科等实力舞者加盟。以正阳门下一家五代人命运流转，铺展中国近现代史长卷。",
        "source_name": "光明文化艺术中心"
    },
    {
        "title": "陈萨、孙一凡与国家大剧院管弦乐团室内乐团——瓦格纳与常乐《自然之诗》",
        "venue": "光明文化艺术中心·演艺中心·大剧场",
        "district": "光明区",
        "date_range": "2026年7月26日（周日）20:00",
        "address": "深圳市光明区光明街道创投路与观光路交汇处",
        "category": "演出",
        "evidence_url": "http://m.toutiao.com/group/7659324778305684020/",
        "description": "唯一包揽三大国际钢琴赛事大奖的中国钢琴家陈萨，指挥冠军孙一凡与国家大剧院管弦乐团室内乐团强强联袂。",
        "source_name": "光明文化艺术中心"
    },
    # --- 儿童剧 ---
    {
        "title": "国风儿童剧《少年诗词游之李白》",
        "venue": "茅洲河体育艺术中心剧场",
        "district": "光明区",
        "date_range": "2026年7月12日（周六）15:30",
        "address": "深圳市光明区茅洲河体育艺术中心",
        "category": "演出",
        "evidence_url": "https://m.sohu.com/a/1037850628_122892870/",
        "description": "诗词大会式的国风儿童剧，带孩子走进诗仙李白的世界，寓教于乐。",
        "source_name": "荣艺文化/搜狐"
    },
    {
        "title": "科普绘本剧《肚子里的火车站》",
        "venue": "茅洲河体育艺术中心剧场",
        "district": "光明区",
        "date_range": "2026年7月18日（周五）15:30",
        "address": "深圳市光明区茅洲河体育艺术中心",
        "category": "演出",
        "evidence_url": "https://m.sohu.com/a/1037850628_122892870/",
        "description": "根据德国经典科普绘本改编，让孩子了解消化系统的奥秘，趣味科普舞台剧。",
        "source_name": "荣艺文化/搜狐"
    },
    {
        "title": "百老汇儿童剧《原始人大冒险》",
        "venue": "玉塘文体中心",
        "district": "光明区",
        "date_range": "2026年7月19日（周六）15:30",
        "address": "深圳市光明区玉塘文体中心",
        "category": "演出",
        "evidence_url": "https://m.sohu.com/a/1037850628_122892870/",
        "description": "百老汇风格儿童剧，带领小朋友穿越原始时代展开冒险。",
        "source_name": "荣艺文化/搜狐"
    },
    {
        "title": "沉浸式互动亲子科学剧《数学秀》",
        "venue": "深圳龙岗国际艺术中心",
        "district": "龙岗区",
        "date_range": "2026年8月8日（周六）10:30",
        "address": "深圳市龙岗区龙岗国际艺术中心",
        "category": "演出",
        "evidence_url": "https://m.sohu.com/a/1045463665_675420/",
        "description": "不是数学课，是一场数学奇幻大冒险！激光三维坐标轴、莫比乌斯环过山车、π博士穿越古今，80分钟让孩子爱上数学。早鸟票99元起。",
        "source_name": "深圳梦/搜狐"
    },
    # --- 美术馆/博物馆展览 ---
    {
        "title": "笔墨同心·林墉、苏华作品展",
        "venue": "何香凝美术馆",
        "district": "南山区",
        "date_range": "2026年6月20日至8月9日",
        "address": "深圳市南山区深南大道9013号",
        "category": "展览",
        "evidence_url": "http://m.toutiao.com/group/7658324154139148850/",
        "description": "全面呈现林墉'霸悍恣丽'的水墨人物风骨与苏华'豪迈雄放'的书画才情。免费免预约。",
        "source_name": "南山融媒体中心"
    },
    {
        "title": "薪火相传 稚笔生花——2026深圳美术馆少儿艺术展",
        "venue": "深圳美术馆",
        "district": "龙华区",
        "date_range": "2026年5月29日至10月31日",
        "address": "深圳市龙华区腾龙路30号",
        "category": "展览",
        "evidence_url": "http://m.toutiao.com/group/7658324154139148850/",
        "description": "从全市1400余件投稿中遴选出140幅少儿佳作，涵盖国画、油画、水彩、数字艺术等。免费免预约。",
        "source_name": "南山融媒体中心"
    },
    {
        "title": "丹青联心——深澳两地书画艺术交流展",
        "venue": "福田美术馆",
        "district": "福田区",
        "date_range": "2026年7月5日至7月30日",
        "address": "深圳市福田区梅林街道梅东二路5号",
        "category": "展览",
        "evidence_url": "http://m.toutiao.com/group/7659258111554961955/",
        "description": "汇聚深澳两地书画名家精品力作140余幅，涵盖国画山水、书法、现代水墨、油画等。免费开放。",
        "source_name": "南方都市报"
    },
    # --- 户外/乐园活动 ---
    {
        "title": "《海洋奇缘：启航》迪士尼电影主题展",
        "venue": "深圳人才公园潮汐广场",
        "district": "南山区",
        "date_range": "2026年7月1日至7月31日",
        "address": "深圳市南山区科苑南路3329号",
        "category": "户外活动",
        "evidence_url": "http://m.toutiao.com/group/7658324154139148850/",
        "description": "还原莫阿娜同款航海木舟、巨型毛伊鱼钩气模、寻路花环秋千等电影场景，拍照打卡。免费免预约。地铁13号线'人才公园站'B1出口。",
        "source_name": "南山融媒体中心"
    },
    {
        "title": "深圳欢乐谷·夏浪狂欢节",
        "venue": "深圳欢乐谷",
        "district": "南山区",
        "date_range": "2026年7月4日起至8月中旬，每周五至周日及法定节假日",
        "address": "深圳市南山区华侨城",
        "category": "户外活动",
        "evidence_url": "https://m.sohu.com/a/1045463665_675420/",
        "description": "全网爆火'大湾鸡天团'空降，夏浪音乐节周周有大咖，清凉水战+电音派对+明星演出。票价130-228元。",
        "source_name": "深圳梦/搜狐"
    },
    {
        "title": "深圳世界之窗·WoW潮音嘉年华+啤酒节",
        "venue": "深圳世界之窗",
        "district": "南山区",
        "date_range": "2026年6月18日至8月30日，每周五至周日",
        "address": "深圳市南山区深南大道9037号",
        "category": "户外活动",
        "evidence_url": "https://m.sohu.com/a/1045463665_675420/",
        "description": "33天露天音乐节，集结焦迈奇、HIGH5、井胧等艺人，罗马假日广场冰镇啤酒+烧烤+音乐派对。",
        "source_name": "深圳梦/搜狐"
    },
    {
        "title": "锦绣中华民俗村·夏浪民族狂欢节",
        "venue": "锦绣中华民俗村",
        "district": "南山区",
        "date_range": "2026年7月4日至8月15日",
        "address": "深圳市南山区深南大道9003号",
        "category": "户外活动",
        "evidence_url": "https://m.sohu.com/a/1045463665_675420/",
        "description": "7位网红主理人每周轮值，全程带领游客沉浸式游玩互动。暑期亲子热门目的地。",
        "source_name": "深圳梦/搜狐"
    },
    # --- 深圳戏院 ---
    {
        "title": "儿童音乐皮影戏",
        "venue": "深圳戏院",
        "district": "罗湖区",
        "date_range": "2026年7月11日至12日",
        "address": "深圳市罗湖区新园路1号",
        "category": "演出",
        "evidence_url": "https://m.sohu.com/a/1047290911_122091088/",
        "description": "深圳戏院'少儿演出季'系列，传统皮影戏融合音乐元素，适合亲子观看。地铁1/3号线老街站F出口。",
        "source_name": "艺览无余/搜狐"
    },
    {
        "title": "炫彩青春——优秀青年京剧演员展演",
        "venue": "深圳戏院",
        "district": "罗湖区",
        "date_range": "2026年7月14日至19日",
        "address": "深圳市罗湖区新园路1号",
        "category": "演出",
        "evidence_url": "https://m.sohu.com/a/1047290911_122091088/",
        "description": "中国京剧艺术基金会与深圳京剧院联合主办，剧目包括《满江红》《寻觅清照》《杨门女将》，张建国等名家领衔。",
        "source_name": "艺览无余/搜狐"
    },
    # --- 深圳图书馆 ---
    {
        "title": "深圳图书馆第十二届'暑期缤纷季'——近300场阅读活动",
        "venue": "深圳图书馆（中心馆+北馆）",
        "district": "福田区/龙华区",
        "date_range": "2026年7月至8月",
        "address": "中心馆：福田区福中一路2001号；北馆：龙华区腾龙路30号",
        "category": "亲子活动",
        "evidence_url": "http://www.sznews.com/news/content/2026-07/08/content_32114626.htm",
        "description": "含8大类69节免费公益培训课（语言朗诵、创意美术、魔方、棋艺、科创等）、人文通识课、走读深圳研学、AI训练营、成语小课堂等近300场活动。面向5-16岁青少年。",
        "source_name": "深圳特区报/深圳新闻网"
    },
    # --- 宝安大仟里 ---
    {
        "title": "宝安大仟里首届暑期儿童戏剧节",
        "venue": "宝安大仟里",
        "district": "宝安区",
        "date_range": "2026年7月4日至8月31日",
        "address": "深圳市宝安区宝安大道与海城路交汇处",
        "category": "亲子活动",
        "evidence_url": "https://sz.ifeng.com/c/8uQvmmWyQO0",
        "description": "联袂小橙堡儿童艺术剧团，连续8周30场活动。五大剧目轮番登场：《和风一起散步》《吹牛大王历险记》《小红帽》《丑小鸭》等。免费儿童用品、星空楼梯乐园、白鸽广场等亲子设施。",
        "source_name": "凤凰网深圳"
    },
    # --- 罗湖 ---
    {
        "title": "罗湖一站式普惠托育集市",
        "venue": "翠湖文体公园拾光草坪",
        "district": "罗湖区",
        "date_range": "2026年7月11日（周六）15:00-19:00",
        "address": "深圳市罗湖区翠湖文体公园",
        "category": "亲子活动",
        "evidence_url": "http://m.toutiao.com/group/7660412037217993243/",
        "description": "备案托育机构现场驻点、儿童保健义诊、童话游园（九宫格扔沙包、套大鹅、跳房子、投壶）、舞台汇演。适合0-3岁宝宝家庭。",
        "source_name": "罗湖发布"
    },
]

def main():
    print(f"=== 新活动发现扫描 ({TODAY}) ===\n")
    
    print("正在获取 goout 现有活动数据...")
    data = fetch_goout_data()
    print(f"  goout 现有 {len(data)} 条活动\n")
    
    missing = []
    for event in DISCOVERED_EVENTS:
        if event_exists(data, event["title"]):
            print(f"  [已有] {event['title']}")
        else:
            print(f"  [缺失] {event['title']}")
            missing.append(event)
    
    print(f"\n共发现 {len(missing)} 个缺失活动\n")
    
    if not missing:
        print("没有新活动需要提醒。")
        return
    
    # 检查已有 Issue 避免重复创建
    existing_issues = api("GET", f"/repos/{GOOUT_REPO}/issues?labels=new-event-discovery&state=open&per_page=100")
    existing_titles = set()
    if existing_issues:
        for iss in existing_issues:
            existing_titles.add(iss.get("title", ""))
    
    created = 0
    skipped = 0
    
    for event in missing:
        title = event["title"]
        issue_title = f"[新活动发现] {title}"
        
        # 跳过已存在的 Issue（按标题去重）
        if issue_title in existing_titles:
            print(f"  [跳过] Issue 已存在: {issue_title}")
            skipped += 1
            continue
        
        # 构建 Issue body
        body = f"""## 发现新活动

### 活动信息

| 字段 | 内容 |
|------|------|
| **活动名称** | {event['title']} |
| **场馆** | {event['venue']} |
| **所在区** | {event['district']} |
| **时间** | {event['date_range']} |
| **地址** | {event['address']} |
| **类型** | {event['category']} |

### 活动描述

{event['description']}

### 证据链接

- 来源: [{event['source_name']}]({event['evidence_url']})

### 建议

请将此活动添加到 `output/exhibitions.json` 数据中，以便在 [深圳亲子活动日历](https://islon.github.io/goout/schedule.html) 上展示。

---
> 本 Issue 由 [新活动发现智能体](https://github.com/{INSPECTOR_REPO}) 自动生成
> 发现时间: {TODAY}
> 标签: `new-event-discovery`
"""
        
        result = api("POST", f"/repos/{GOOUT_REPO}/issues", {
            "title": issue_title,
            "body": body,
            "labels": ["new-event-discovery", "automated"]
        })
        if result:
            print(f"  [创建] Issue #{result['number']}: {result['html_url']}")
            created += 1
        else:
            print(f"  [失败] 无法创建 Issue: {issue_title}")
    
    print(f"\n=== 完成: 创建 {created} 个 Issue, 跳过 {skipped} 个 ===")

if __name__ == "__main__":
    main()