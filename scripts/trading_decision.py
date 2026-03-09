#!/usr/bin/env python3
"""
交易决策生成器
综合基本面+技术面给出操作建议
"""

import json
from typing import Dict, List, Optional
from .get_stock_data import get_kline_data, get_realtime_quote
from .chan_theory_analyzer import ChanTheoryAnalyzer

class TradingDecisionGenerator:
    def __init__(self):
        self.chan_analyzer = ChanTheoryAnalyzer()
        # 风险偏好等级
        self.risk_preference = {
            "conservative": {"max_position": 0.3, "stop_loss": 0.05, "take_profit": 0.1},
            "moderate": {"max_position": 0.5, "stop_loss": 0.08, "take_profit": 0.15},
            "aggressive": {"max_position": 0.8, "stop_loss": 0.12, "take_profit": 0.25}
        }
    
    def generate_decision(self, stock_code: str, news_analysis: Optional[Dict] = None, risk_level: str = "moderate") -> Dict:
        """
        生成交易决策建议
        
        Args:
            stock_code: 股票代码
            news_analysis: 新闻/政策分析结果（可选）
            risk_level: 风险偏好: conservative(保守), moderate(适中), aggressive(激进)
        
        Returns:
            {
                "stock_info": Dict,  # 股票基本信息
                "technical_analysis": Dict,  # 技术面分析
                "news_impact": Dict,  # 消息面影响
                "trading_suggestion": Dict,  # 交易建议
                "risk_warning": List[str]  # 风险提示
            }
        """
        # 获取股票基本信息
        quote = get_realtime_quote(stock_code)
        if not quote:
            return {"error": "无法获取股票行情数据"}
        
        # 获取K线数据
        df = get_kline_data(stock_code, 'day', 100)
        if df is None or len(df) < 20:
            return {"error": "无法获取足够的K线数据"}
        
        # 技术面分析
        tech_analysis = self.chan_analyzer.analyze_kline(df)
        if "error" in tech_analysis:
            return tech_analysis
        
        # 消息面影响评估
        news_impact = self._evaluate_news_impact(news_analysis, stock_code)
        
        # 综合评分
        total_score = self._calculate_total_score(tech_analysis, news_impact, quote)
        
        # 生成交易建议
        suggestion = self._generate_suggestion(total_score, tech_analysis, risk_level, quote['price'])
        
        # 风险提示
        risk_warnings = self._generate_risk_warnings(tech_analysis, news_impact, quote)
        
        return {
            "stock_info": {
                "code": stock_code,
                "name": quote['name'],
                "current_price": quote['price'],
                "change": quote['change'],
                "change_percent": quote['change_percent'],
                "volume": quote['volume'],
                "amount": quote['amount']
            },
            "technical_analysis": tech_analysis,
            "news_impact": news_impact,
            "total_score": total_score,
            "trading_suggestion": suggestion,
            "risk_warning": risk_warnings
        }
    
    def _evaluate_news_impact(self, news_analysis: Optional[Dict], stock_code: str) -> Dict:
        """评估消息面对个股的影响"""
        if not news_analysis:
            return {
                "impact": "neutral",
                "score": 0,
                "reason": "无相关消息面影响"
            }
        
        # 查找当前股票是否在相关个股中
        related_stocks = news_analysis.get("related_stocks", [])
        stock_match = next((s for s in related_stocks if s["code"].endswith(stock_code) or stock_code.endswith(s["code"])), None)
        
        if stock_match:
            impact = stock_match["impact"]
            score = stock_match["score"]
            reason = f"受相关消息影响，属于{stock_match['industry']}板块，消息面{impact}"
        else:
            # 判断行业相关性
            related_industries = news_analysis.get("related_industries", [])
            if related_industries:
                impact = news_analysis["sentiment"]
                score = news_analysis["sentiment_score"] * 2
                reason = f"所属板块受消息面{impact}影响"
            else:
                impact = "neutral"
                score = 0
                reason = "无直接消息面影响"
        
        return {
            "impact": impact,
            "score": min(max(score, -5), 5),  # 限制在-5到5之间
            "reason": reason
        }
    
    def _calculate_total_score(self, tech_analysis: Dict, news_impact: Dict, quote: Dict) -> int:
        """计算综合评分，满分10分，最低-10分"""
        score = 0
        
        # 技术面评分（占70%）
        # 走势评分
        trend = tech_analysis["trend"]
        if trend == "up":
            score += 4
        elif trend == "down":
            score -= 4
        
        # 背驰评分
        divergence = tech_analysis["divergence"]
        if divergence["has_divergence"]:
            if divergence["type"] == "bottom":
                score += 3
            else:
                score -= 3
        
        # 买卖点评分
        buy_points = len(tech_analysis["buy_points"])
        sell_points = len(tech_analysis["sell_points"])
        score += buy_points * 2
        score -= sell_points * 2
        
        # 支撑压力位评分
        current_price = quote["price"]
        support_levels = tech_analysis["support_levels"]
        resistance_levels = tech_analysis["resistance_levels"]
        
        # 距离最近支撑位的距离
        if support_levels:
            nearest_support = min(s for s in support_levels if s < current_price) if any(s < current_price for s in support_levels) else None
            if nearest_support:
                support_distance = (current_price - nearest_support) / current_price
                if support_distance < 0.03:  # 接近支撑位
                    score += 1
        
        # 距离最近压力位的距离
        if resistance_levels:
            nearest_resistance = min(r for r in resistance_levels if r > current_price) if any(r > current_price for r in resistance_levels) else None
            if nearest_resistance:
                resistance_distance = (nearest_resistance - current_price) / current_price
                if resistance_distance < 0.03:  # 接近压力位
                    score -= 1
        
        # 消息面评分（占30%）
        score += news_impact["score"] * 0.7
        
        # 限制在-10到10之间
        return max(min(round(score), 10), -10)
    
    def _generate_suggestion(self, total_score: int, tech_analysis: Dict, risk_level: str, current_price: float) -> Dict:
        """生成具体交易建议"""
        risk_config = self.risk_preference[risk_level]
        
        # 操作建议
        if total_score >= 7:
            action = "强烈买入"
            position = risk_config["max_position"]
        elif total_score >= 4:
            action = "买入"
            position = risk_config["max_position"] * 0.7
        elif total_score >= 1:
            action = "逢低买入"
            position = risk_config["max_position"] * 0.3
        elif total_score >= -2:
            action = "持有"
            position = 0
        elif total_score >= -5:
            action = "逢高减仓"
            position = 0
        elif total_score >= -8:
            action = "卖出"
            position = 0
        else:
            action = "强烈卖出"
            position = 0
        
        # 止损止盈位
        stop_loss = None
        take_profit = None
        
        if "buy" in action or action == "持有":
            # 支撑位作为止损
            support_levels = tech_analysis["support_levels"]
            if support_levels:
                stop_loss = min(s for s in support_levels if s < current_price) if any(s < current_price for s in support_levels) else current_price * (1 - risk_config["stop_loss"])
            else:
                stop_loss = current_price * (1 - risk_config["stop_loss"])
            
            # 压力位作为止盈
            resistance_levels = tech_analysis["resistance_levels"]
            if resistance_levels:
                take_profit = min(r for r in resistance_levels if r > current_price) if any(r > current_price for r in resistance_levels) else current_price * (1 + risk_config["take_profit"])
            else:
                take_profit = current_price * (1 + risk_config["take_profit"])
        
        return {
            "action": action,
            "position": f"{int(position * 100)}%" if position > 0 else "0",
            "stop_loss": round(stop_loss, 2) if stop_loss else None,
            "take_profit": round(take_profit, 2) if take_profit else None,
            "score": total_score
        }
    
    def _generate_risk_warnings(self, tech_analysis: Dict, news_impact: Dict, quote: Dict) -> List[str]:
        """生成风险提示"""
        warnings = []
        
        # 技术面风险
        divergence = tech_analysis["divergence"]
        if divergence["has_divergence"] and divergence["type"] == "top":
            warnings.append("⚠️ 技术面出现顶背驰，短期回调风险较大")
        
        if tech_analysis["trend"] == "down":
            warnings.append("📉 当前处于下降趋势，注意趋势风险")
        
        sell_points = tech_analysis["sell_points"]
        if sell_points:
            warnings.append(f"🔴 出现{len(sell_points)}个卖点信号，注意控制仓位")
        
        # 消息面风险
        if news_impact["impact"] == "negative":
            warnings.append(f"📰 消息面利空：{news_impact['reason']}")
        
        # 市场风险
        if abs(quote["change_percent"]) > 7:
            warnings.append(f"⚠️ 今日涨跌幅{quote['change_percent']:.2f}%，波动较大，注意风险")
        
        if not warnings:
            warnings.append("✅ 当前无明显风险信号")
        
        return warnings
    
    def format_output(self, decision: Dict) -> str:
        """格式化输出为易读文本"""
        if "error" in decision:
            return f"❌ 分析失败：{decision['error']}"
        
        stock = decision["stock_info"]
        suggestion = decision["trading_suggestion"]
        
        output = [
            f"📊 {stock['name']}({stock['code']}) 分析报告",
            f"================================",
            f"💹 当前价格：{stock['current_price']:.2f}元  {'📈' if stock['change'] >= 0 else '📉'} {stock['change']:+.2f}({stock['change_percent']:+.2f}%)",
            f"💰 成交额：{stock['amount']/100000000:.2f}亿元  成交量：{stock['volume']/10000:.0f}手",
            f"",
            f"🔍 技术面分析：",
            f"{decision['technical_analysis']['conclusion']}",
            f"",
            f"📰 消息面影响：",
            f"   {decision['news_impact']['reason']}",
            f"",
            f"⭐ 综合评分：{suggestion['score']}/10",
            f"",
            f"💡 交易建议：",
            f"   操作：{suggestion['action']}",
        ]
        
        if suggestion['position'] != "0":
            output.append(f"   仓位：{suggestion['position']}")
        
        if suggestion['stop_loss']:
            output.append(f"   止损位：{suggestion['stop_loss']:.2f}元")
        
        if suggestion['take_profit']:
            output.append(f"   止盈位：{suggestion['take_profit']:.2f}元")
        
        output.append("")
        output.append("⚠️ 风险提示：")
        for warning in decision["risk_warning"]:
            output.append(f"   {warning}")
        
        output.append("")
        output.append("💡 本建议仅供参考，不构成投资建议，投资有风险，入市需谨慎。")
        
        return "\n".join(output)

if __name__ == "__main__":
    # 测试
    generator = TradingDecisionGenerator()
    
    # 测试比亚迪
    print("测试：比亚迪(002594) 分析...")
    decision = generator.generate_decision("sz002594")
    print(generator.format_output(decision))
    
    # 测试腾讯控股
    print("\n" + "="*60 + "\n")
    print("测试：腾讯控股(00700) 分析...")
    decision = generator.generate_decision("hk00700")
    print(generator.format_output(decision))
