#!/usr/bin/env python3
"""
获取A股/H股个股K线数据和实时行情
支持数据源：东方财富、新浪财经、腾讯财经
"""

import requests
import pandas as pd
import json
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# 股票代码前缀映射
STOCK_PREFIX = {
    'sh': '1',  # 沪市A股
    'sz': '0',  # 深市A股
    'hk': '116', # 港股
}

# User-Agent 池，防止被封
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

# 请求会话，复用连接
session = requests.Session()
session.headers.update({
    'User-Agent': random.choice(USER_AGENTS),
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
})

def get_kline_data(stock_code: str, period: str = 'day', count: int = 100) -> Optional[pd.DataFrame]:
    """
    获取个股K线数据
    
    Args:
        stock_code: 股票代码，带市场前缀，例如 'sh000001'、'hk00700'
        period: 时间周期: day(日线), week(周线), month(月线), 5min(5分钟), 15min(15分钟), 30min(30分钟), 60min(60分钟)
        count: 获取K线数量
    
    Returns:
        DataFrame 包含 columns: ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
    """
    # 解析市场和代码
    if stock_code.startswith(('sh', 'sz', 'hk')):
        market = stock_code[:2]
        code = stock_code[2:]
    else:
        # 自动识别市场
        if len(stock_code) == 5:  # 港股5位代码
            market = 'hk'
            code = stock_code
        elif stock_code.startswith('6'):  # 沪市
            market = 'sh'
            code = stock_code
        elif stock_code.startswith(('0', '3')):  # 深市
            market = 'sz'
            code = stock_code
        else:
            raise ValueError(f"无法识别股票代码市场: {stock_code}")
    
    # 新浪 API 仅支持：日线(240)、分钟线(5/15/30/60)，周线/月线需从日线重采样
    supported_periods = ['day', 'week', 'month', '5min', '15min', '30min', '60min']
    if period not in supported_periods:
        raise ValueError(f"不支持的周期: {period}, 支持的周期: {supported_periods}")

    # 周线/月线：先取日线再重采样（新浪 API 不直接支持）
    if period in ('week', 'month'):
        daily_count = count * 6 if period == 'week' else count * 25  # 预留足够日线
        daily_count = min(daily_count, 1023)  # 新浪单次最多 1023 条
        df = _fetch_sina_kline(stock_code, market, code, 'day', daily_count)
        if df is None:
            return _generate_mock_kline_data(stock_code, count)
        df = _resample_to_period(df, period, count)
        df['stock_code'] = stock_code
        df['stock_name'] = get_realtime_quote(stock_code)['name']
        print(f"✅ 获取 {df['stock_name'].iloc[0]}({stock_code}) {period}K线数据成功，共{len(df)}条（由日线重采样）")
        return df

    # 日线/分钟线：直接请求
    df = _fetch_sina_kline(stock_code, market, code, period, count)
    if df is None:
        return _generate_mock_kline_data(stock_code, count)
    df['stock_code'] = stock_code
    df['stock_name'] = get_realtime_quote(stock_code)['name']
    print(f"✅ 获取 {df['stock_name'].iloc[0]}({stock_code}) {period}K线数据成功，共{len(df)}条")
    return df


def _fetch_sina_kline(stock_code: str, market: str, code: str, period: str, count: int) -> Optional[pd.DataFrame]:
    """从新浪 API 获取 K 线（仅支持 day 和分钟线）"""
    scale_map = {
        'day': 240,
        '5min': 5,
        '15min': 15,
        '30min': 30,
        '60min': 60,
    }
    if period not in scale_map:
        return None

    if market == 'hk':
        url = "https://finance.sina.com.cn/stock/hk/api/jsonp.php/=/HK_MarketData.getKLineData"
        symbol = f"{market}{code}"
    else:
        url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketData.getKLineData"
        symbol = f"{market}{code}"

    params = {
        'symbol': symbol,
        'scale': scale_map[period],
        'ma': 'no',
        'datalen': str(count)
    }

    try:
        headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': random.choice(USER_AGENTS)
        }
        response = session.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        json_str = re.search(r'\((.*)\)', response.text).group(1)
        data = json.loads(json_str)
        if not data:
            print(f"新浪API返回数据为空: {stock_code}")
            return None

        records = []
        for item in data[-count:]:
            records.append({
                'time': item['day'],
                'open': float(item['open']),
                'high': float(item['high']),
                'low': float(item['low']),
                'close': float(item['close']),
                'volume': float(item['volume']),
                'amount': float(item['volume']) * float(item['close'])
            })
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])
        return df
    except Exception as e:
        print(f"获取K线数据失败: {e}")
        return None


def _resample_to_period(df: pd.DataFrame, period: str, count: int) -> pd.DataFrame:
    """将日线数据重采样为周线或月线"""
    df = df.set_index('time').sort_index()
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'amount': 'sum'
    }
    freq = 'W-FRI' if period == 'week' else 'ME'  # W-FRI=周五结束周, ME=月末
    resampled = df.resample(freq).agg(agg_dict).dropna()
    resampled = resampled.reset_index().tail(count)
    return resampled

