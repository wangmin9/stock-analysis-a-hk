#!/usr/bin/env python3
"""
动态概念板块个股获取工具
按需实时获取东方财富概念板块成分股，本地缓存，无需提前配置
"""

import requests
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import quote

# User-Agent 池
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.1',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

# 缓存配置
CACHE_DIR = Path(__file__).parent.parent / "cache" / "concepts"
CACHE_EXPIRE_DAYS = 7  # 缓存有效期7天

# 创建缓存目录
CACHE_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    'User-Agent': USER_AGENTS[0],
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
})

def get_concept_stocks(keyword: str, use_cache: bool = True) -> List[Dict]:
    """
    获取概念板块对应的个股列表
    
    Args:
        keyword: 概念关键词，例如 "特高压", "氦气", "染料"
        use_cache: 是否使用本地缓存
    
    Returns:
        个股列表，每个元素包含:
        {
            "code": "sh600000",
            "name": "浦发银行",
            "concept": "概念名称",
            "relevance": 5,  # 相关性评分 1-5
            "business": "业务描述"
        }
    """
    # 1. 检查缓存
    cache_file = CACHE_DIR / f"{keyword}.json"
    if use_cache and cache_file.exists():
        cache_time = cache_file.stat().st_mtime
        if time.time() - cache_time < CACHE_EXPIRE_DAYS * 86400:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass  # 缓存损坏，重新获取
    
    # 2. 实时搜索概念板块
    stocks = _search_eastmoney_concept(keyword)
    
    # 3. 保存缓存
    if stocks:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
    
    return stocks

def _search_eastmoney_concept(keyword: str) -> List[Dict]:
    """从东方财富搜索概念板块个股"""
    try:
        # 1. 搜索概念板块ID
        search_url = f"https://searchapi.eastmoney.com/api/suggest/get?input={quote(keyword)}&type=14&token=D43BF722C8E39585C3EB54EE3A6D62E5"
        headers = {
            'Referer': 'https://www.eastmoney.com/',
            'User-Agent': USER_AGENTS[0]
        }
        response = session.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"搜索返回数据: {json.dumps(data, ensure_ascii=False)[:500]}...")  # 调试输出
        
        # 适配东方财富返回结构
        if data.get('QuotationCodeTable') and data['QuotationCodeTable'].get('Data'):
            # 新返回结构
            concept = data['QuotationCodeTable']['Data'][0]
            plate_code = concept['Code'].replace('BK', '')
            plate_name = concept['Name']
        elif data.get('Result') and data['Result'].get('ConceptPlate'):
            # 旧返回结构
            concept = data['Result']['ConceptPlate'][0]
            plate_code = concept['Code']
            plate_name = concept['Name']
        else:
            return []
        
        # 2. 获取板块成分股
        stock_url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f3&fs=b:BK{plate_code}&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13"
        response = session.get(stock_url, headers=headers, timeout=10)
        response.raise_for_status()
        stock_data = response.json()
        
        if not stock_data.get('data') or not stock_data['data'].get('diff'):
            return []
            
        stocks = []
        for i, item in enumerate(stock_data['data']['diff']):
            # 格式化股票代码
            code = item['f12']
            if code.startswith('6'):
                full_code = f"sh{code}"
            elif code.startswith(('0', '3')):
                full_code = f"sz{code}"
            else:
                continue  # 跳过其他市场
                
            # 相关性评分：前20名给5分，21-50给4分，51+给3分
            relevance = 5 if i < 20 else 4 if i < 50 else 3
            
            stocks.append({
                "code": full_code,
                "name": item['f14'],
                "concept": plate_name,
                "relevance": relevance,
                "business": f"{plate_name}概念板块成分股，{item['f14']}"
            })
            
        return stocks[:50]  # 最多返回50只
        
    except Exception as e:
        print(f"东方财富概念搜索失败: {e}")
        return _get_fallback_concept_stocks(keyword)

def _get_fallback_concept_stocks(keyword: str) -> List[Dict]:
    """备用数据源：内置常用概念映射"""
    fallback_mapping = {
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
        "氦气": [
            {"code": "sh600256", "name": "广汇能源", "relevance": 5, "business": "国内最大氦气生产商，年产200万立方米"},
            {"code": "sz002978", "name": "安宁股份", "relevance": 4, "business": "钒钛磁铁矿提氦技术领先"},
            {"code": "sh688239", "name": "杭氧股份", "relevance": 4, "business": "空分设备龙头，具备氦气提纯能力"},
            {"code": "sh603798", "name": "康普顿", "relevance": 3, "business": "参股氦气提纯项目"},
            {"code": "sz000552", "name": "靖远煤电", "relevance": 3, "business": "煤层气提氦项目已投产"}
        ],
        "染料": [
            {"code": "sh600352", "name": "浙江龙盛", "relevance": 5, "business": "全球染料龙头，分散染料产能30万吨/年"},
            {"code": "sz002440", "name": "闰土股份", "relevance": 4, "business": "国内第二大分散染料生产商，产能11万吨/年"},
            {"code": "sz002738", "name": "中农立华", "relevance": 4, "business": "农药及染料中间体供应商"},
            {"code": "sh603181", "name": "皇马科技", "relevance": 3, "business": "特种表面活性剂和染料中间体生产商"}
        ],
        "燃气轮机": [
            {"code": "sh600875", "name": "东方电气", "relevance": 5, "business": "国内燃气轮机龙头，具备重型燃机自主研发能力"},
            {"code": "sh601727", "name": "上海电气", "relevance": 5, "business": "国内第二大燃气轮机制造商"},
            {"code": "sh603308", "name": "应流股份", "relevance": 4, "business": "燃气轮机叶片核心供应商"},
            {"code": "sz002353", "name": "杰瑞股份", "relevance": 4, "business": "燃气轮机装备及服务提供商"},
            {"code": "sh605060", "name": "联德股份", "relevance": 3, "business": "燃气轮机核心精密铸件供应商"}
        ]
    }
    
    # 模糊匹配
    for key, stocks in fallback_mapping.items():
        if key in keyword or keyword in key:
            return stocks
    
    return []

def clear_expired_cache() -> None:
    """清理过期缓存"""
    now = time.time()
    for cache_file in CACHE_DIR.glob("*.json"):
        if now - cache_file.stat().st_mtime > CACHE_EXPIRE_DAYS * 86400:
            cache_file.unlink()

if __name__ == "__main__":
    # 测试
    print("测试搜索特高压概念个股...")
    stocks = get_concept_stocks("特高压")
    if stocks:
        print(f"找到{len(stocks)}只相关个股:")
        for stock in stocks[:10]:
            print(f"{stock['code']} {stock['name']} - 相关性: {stock['relevance']}星 - {stock['business']}")
    
    print("\n测试搜索电力电网概念个股...")
    stocks = get_concept_stocks("电力电网")
    if stocks:
        print(f"找到{len(stocks)}只相关个股:")
        for stock in stocks[:10]:
            print(f"{stock['code']} {stock['name']} - 相关性: {stock['relevance']}星 - {stock['business']}")
    
    # 清理过期缓存
    clear_expired_cache()
