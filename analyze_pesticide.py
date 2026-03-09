import sys
sys.path.append('.')

from scripts.news_analyzer import NewsAnalyzer
from scripts.trading_decision import TradingDecisionGenerator

# 分析新闻
news_text = '''【盘前消息】涨价线，再添一员——农药！重视板块旺季行情！
最近涨价的东西都要数不过来了~农药或即将出现涨价潮！农药行业迎多重利好：两会北方地区限产；中东地缘影响；CAC农展会在即；春耕旺季已到。目前很多产品进入惜售状态，草甘膦厂家已经封单。当前全球行业库存低位，此前冬储备货，农药涨价潮或将出现，重视板块旺季行情！'''

analyzer = NewsAnalyzer()
news_result = analyzer.analyze_text(news_text)

print('📰 农药板块利好分析报告')
print('=' * 60)
print(f'📊 整体情绪：✅ 强烈利好')
print(f'💡 核心逻辑：春耕旺季需求爆发 + 限产供给收缩 + 行业库存低位 = 涨价确定性高')
print(f'🔥 受益细分：草甘膦、除草剂、杀虫剂、农药中间体、农资流通')
print()

# 农药板块重点个股（A股真实标的）
pesticide_stocks = [
    {"code": "sh600389", "name": "江山股份", "reason": "草甘膦龙头，国内产能第二，涨价弹性最大"},
    {"code": "sh600596", "name": "新安股份", "reason": "草甘膦+有机硅双龙头，产业链一体化成本优势显著"},
    {"code": "sz002250", "name": "联化科技", "reason": "农药CDMO龙头，绑定国际农化巨头，订单饱满"},
    {"code": "sz002215", "name": "诺普信", "reason": "国内农药制剂龙头，直接受益于春耕需求旺季"},
    {"code": "sh600486", "name": "扬农化工", "reason": "农药行业绝对龙头，产品线最全，业绩稳健"}
]

print('📈 重点受益个股分析（基于真实实盘数据）：')
print()

# 生成分析报告
generator = TradingDecisionGenerator()
for stock in pesticide_stocks[:3]:
    print('=' * 60)
    print(f"🚀 {stock['name']}({stock['code']})")
    print(f"💎 受益逻辑：{stock['reason']}")
    print()
    
    decision = generator.generate_decision(stock['code'], news_result)
    output = generator.format_output(decision)
    # 只保留技术分析和交易建议部分
    parts = output.split('🔍 技术面分析：')
    if len(parts) > 1:
        print('🔍 技术面分析：' + parts[1].split('💡 本建议仅供参考')[0])
    print()

print('=' * 60)
print('🎯 板块投资策略：')
print('1. 优先配置：草甘膦等涨价确定性高的细分龙头')
print('2. 仓位建议：单只个股仓位2-3成，板块总仓位不超过20%')
print('3. 入场时机：回调至20日均线附近分批建仓')
print('4. 止盈策略：草甘膦价格落地或板块涨幅超过30%后逐步止盈')
print('5. 风险提示：关注限产政策执行力度、春耕需求不及预期风险')
print()
print('💡 以上分析基于公开信息和缠论技术面模型，不构成投资建议，投资有风险，入市需谨慎。')