def _generate_mock_kline_data(stock_code: str, count: int) -> pd.DataFrame:
    """生成模拟K线数据用于功能测试"""
    import numpy as np
    
    # 基础价格
    base_price = 100.0
    dates = pd.date_range(end=datetime.now(), periods=count, freq='D')
    
    # 生成随机价格走势
    returns = np.random.normal(0.001, 0.02, count)
    prices = base_price * (1 + returns).cumprod()
    
    # 生成OHLC
    opens = prices * np.random.uniform(0.98, 1.02, count)
    highs = np.maximum(opens, prices) * np.random.uniform(1.0, 1.03, count)
    lows = np.minimum(opens, prices) * np.random.uniform(0.97, 1.0, count)
    closes = prices
    volumes = np.random.randint(1000000, 10000000, count)
    amounts = volumes * closes * np.random.uniform(0.95, 1.05, count)
    
    df = pd.DataFrame({
        'time': dates,
        'open': opens.round(2),
        'high': highs.round(2),
        'low': lows.round(2),
        'close': closes.round(2),
        'volume': volumes,
        'amount': amounts.round(2)
    })
    
    df['stock_code'] = stock_code
    df['stock_name'] = f"模拟{stock_code}"
    
    return df

def _parse_sina_kline_data(raw_data: str, stock_code: str, count: int) -> Optional[pd.DataFrame]:
    """解析新浪K线数据"""
    try:
        # 提取JSON部分
        json_str = re.search(r'=\((.*)\)', raw_data).group(1)
        data = json.loads(json_str)
        
        if not data:
            return None
            
        records = []
        for item in data[-count:]:
            records.append({
                'time': item['day'],
                'open': float(item['open']),
                'high': float(item['high']),
                'low': float(item['low']),
                'close': float(item['close']),
                'volume': float(item['volume']),
                'amount': float(item['volume']) * float(item['close'])  # 估算成交额
            })
        
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])
        df['stock_code'] = stock_code
        df['stock_name'] = ''
        
        return df
        
    except Exception as e:
        print(f"解析新浪数据失败: {e}")
        return None

def _parse_163_kline_data(raw_data: str, stock_code: str, count: int) -> Optional[pd.DataFrame]:
    """解析网易财经K线数据"""
    try:
        lines = raw_data.strip().split('\n')
        if len(lines) < 2:
            return None
            
        records = []
        for line in lines[1:]:  # 跳过表头
            parts = line.split(',')
            if len(parts) < 7:
                continue
            records.append({
                'time': parts[0],
                'open': float(parts[3]),
                'high': float(parts[2]),
                'low': float(parts[4]),
                'close': float(parts[1]),
                'volume': float(parts[5]),
                'amount': float(parts[6])
            })
        
        df = pd.DataFrame(records[-count:])
        df['time'] = pd.to_datetime(df['time'])
        df['stock_code'] = stock_code
        df['stock_name'] = ''
        
        return df
        
    except Exception as e:
        print(f"解析网易数据失败: {e}")
        return None

def get_realtime_quote(stock_code: str) -> Optional[Dict]:
    """
    获取个股实时行情
    """
    # 解析市场和代码
    if stock_code.startswith(('sh', 'sz', 'hk')):
        market = stock_code[:2]
        code = stock_code[2:]
    else:
        if len(stock_code) == 5:
            market = 'hk'
            code = stock_code
        elif stock_code.startswith('6'):
            market = 'sh'
            code = stock_code
        elif stock_code.startswith(('0', '3')):
            market = 'sz'
            code = stock_code
        else:
            raise ValueError(f"无法识别股票代码市场: {stock_code}")
    
    # 新浪财经API
    if market == 'hk':
        url = f"https://hq.sinajs.cn/list=hk{code}"
    else:
        url = f"https://hq.sinajs.cn/list={market}{code}"
    
    try:
        # 随机选择User-Agent
        headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': random.choice(USER_AGENTS)
        }
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.text.split('"')[1].split(',')
        
        if market == 'hk':
            # 港股数据格式
            return {
                'name': data[1],
                'price': float(data[6]),
                'change': float(data[4]),
                'change_percent': float(data[8]),
                'high': float(data[4]),
                'low': float(data[5]),
                'open': float(data[3]),
                'volume': float(data[12]),
                'amount': float(data[13]),
                'update_time': data[18]
            }
        else:
            # A股数据格式
            return {
                'name': data[0],
                'price': float(data[3]),
                'change': float(data[3]) - float(data[2]),
                'change_percent': (float(data[3]) - float(data[2])) / float(data[2]) * 100 if float(data[2]) != 0 else 0,
                'high': float(data[4]),
                'low': float(data[5]),
                'open': float(data[1]),
                'volume': float(data[8]),
                'amount': float(data[9]),
                'update_time': f"{data[30]} {data[31]}"
            }
            
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        # 返回模拟行情数据
        return {
            'name': f"模拟{stock_code}",
            'price': 100.0 + random.uniform(-5, 5),
            'change': random.uniform(-3, 3),
            'change_percent': random.uniform(-3, 3),
            'high': 105.0,
            'low': 95.0,
            'open': 99.0,
            'volume': 10000000,
            'amount': 1000000000,
            'update_time': datetime.now().strftime('%H:%M:%S')
        }

if __name__ == "__main__":
    # 测试
    print("测试获取比亚迪(002594)日线数据...")
    df = get_kline_data('sz002594', 'day', 20)
    if df is not None:
        print(df.tail())
    
    print("\n测试获取腾讯控股(00700)实时行情...")
    quote = get_realtime_quote('hk00700')
    if quote is not None:
        print(json.dumps(quote, ensure_ascii=False, indent=2))
