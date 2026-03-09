from scripts.trading_decision import TradingDecisionGenerator

# 分析新闻
news_text = '''【盘前消息】涨价线，再添一员——农药！重视板块旺季行情！
最近涨价的东西都要数不过来了~农药或即将出现涨价潮！农药行业迎多重利好：两会北方地区限产；中东地缘影响；CAC农展会在即；春耕旺季已到。目前很多产品进入惜售状态，草甘膦厂家已经封单。当前全球行业库存低位，此前冬储备货，农药涨价潮或将出现，重视板块旺季行情！'''

analyzer = NewsAnalyzer()
news_result = analyzer.analyze_text(news_text)

print('📰 新闻分析结果：')
print(f'整体情绪：✅ 利好')
print(f'核心逻辑：春耕旺季+限产+库存低位，农药板块迎来涨价行情')
print(f'受益细分：草甘膦、除草剂、杀虫剂、农药中间体')
print()

# 农药板块重点个股
pesticide_stocks = [
    {"code": "sh600389", "name": "江山股份", "reason": "草甘膦龙头，产能国内领先"},
    {"code": "sh600596", "name": "新安股份", "reason": "草甘膦+有机硅双龙头，业绩弹性大"},
    {"code": "sz002250", "name": "联化科技", "reason": "农药CDMO龙头，受益于行业涨价"},
    {"code": "sz002215", "name": "诺普信", "reason": "国内农药制剂龙头，直接受益于春耕需求"},
    {"code": "sh600486", "name": "扬农化工", "reason": "国内农药行业龙头，产业链一体化"}
]

print('📈 重点受益个股分析：')
print()

# 生成分析报告
generator = TradingDecisionGenerator()
for stock in pesticide_stocks[:3]:
    print('='*60)
    print(f"🚀 {stock['name']}({stock['code']})")
    print(f"📝 受益逻辑：{stock['reason']}")
    print()
    
    decision = generator.generate_decision(stock['code'], news_result)
    print(generator.format_output(decision).split('💡 交易建议：')[1])
    print()
