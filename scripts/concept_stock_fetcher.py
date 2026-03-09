#!/usr/bin/env python3
"""
概念板块个股查询工具
支持东方财富 API + 本地缓存 + 内置映射兜底
"""

import requests
import json
import time
import random
from pathlib import Path
from typing import List, Dict
from urllib.parse import quote

# User-Agent 池
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.1',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

CACHE_DIR = Path(__file__).parent.parent / "cache" / "concepts"
CACHE_EXPIRE_DAYS = 7

session = requests.Session()
session.headers.update({
    'User-Agent': random.choice(USER_AGENTS),
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'identity',  # 禁用gzip压缩，避免LibreSSL环境下解压失败
    'Connection': 'keep-alive'
})


def search_concept_stocks(keyword: str, use_cache: bool = True) -> List[Dict]:
    """
    通过关键词搜索相关概念板块的个股列表

    Args:
        keyword: 行业/产品/概念关键词，例如 "燃气轮机", "钾肥", "海上风电"
        use_cache: 是否使用本地缓存（7天有效）

    Returns:
        个股列表，每个元素包含: code, name, concept, relevance, business
    """
    # 1. 检查缓存
    if use_cache:
        cache_file = CACHE_DIR / f"{keyword}.json"
        if cache_file.exists():
            if time.time() - cache_file.stat().st_mtime < CACHE_EXPIRE_DAYS * 86400:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass

    # 2. 东方财富 API
    stocks = _search_eastmoney_concept(keyword)
    if stocks:
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_DIR / f"{keyword}.json", 'w', encoding='utf-8') as f:
                json.dump(stocks, f, ensure_ascii=False, indent=2)
        return stocks

    # 3. 内置映射兜底
    return _get_fallback_stocks(keyword)

def _search_eastmoney_concept(keyword: str) -> List[Dict]:
    """从东方财富搜索概念板块个股"""
    try:
        search_url = f"https://searchapi.eastmoney.com/api/suggest/get?input={quote(keyword)}&type=14&token=D43BF722C8E39585C3EB54EE3A6D62E5"
        headers = {
            'Referer': 'https://www.eastmoney.com/',
            'User-Agent': random.choice(USER_AGENTS)
        }
        response = session.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 适配东方财富返回结构（新旧两种）
        plate_code = None
        plate_name = None
        if data.get('QuotationCodeTable') and data['QuotationCodeTable'].get('Data'):
            concept = data['QuotationCodeTable']['Data'][0]
            plate_code = concept['Code'].replace('BK', '')
            plate_name = concept['Name']
        elif data.get('Result') and data['Result'].get('ConceptPlate'):
            concept = data['Result']['ConceptPlate'][0]
            plate_code = concept['Code']
            plate_name = concept['Name']
        if not plate_code or not plate_name:
            return []

        stock_url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f3&fs=b:BK{plate_code}&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13"
        response = session.get(stock_url, headers=headers, timeout=10)
        response.raise_for_status()
        stock_data = response.json()

        if not stock_data.get('data') or not stock_data['data'].get('diff'):
            return []

        stocks = []
        for i, item in enumerate(stock_data['data']['diff']):
            code = item['f12']
            if code.startswith('6'):
                full_code = f"sh{code}"
            elif code.startswith(('0', '3')):
                full_code = f"sz{code}"
            else:
                continue
            relevance = 5 if i < 20 else 4 if i < 50 else 3
            stocks.append({
                "code": full_code,
                "name": item['f14'],
                "concept": plate_name,
                "relevance": relevance,
                "business": f"属于{plate_name}概念板块"
            })
        return stocks[:30]

    except Exception as e:
        print(f"东方财富概念搜索失败: {e}")
        return []

