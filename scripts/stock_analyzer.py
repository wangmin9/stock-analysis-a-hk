#!/usr/bin/env python3
"""
通用股票技术面分析工具
支持A股/H股，提供完整的技术分析报告

用法：
    python3 stock_analyzer.py <股票代码> [周期] [K线数量]

示例：
    python3 stock_analyzer.py sh603606              # 分析东方电缆日线
    python3 stock_analyzer.py hk00700 week 50       # 分析腾讯控股周线
    python3 stock_analyzer.py sz002594 day 100      # 分析比亚迪日线100根
"""

import sys
import os

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from get_stock_data import get_kline_data, get_realtime_quote
from chan_theory_analyzer import ChanTheoryAnalyzer
import pandas as pd


def analyze_stock(stock_code: str, period: str = 'day', count: int = 100):
    """
    分析个股技术面

    Args:
        stock_code: 股票代码，例如 sh603606, hk00700, sz002594
        period: 时间周期，day/week/month/5min/15min/30min/60min
        count: K线数量
    """

    # 1. 获取实时行情
    print("=" * 70)
    print(f"📊 {stock_code.upper()} 技术面分析报告")
    print("=" * 70)

    quote = get_realtime_quote(stock_code)
    print(f"\n【实时行情】")
    print(f"股票名称：{quote['name']}")
    print(f"最新价格：{quote['price']:.2f} 元")
    print(f"涨跌幅：{quote['change_percent']:+.2f}%")
    print(f"今日最高：{quote['high']:.2f} 元")
    print(f"今日最低：{quote['low']:.2f} 元")
    print(f"今日开盘：{quote['open']:.2f} 元")

    if quote['volume'] > 0:
        print(f"成交量：{quote['volume']/10000:.2f} 万手")
    if quote['amount'] > 0:
        print(f"成交额：{quote['amount']/100000000:.2f} 亿元")

    # 2. 获取K线数据
    print(f"\n{'='*70}")
    df = get_kline_data(stock_code, period, count)
    if df is None:
        print("❌ 无法获取K线数据，分析终止")
        return None

    # 3. 缠论分析
    print(f"\n【缠论技术分析】")
    analyzer = ChanTheoryAnalyzer()
    result = analyzer.analyze_kline(df)

    # 打印分析结果
    print(f"\n{result['conclusion']}")

    # 4. 均线分析
    print(f"\n【均线分析】")
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()

    latest = df.iloc[-1]
    current_price = latest['close']

    print(f"当前价格：{current_price:.2f} 元")
    print(f"MA5：{latest['ma5']:.2f} 元 ({(current_price/latest['ma5']-1)*100:+.2f}%)")
    print(f"MA10：{latest['ma10']:.2f} 元 ({(current_price/latest['ma10']-1)*100:+.2f}%)")
    print(f"MA20：{latest['ma20']:.2f} 元 ({(current_price/latest['ma20']-1)*100:+.2f}%)")
    print(f"MA60：{latest['ma60']:.2f} 元 ({(current_price/latest['ma60']-1)*100:+.2f}%)")

    # 均线多头排列判断
    if latest['ma5'] > latest['ma10'] > latest['ma20'] > latest['ma60']:
        print("✅ 均线多头排列，趋势向好")
        ma_trend = "bullish"
    elif latest['ma5'] < latest['ma10'] < latest['ma20'] < latest['ma60']:
        print("❌ 均线空头排列，趋势向下")
        ma_trend = "bearish"
    else:
        print("⚠️  均线交织，震荡格局")
        ma_trend = "neutral"

    # 5. 成交量分析
    print(f"\n【成交量分析】")
    recent_volume = df['volume'].tail(5).mean()
    avg_volume = df['volume'].tail(20).mean()
    volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

    print(f"近5日均量：{recent_volume/10000:.2f} 万手")
    print(f"近20日均量：{avg_volume/10000:.2f} 万手")
    print(f"量比：{volume_ratio:.2f}")

    if volume_ratio > 1.5:
        print("✅ 成交量放大，资金活跃")
        volume_status = "active"
    elif volume_ratio < 0.7:
        print("⚠️  成交量萎缩，观望情绪浓")
        volume_status = "weak"
    else:
        print("➡️  成交量正常")
        volume_status = "normal"

    # 6. 涨跌幅统计
    print(f"\n【近期涨跌幅】")
    df['change_pct'] = df['close'].pct_change() * 100
    change_5d = df['change_pct'].tail(5).sum()
    change_10d = df['change_pct'].tail(10).sum()
    change_20d = df['change_pct'].tail(20).sum()

    print(f"近5日涨跌幅：{change_5d:+.2f}%")
    print(f"近10日涨跌幅：{change_10d:+.2f}%")
    print(f"近20日涨跌幅：{change_20d:+.2f}%")

    # 7. 综合操作建议
    print(f"\n{'='*70}")
    print(f"【综合操作建议】")
    print(f"{'='*70}")

    # 基于缠论买卖点和均线判断
    has_buy_signal = len(result['buy_points']) > 0
    has_sell_signal = len(result['sell_points']) > 0
    is_bullish = ma_trend == "bullish" or (latest['ma5'] > latest['ma10'] and current_price > latest['ma20'])
    is_bearish = ma_trend == "bearish" or (latest['ma5'] < latest['ma10'] and current_price < latest['ma20'])

    # 综合评分
    score = 0
    if has_buy_signal:
        score += 3
    if is_bullish:
        score += 2
    if volume_status == "active":
        score += 1
    if change_10d > 5:
        score += 1
    if has_sell_signal:
        score -= 3
    if is_bearish:
        score -= 2
    if result['divergence'].get('type') == 'top':
        score -= 2

    # 操作建议
    if score >= 4 or (has_buy_signal and is_bullish):
        print("✅ 操作建议：【买入】")
        print(f"   理由：缠论买点信号 + 均线多头排列 + 趋势向好")
        print(f"   建议仓位：2-3成")
        if result['support_levels']:
            print(f"   止损位：{result['support_levels'][0]:.2f} 元")
        if result['resistance_levels']:
            print(f"   第一目标位：{result['resistance_levels'][0]:.2f} 元")
            if len(result['resistance_levels']) > 1:
                print(f"   第二目标位：{result['resistance_levels'][1]:.2f} 元")

    elif score <= -3 or has_sell_signal or (is_bearish and result['divergence'].get('type') == 'top'):
        print("❌ 操作建议：【卖出/观望】")
        print(f"   理由：卖点信号或均线空头或顶背驰")
        print(f"   建议：持有者减仓，空仓者观望")
        if result['resistance_levels']:
            print(f"   反弹压力位：{result['resistance_levels'][0]:.2f} 元")

    elif is_bullish and change_10d > 0:
        print("➡️  操作建议：【持有/逢低加仓】")
        print(f"   理由：均线多头排列，趋势向好")
        if result['support_levels']:
            print(f"   加仓参考位：{result['support_levels'][0]:.2f} 元附近")
        if result['resistance_levels']:
            print(f"   目标位：{result['resistance_levels'][0]:.2f} 元")

    else:
        print("⚠️  操作建议：【观望】")
        print(f"   理由：走势不明朗，等待更好机会")
        if result['support_levels']:
            print(f"   关注支撑位：{result['support_levels'][0]:.2f} 元")
        if result['resistance_levels']:
            print(f"   关注压力位：{result['resistance_levels'][0]:.2f} 元")

    # 8. 风险提示
    print(f"\n⚠️  【风险提示】")
    print(f"1. 股市有风险，投资需谨慎")
    print(f"2. 本分析仅供参考，不构成投资建议")
    print(f"3. 严格控制仓位，设置止损位")
    print(f"4. 关注市场环境变化和个股基本面")

    # 特别风险提示
    if result['divergence'].get('has_divergence'):
        if result['divergence']['type'] == 'top':
            print(f"5. ⚠️  当前出现顶背驰信号，警惕回调风险！")
        elif result['divergence']['type'] == 'bottom':
            print(f"5. ✅ 当前出现底背驰信号，关注反弹机会")

    print(f"\n{'='*70}\n")

    return {
        'quote': quote,
        'kline': df,
        'chan_analysis': result,
        'ma_trend': ma_trend,
        'volume_status': volume_status,
        'recommendation_score': score
    }


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python3 stock_analyzer.py <股票代码> [周期] [K线数量]")
        print()
        print("示例:")
        print("  python3 stock_analyzer.py sh603606              # 分析东方电缆日线")
        print("  python3 stock_analyzer.py hk00700 week 50       # 分析腾讯控股周线")
        print("  python3 stock_analyzer.py sz002594 day 100      # 分析比亚迪日线")
        print()
        print("支持的股票代码格式:")
        print("  A股：sh600000（沪市）、sz000001（深市）")
        print("  H股：hk00700")
        print()
        print("支持的周期:")
        print("  day（日线）、week（周线）、month（月线）")
        print("  5min、15min、30min、60min（分钟线）")
        sys.exit(1)

    stock_code = sys.argv[1]
    period = sys.argv[2] if len(sys.argv) > 2 else 'day'
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    analyze_stock(stock_code, period, count)


if __name__ == "__main__":
    main()
