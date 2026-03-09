#!/usr/bin/env python3
"""
缠论自动分析工具
- 中枢识别
- 背驰判断
- 买卖点识别
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

class ChanTheoryAnalyzer:
    def __init__(self):
        pass
    
    def analyze_kline(self, df: pd.DataFrame) -> Dict:
        """
        分析K线数据，返回缠论分析结果
        
        Args:
            df: K线数据，包含 columns: ['time', 'open', 'high', 'low', 'close', 'volume']
        
        Returns:
            {
                "trend": "up|down|consolidation",  # 当前走势
                "central_levels": List[Dict],  # 中枢列表
                "divergence": Dict,  # 背驰情况
                "buy_points": List[Dict],  # 买点
                "sell_points": List[Dict],  # 卖点
                "support_levels": List[float],  # 支撑位
                "resistance_levels": List[float],  # 压力位
                "conclusion": str  # 分析结论
            }
        """
        if len(df) < 20:
            return {"error": "K线数据不足，至少需要20根K线"}
        
        # 1. 分型识别
        fractals = self._identify_fractals(df)
        
        # 2. 笔识别
        strokes = self._identify_strokes(df, fractals)
        
        # 3. 线段识别
        segments = self._identify_segments(strokes)
        
        # 4. 中枢识别
        centrals = self._identify_centrals(segments)
        
        # 5. 背驰判断
        divergence = self._judge_divergence(df, segments, centrals)
        
        # 6. 买卖点识别
        buy_points, sell_points = self._identify_trade_points(df, segments, centrals, divergence)
        
        # 7. 支撑压力位计算
        support_levels, resistance_levels = self._calculate_support_resistance(df, centrals)
        
        # 8. 综合判断走势
        trend = self._judge_trend(segments, centrals)
        
        return {
            "trend": trend,
            "central_levels": centrals,
            "divergence": divergence,
            "buy_points": buy_points,
            "sell_points": sell_points,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "conclusion": self._generate_conclusion(trend, divergence, buy_points, sell_points, support_levels, resistance_levels)
        }
    
    def _identify_fractals(self, df: pd.DataFrame) -> List[Dict]:
        """识别顶分型和底分型"""
        fractals = []
        n = len(df)
        
        for i in range(2, n - 2):
            # 顶分型：中间K线高点是最高
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i-2] and
                df['high'].iloc[i] > df['high'].iloc[i+1] and 
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                fractals.append({
                    "index": i,
                    "time": df['time'].iloc[i],
                    "price": df['high'].iloc[i],
                    "type": "top"
                })
            
            # 底分型：中间K线低点是最低
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i-2] and
                df['low'].iloc[i] < df['low'].iloc[i+1] and 
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                fractals.append({
                    "index": i,
                    "time": df['time'].iloc[i],
                    "price": df['low'].iloc[i],
                    "type": "bottom"
                })
        
        return fractals
    
    def _identify_strokes(self, df: pd.DataFrame, fractals: List[Dict]) -> List[Dict]:
        """识别笔：相邻顶底分型构成笔"""
        strokes = []
        if len(fractals) < 2:
            return strokes
        
        i = 0
        while i < len(fractals) - 1:
            current = fractals[i]
            next_f = fractals[i+1]
            
            # 顶底分型交替
            if current["type"] != next_f["type"]:
                # 笔的幅度要求：至少3%
                price_diff = abs(next_f["price"] - current["price"]) / current["price"]
                if price_diff > 0.03:
                    stroke_type = "up" if next_f["type"] == "top" else "down"
                    strokes.append({
                        "start_index": current["index"],
                        "end_index": next_f["index"],
                        "start_time": current["time"],
                        "end_time": next_f["time"],
                        "start_price": current["price"],
                        "end_price": next_f["price"],
                        "type": stroke_type,
                        "amplitude": price_diff
                    })
                    i += 1
                    continue
            i += 1
        
        return strokes
    
    def _identify_segments(self, strokes: List[Dict]) -> List[Dict]:
        """识别线段：至少3笔构成线段"""
        segments = []
        if len(strokes) < 3:
            return segments
        
        i = 0
        while i < len(strokes) - 2:
            # 连续3笔方向相同构成线段
            if (strokes[i]["type"] == strokes[i+1]["type"] and 
                strokes[i]["type"] == strokes[i+2]["type"]):
                
                segment_type = strokes[i]["type"]
                start_price = strokes[i]["start_price"]
                end_price = strokes[i+2]["end_price"]
                
                segments.append({
                    "start_index": strokes[i]["start_index"],
                    "end_index": strokes[i+2]["end_index"],
                    "start_time": strokes[i]["start_time"],
                    "end_time": strokes[i+2]["end_time"],
                    "start_price": start_price,
                    "end_price": end_price,
                    "type": segment_type,
                    "amplitude": abs(end_price - start_price) / start_price
                })
                i += 3
            else:
                i += 1
        
        return segments
    
    def _identify_centrals(self, segments: List[Dict]) -> List[Dict]:
        """识别中枢：连续3个线段的重叠部分构成中枢"""
        centrals = []
        if len(segments) < 3:
            return centrals
        
        i = 0
        while i < len(segments) - 2:
            seg1 = segments[i]
            seg2 = segments[i+1]
            seg3 = segments[i+2]
            
            # 计算重叠区间
            high1, low1 = max(seg1["start_price"], seg1["end_price"]), min(seg1["start_price"], seg1["end_price"])
            high2, low2 = max(seg2["start_price"], seg2["end_price"]), min(seg2["start_price"], seg2["end_price"])
            high3, low3 = max(seg3["start_price"], seg3["end_price"]), min(seg3["start_price"], seg3["end_price"])
            
            central_high = min(high1, high2, high3)
            central_low = max(low1, low2, low3)
            
            if central_high > central_low:  # 有重叠
                centrals.append({
                    "start_index": seg1["start_index"],
                    "end_index": seg3["end_index"],
                    "start_time": seg1["start_time"],
                    "end_time": seg3["end_time"],
                    "high": central_high,
                    "low": central_low,
                    "center": (central_high + central_low) / 2,
                    "level": "day"  # 暂时默认日线级别
                })
                i += 3
            else:
                i += 1
        
        return centrals
    
    def _judge_divergence(self, df: pd.DataFrame, segments: List[Dict], centrals: List[Dict]) -> Dict:
        """判断背驰：比较两段同方向走势的力度（MACD/成交量）"""
        if len(segments) < 2 or len(centrals) < 1:
            return {"has_divergence": False}
        
        # 取最近两个同方向线段
        recent_segments = [s for s in segments if s["end_index"] > centrals[-1]["end_index"]]
        if len(recent_segments) < 2:
            return {"has_divergence": False}
        
        seg1, seg2 = recent_segments[-2], recent_segments[-1]
        if seg1["type"] != seg2["type"]:
            return {"has_divergence": False}
        
        # 计算两段走势的力度（用幅度和成交量加权）
        power1 = seg1["amplitude"] * df["volume"].iloc[seg1["start_index"]:seg1["end_index"]].mean()
        power2 = seg2["amplitude"] * df["volume"].iloc[seg2["start_index"]:seg2["end_index"]].mean()
        
        divergence_type = None
        has_divergence = False
        
        if seg1["type"] == "up" and power2 < power1 * 0.7:  # 顶背驰
            has_divergence = True
            divergence_type = "top"
        elif seg1["type"] == "down" and power2 < power1 * 0.7:  # 底背驰
            has_divergence = True
            divergence_type = "bottom"
        
        return {
            "has_divergence": has_divergence,
            "type": divergence_type,
            "power_ratio": power2 / power1 if power1 != 0 else 0
        }
    
    def _identify_trade_points(self, df: pd.DataFrame, segments: List[Dict], centrals: List[Dict], divergence: Dict) -> Tuple[List[Dict], List[Dict]]:
        """识别买卖点"""
        buy_points = []
        sell_points = []
        current_price = df["close"].iloc[-1]
        
        # 第一类买卖点：背驰点
        if divergence["has_divergence"]:
            if divergence["type"] == "bottom":
                buy_points.append({
                    "type": "1",
                    "price": df["low"].iloc[-1],
                    "description": "第一类买点（底背驰）"
                })
            elif divergence["type"] == "top":
                sell_points.append({
                    "type": "1",
                    "price": df["high"].iloc[-1],
                    "description": "第一类卖点（顶背驰）"
                })
        
        # 第二类买卖点：回踩不创新低/新高
        if len(centrals) > 0:
            last_central = centrals[-1]
            if current_price > last_central["high"] * 1.01:
                # 突破中枢后回踩
                buy_points.append({
                    "type": "2",
                    "price": last_central["high"],
                    "description": "第二类买点（突破中枢回踩）"
                })
            elif current_price < last_central["low"] * 0.99:
                # 跌破中枢后反抽
                sell_points.append({
                    "type": "2",
                    "price": last_central["low"],
                    "description": "第二类卖点（跌破中枢反抽）"
                })
        
        # 第三类买卖点：不回到中枢
        if len(centrals) > 0:
            last_central = centrals[-1]
            if current_price > last_central["high"] and all(s["low"] > last_central["high"] for s in segments[-3:]):
                buy_points.append({
                    "type": "3",
                    "price": current_price,
                    "description": "第三类买点（强势不回中枢）"
                })
            elif current_price < last_central["low"] and all(s["high"] < last_central["low"] for s in segments[-3:]):
                sell_points.append({
                    "type": "3",
                    "price": current_price,
                    "description": "第三类卖点（弱势不回中枢）"
                })
        
        return buy_points, sell_points
    
    def _calculate_support_resistance(self, df: pd.DataFrame, centrals: List[Dict]) -> Tuple[List[float], List[float]]:
        """计算支撑位和压力位"""
        support_levels = []
        resistance_levels = []
        
        # 近期低点作为支撑
        recent_lows = df["low"].tail(20).nsmallest(3).values
        support_levels.extend(recent_lows)
        
        # 近期高点作为压力
        recent_highs = df["high"].tail(20).nlargest(3).values
        resistance_levels.extend(recent_highs)
        
        # 中枢上下沿作为支撑压力
        for central in centrals[-3:]:
            support_levels.append(central["low"])
            resistance_levels.append(central["high"])
        
        # 去重并排序
        support_levels = sorted(list(set(support_levels)), reverse=True)[:3]  # 最近的3个支撑
        resistance_levels = sorted(list(set(resistance_levels)))[:3]  # 最近的3个压力
        
        return support_levels, resistance_levels
    
    def _judge_trend(self, segments: List[Dict], centrals: List[Dict]) -> str:
        """判断当前走势"""
        if len(segments) < 2:
            return "consolidation"
        
        recent_type = segments[-1]["type"]
        recent_amplitude = segments[-1]["amplitude"]
        
        if len(centrals) > 0:
            last_central = centrals[-1]
            current_end_price = segments[-1]["end_price"]
            
            if current_end_price > last_central["high"] * 1.03:
                return "up"
            elif current_end_price < last_central["low"] * 0.97:
                return "down"
            else:
                return "consolidation"
        else:
            if recent_amplitude > 0.1:  # 幅度超过10%算趋势
                return recent_type
            else:
                return "consolidation"
    
    def _generate_conclusion(self, trend: str, divergence: Dict, buy_points: List[Dict], sell_points: List[Dict], support_levels: List[float], resistance_levels: List[float]) -> str:
        """生成分析结论"""
        conclusion = []
        
        trend_desc = {"up": "上升趋势", "down": "下降趋势", "consolidation": "震荡盘整"}
        conclusion.append(f"当前走势：{trend_desc.get(trend, '震荡')}")
        
        if divergence["has_divergence"]:
            if divergence["type"] == "top":
                conclusion.append(f"⚠️ 出现顶背驰，走势力度减弱，警惕回调风险")
            else:
                conclusion.append(f"✅ 出现底背驰，下跌动能衰竭，有望反弹")
        
        if buy_points:
            conclusion.append("📈 买点信号：")
            for point in buy_points:
                conclusion.append(f"  - {point['description']}，参考价位：{point['price']:.2f}")
        
        if sell_points:
            conclusion.append("📉 卖点信号：")
            for point in sell_points:
                conclusion.append(f"  - {point['description']}，参考价位：{point['price']:.2f}")
        
        if support_levels:
            conclusion.append(f"🛡️  支撑位：{', '.join([f'{s:.2f}' for s in support_levels])}")
        
        if resistance_levels:
            conclusion.append(f"🔴 压力位：{', '.join([f'{r:.2f}' for r in resistance_levels])}")
        
        return "\n".join(conclusion)

if __name__ == "__main__":
    # 测试
    from .get_stock_data import get_kline_data
    
    print("测试缠论分析：比亚迪(002594)")
    df = get_kline_data('sz002594', 'day', 100)
    if df is not None:
        analyzer = ChanTheoryAnalyzer()
        result = analyzer.analyze_kline(df)
        print(result["conclusion"])