def _get_fallback_stocks(keyword: str) -> List[Dict]:
    """API 失败时使用内置映射兜底"""
    common_mapping = {
            "燃气轮机": [
                {"code": "sh600875", "name": "东方电气", "relevance": 5, "business": "国内燃气轮机龙头，具备重型燃机自主研发能力"},
                {"code": "sh601727", "name": "上海电气", "relevance": 5, "business": "国内第二大燃气轮机制造商"},
                {"code": "sh603308", "name": "应流股份", "relevance": 4, "business": "燃气轮机叶片核心供应商，全球市占率领先"},
                {"code": "sz002353", "name": "杰瑞股份", "relevance": 4, "business": "燃气轮机装备及服务提供商"},
                {"code": "sh605060", "name": "联德股份", "relevance": 3, "business": "燃气轮机核心精密铸件供应商"},
                {"code": "sz002380", "name": "科远智慧", "relevance": 3, "business": "燃气轮机控制系统提供商"},
                {"code": "sz002255", "name": "海陆重工", "relevance": 3, "business": "燃气轮机余热锅炉龙头"},
                {"code": "sh600416", "name": "湘电股份", "relevance": 3, "business": "特种燃气轮机技术储备"},
                {"code": "hk01072", "name": "东方电气", "relevance": 5, "business": "东方电气H股，估值更低"},
                {"code": "hk02727", "name": "上海电气", "relevance": 4, "business": "上海电气H股"}
            ],
            "钾肥": [
                {"code": "sz000792", "name": "盐湖股份", "relevance": 5, "business": "国内钾肥龙头，钾肥产能500万吨/年"},
                {"code": "sz000408", "name": "藏格矿业", "relevance": 5, "business": "国内第二大钾肥生产商，产能200万吨/年"},
                {"code": "sz002545", "name": "东方铁塔", "relevance": 4, "business": "境外钾肥产能100万吨/年"},
                {"code": "sh600251", "name": "冠农股份", "relevance": 4, "business": "参股国投罗钾，享有钾肥收益"},
                {"code": "sh600096", "name": "云天化", "relevance": 3, "business": "国内磷复肥龙头，配套钾肥产能"},
                {"code": "sh600792", "name": "云煤能源", "relevance": 3, "business": "间接持有钾肥项目股权"},
                {"code": "sz000839", "name": "中信国安", "relevance": 3, "business": "参股青海盐湖钾肥项目"}
            ],
            "算力": [
                {"code": "sz000977", "name": "浪潮信息", "relevance": 5, "business": "国内服务器龙头，市占率第一"},
                {"code": "sz300308", "name": "中际旭创", "relevance": 5, "business": "全球光模块龙头，800G/1.6T产品领先"},
                {"code": "sh603019", "name": "中科曙光", "relevance": 4, "business": "国产服务器龙头，算力基建核心"},
                {"code": "sz002261", "name": "拓维信息", "relevance": 4, "business": "华为昇腾服务器核心合作伙伴"},
                {"code": "sz000938", "name": "紫光股份", "relevance": 4, "business": "新华三服务器和交换机龙头"},
                {"code": "sh688041", "name": "海光信息", "relevance": 4, "business": "国产CPU龙头，算力芯片核心"},
                {"code": "sh688256", "name": "寒武纪", "relevance": 4, "business": "AI芯片独角兽，算力芯片提供商"}
            ],
            "染料": [
                {"code": "sz002440", "name": "闰土股份", "relevance": 5, "business": "国内第二大分散染料生产商，产能11万吨/年"},
                {"code": "sz002738", "name": "中农立华", "relevance": 4, "business": "农药及染料中间体供应商"},
                {"code": "sh600352", "name": "浙江龙盛", "relevance": 5, "business": "全球染料龙头，分散染料产能30万吨/年，市占率第一"},
                {"code": "sh603181", "name": "皇马科技", "relevance": 3, "business": "特种表面活性剂和染料中间体生产商"},
                {"code": "sz002010", "name": "传化智联", "relevance": 3, "business": "纺织化学品和染料助剂龙头"},
                {"code": "sz002361", "name": "神剑股份", "relevance": 3, "business": "聚酯树脂和染料中间体供应商"},
                {"code": "sh600486", "name": "扬农化工", "relevance": 3, "business": "农药及精细化工中间体生产商"}
            ],
            "氦气": [
                {"code": "sh600256", "name": "广汇能源", "relevance": 5, "business": "国内最大的氦气生产商，年产氦气200万立方米，自给率第一"},
                {"code": "sz002978", "name": "安宁股份", "relevance": 4, "business": "钒钛磁铁矿提氦，具备氦气量产能力"},
                {"code": "sh603798", "name": "康普顿", "relevance": 4, "business": "参股公司具备氦气提纯和销售业务"},
                {"code": "sz000552", "name": "靖远煤电", "relevance": 3, "business": "煤层气提氦项目已投产，具备氦气产能"},
                {"code": "sh600989", "name": "宝丰能源", "relevance": 3, "business": "煤化工尾气提氦项目在建，未来产能可观"},
                {"code": "sz000830", "name": "鲁西化工", "relevance": 3, "business": "工业气体业务包含氦气提纯和销售"},
                {"code": "sh688239", "name": "杭氧股份", "relevance": 4, "business": "国内空分设备龙头，具备氦气提纯技术和产能"}
            ],
            "海上风电": [
                {"code": "sh601615", "name": "明阳智能", "relevance": 5, "business": "国内海上风电龙头，市占率第二，大容量海上机组技术领先"},
                {"code": "sz002202", "name": "金风科技", "relevance": 5, "business": "国内风电整机龙头，市占率第一，海上风电布局完善"},
                {"code": "sh688660", "name": "电气风电", "relevance": 5, "business": "上海电气旗下海上风电平台，大容量机组竞争力强"},
                {"code": "sz002531", "name": "天顺风能", "relevance": 4, "business": "海上风电塔筒/管桩龙头，产业链核心配套"},
                {"code": "sh603606", "name": "东方电缆", "relevance": 4, "business": "海上风电场内海缆供应商，市占率超50%"},
                {"code": "sh600875", "name": "东方电气", "relevance": 4, "business": "国内风电主机制造商之一，海上风电业务布局"}
            ],
            "特高压": [
                {"code": "sz002028", "name": "思源电气", "relevance": 5, "business": "特高压核心设备供应商，GIS、换流阀市占率领先"},
                {"code": "sh600406", "name": "国电南瑞", "relevance": 5, "business": "电网自动化绝对龙头，特高压二次设备市占率第一"},
                {"code": "sh600312", "name": "平高电气", "relevance": 4, "business": "特高压开关设备龙头"},
                {"code": "sz000400", "name": "许继电气", "relevance": 4, "business": "特高压直流设备核心供应商"},
                {"code": "sh600089", "name": "特变电工", "relevance": 5, "business": "特高压变压器龙头，新能源EPC业务协同发展"},
                {"code": "sh601179", "name": "中国西电", "relevance": 4, "business": "特高压一次设备核心供应商"}
            ],
            "电力电网": [
                {"code": "sh600406", "name": "国电南瑞", "relevance": 5, "business": "电网自动化龙头，受益于电网投资增长"},
                {"code": "sz002028", "name": "思源电气", "relevance": 5, "business": "输配电设备全产业链布局"},
                {"code": "sz000400", "name": "许继电气", "relevance": 4, "business": "直流输电设备龙头"},
                {"code": "sh600312", "name": "平高电气", "relevance": 4, "business": "开关设备龙头"},
                {"code": "sh601877", "name": "正泰电器", "relevance": 4, "business": "低压电器龙头，光伏+储能协同发展"}
            ],
            "海缆": [
                {"code": "sh603606", "name": "东方电缆", "relevance": 5, "business": "国内海缆绝对龙头，35kV/220kV/500kV全覆盖，海上风电海缆市占率超50%"},
                {"code": "sh600522", "name": "中天科技", "relevance": 5, "business": "国内第二大海缆供应商，海上风电+海洋工程双重布局"},
                {"code": "sh600487", "name": "亨通光电", "relevance": 4, "business": "海缆业务快速增长，海上风电海缆竞争力提升"},
                {"code": "sz002498", "name": "汉缆股份", "relevance": 4, "business": "海底电缆及海洋脐带缆供应商"},
                {"code": "sh600973", "name": "宝胜股份", "relevance": 3, "business": "特种电缆龙头，涉及海缆业务"},
                {"code": "sz002545", "name": "东方铁塔", "relevance": 3, "business": "海上风电安装平台及海缆敷设服务"}
            ],
            "海洋工程": [
                {"code": "sh600583", "name": "中国海油工程", "relevance": 5, "business": "海洋工程施工龙头，海底安装经验丰富，具备海底数据仓安装能力"},
                {"code": "sh600968", "name": "海油发展", "relevance": 5, "business": "海洋工程服务及海底施工，海上平台安装维护经验丰富"},
                {"code": "sh600320", "name": "振华重工", "relevance": 5, "business": "海上风电安装船/海工装备龙头，海底数据仓吊装设备提供商"},
                {"code": "sh600482", "name": "中国动力", "relevance": 4, "business": "船舶动力及海工装备核心供应商"},
                {"code": "sh601919", "name": "中远海控", "relevance": 4, "business": "海洋运输及海工物流服务"},
                {"code": "sz002255", "name": "海陆重工", "relevance": 4, "business": "海洋工程装备及海底管道安装"},
                {"code": "sh600150", "name": "中国船舶", "relevance": 3, "business": "船舶及海工平台制造"}
            ],
            "数据中心": [
                {"code": "sz002837", "name": "英维克", "relevance": 5, "business": "数据中心温控龙头，液冷/海水冷却技术储备"},
                {"code": "sz000977", "name": "浪潮信息", "relevance": 5, "business": "国内服务器龙头，数据中心IT设备核心供应商"},
                {"code": "sz300308", "name": "中际旭创", "relevance": 4, "business": "全球光模块龙头，数据中心光互连核心"},
                {"code": "sh603019", "name": "中科曙光", "relevance": 4, "business": "国产服务器龙头，数据中心算力基建核心"},
                {"code": "sh301018", "name": "申菱环境", "relevance": 4, "business": "数据中心空调系统，海水冷却改造"},
                {"code": "sz300215", "name": "电科院", "relevance": 3, "business": "数据中心电力检测及运维"},
                {"code": "sh688561", "name": "奇安信", "relevance": 3, "business": "数据中心网络安全"}
            ]
        }
        
    # 模糊匹配关键词
    for key, stocks in common_mapping.items():
        if key in keyword or keyword in key:
            for s in stocks:
                s.setdefault("concept", key)
            return stocks
    return []

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 concept_stock_fetcher.py <关键词>")
        print("示例: python3 concept_stock_fetcher.py 海上风电")
        sys.exit(1)

    keyword = sys.argv[1]
    print(f"搜索 '{keyword}' 相关个股...")
    stocks = search_concept_stocks(keyword)

    if stocks:
        print(f"找到{len(stocks)}只相关个股:")
        for stock in stocks:
            print(f"{stock['code']} {stock['name']} - 相关性: {stock['relevance']}星 - {stock['business']}")
    else:
        print(f"未找到与 '{keyword}' 相关的个股")
