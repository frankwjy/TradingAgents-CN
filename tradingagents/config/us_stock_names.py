"""
美股公司名称配置模块
提供统一的股票代码-公司名称映射，支持中英文名称和关键词检索。
默认数据内嵌于模块中，可通过 reload_config(path) 从外部 JSON 文件覆盖。
"""

import json
from typing import Dict, List, Optional

_DEFAULT_CONFIG: Dict = {
    "AAPL": {"en": "Apple", "zh": "苹果公司", "keywords": ["apple", "iphone", "ipad", "mac"]},
    "MSFT": {"en": "Microsoft", "zh": "微软", "keywords": ["microsoft", "windows", "azure"]},
    "GOOGL": {"en": "Google", "zh": "谷歌", "keywords": ["google", "alphabet", "search"]},
    "AMZN": {"en": "Amazon", "zh": "亚马逊", "keywords": ["amazon", "aws", "prime"]},
    "TSLA": {"en": "Tesla", "zh": "特斯拉", "keywords": ["tesla", "elon musk", "electric vehicle"]},
    "NVDA": {"en": "NVIDIA", "zh": "英伟达", "keywords": ["nvidia", "gpu", "ai chip"]},
    "META": {"en": "Meta", "zh": "Meta", "keywords": ["meta", "facebook", "instagram", "whatsapp"]},
    "NFLX": {"en": "Netflix", "zh": "奈飞", "keywords": ["netflix", "streaming"]},
    "TSM": {"en": "TSMC", "zh": "台积电", "keywords": ["tsmc", "taiwan semiconductor"]},
    "JPM": {"en": "JPMorgan Chase", "zh": "摩根大通", "keywords": ["jpmorgan", "jp morgan", "chase"]},
    "JNJ": {"en": "Johnson & Johnson", "zh": "强生", "keywords": ["johnson & johnson", "jnj"]},
    "V": {"en": "Visa", "zh": "Visa", "keywords": ["visa"]},
    "WMT": {"en": "Walmart", "zh": "沃尔玛", "keywords": ["walmart"]},
    "AMD": {"en": "AMD", "zh": "AMD", "keywords": ["amd", "ryzen", "radeon"]},
    "INTC": {"en": "Intel", "zh": "英特尔", "keywords": ["intel"]},
    "QCOM": {"en": "Qualcomm", "zh": "高通", "keywords": ["qualcomm", "snapdragon"]},
    "BABA": {"en": "Alibaba", "zh": "阿里巴巴", "keywords": ["alibaba", "aliexpress"]},
    "ADBE": {"en": "Adobe", "zh": "Adobe", "keywords": ["adobe", "photoshop"]},
    "CRM": {"en": "Salesforce", "zh": "Salesforce", "keywords": ["salesforce"]},
    "PYPL": {"en": "PayPal", "zh": "PayPal", "keywords": ["paypal"]},
    "PLTR": {"en": "Palantir", "zh": "Palantir", "keywords": ["palantir"]},
    "MU": {"en": "Micron", "zh": "美光", "keywords": ["micron"]},
    "SQ": {"en": "Block", "zh": "Block", "keywords": ["block", "square", "cash app"]},
    "ZM": {"en": "Zoom", "zh": "Zoom", "keywords": ["zoom"]},
    "CSCO": {"en": "Cisco", "zh": "思科", "keywords": ["cisco"]},
    "SHOP": {"en": "Shopify", "zh": "Shopify", "keywords": ["shopify"]},
    "ORCL": {"en": "Oracle", "zh": "甲骨文", "keywords": ["oracle"]},
    "X": {"en": "X", "zh": "X", "keywords": ["twitter", "x corp"]},
    "SPOT": {"en": "Spotify", "zh": "Spotify", "keywords": ["spotify"]},
    "AVGO": {"en": "Broadcom", "zh": "博通", "keywords": ["broadcom"]},
    "ASML": {"en": "ASML", "zh": "ASML", "keywords": ["asml"]},
    "TWLO": {"en": "Twilio", "zh": "Twilio", "keywords": ["twilio"]},
    "SNAP": {"en": "Snap Inc.", "zh": "Snap", "keywords": ["snapchat", "snap"]},
    "TEAM": {"en": "Atlassian", "zh": "Atlassian", "keywords": ["atlassian", "jira", "confluence"]},
    "SQSP": {"en": "Squarespace", "zh": "Squarespace", "keywords": ["squarespace"]},
    "UBER": {"en": "Uber", "zh": "Uber", "keywords": ["uber"]},
    "ROKU": {"en": "Roku", "zh": "Roku", "keywords": ["roku"]},
    "PINS": {"en": "Pinterest", "zh": "Pinterest", "keywords": ["pinterest"]},
    # Major Index ETFs
    "SPY": {"en": "SPDR S&P 500 ETF Trust", "zh": "标普500 ETF", "keywords": ["spy", "spdr", "s&p 500", "sp500"]},
    "QQQ": {"en": "Invesco QQQ Trust", "zh": "纳斯达克100 ETF", "keywords": ["qqq", "nasdaq 100", "invesco"]},
    "DIA": {"en": "SPDR Dow Jones Industrial Average ETF", "zh": "道琼斯 ETF", "keywords": ["dia", "dow jones", "djia"]},
    "IWM": {"en": "iShares Russell 2000 ETF", "zh": "罗素2000 ETF", "keywords": ["iwm", "russell 2000", "ishares"]},
    "VTI": {"en": "Vanguard Total Stock Market ETF", "zh": "全股市 ETF", "keywords": ["vti", "vanguard", "total stock market"]},
    "VO": {"en": "Vanguard Mid-Cap ETF", "zh": "中盘股 ETF", "keywords": ["vo", "vanguard", "mid-cap"]},
    "VB": {"en": "Vanguard Small-Cap ETF", "zh": "小盘股 ETF", "keywords": ["vb", "vanguard", "small-cap"]},
    "VGT": {"en": "Vanguard Information Technology ETF", "zh": "信息技术 ETF", "keywords": ["vgt", "vanguard", "information technology"]},
    "XLF": {"en": "Financial Select Sector SPDR Fund", "zh": "金融板块 ETF", "keywords": ["xlf", "financial", "spdr"]},
    "XLE": {"en": "Energy Select Sector SPDR Fund", "zh": "能源板块 ETF", "keywords": ["xle", "energy", "spdr"]},
    "XLK": {"en": "Technology Select Sector SPDR Fund", "zh": "科技板块 ETF", "keywords": ["xlk", "technology", "spdr"]},
    "XLV": {"en": "Health Care Select Sector SPDR Fund", "zh": "医疗保健 ETF", "keywords": ["xlv", "health care", "spdr"]},
    "ARKK": {"en": "ARK Innovation ETF", "zh": "ARK创新 ETF", "keywords": ["arkk", "ark", "innovation", "cathie wood"]},
    "SOXX": {"en": "iShares Semiconductor ETF", "zh": "半导体 ETF", "keywords": ["soxx", "semiconductor", "ishares"]},
    "IBB": {"en": "iShares Biotechnology ETF", "zh": "生物科技 ETF", "keywords": ["ibb", "biotechnology", "ishares"]},
    "GLD": {"en": "SPDR Gold Shares", "zh": "黄金 ETF", "keywords": ["gld", "gold", "spdr"]},
    "SLV": {"en": "iShares Silver Trust", "zh": "白银 ETF", "keywords": ["slv", "silver", "ishares"]},
    "USO": {"en": "United States Oil Fund", "zh": "石油 ETF", "keywords": ["uso", "oil", "crude"]},
    "TLT": {"en": "iShares 20+ Year Treasury Bond ETF", "zh": "长期国债 ETF", "keywords": ["tlt", "treasury", "bond", "20 year"]},
    "QQQM": {"en": "Invesco NASDAQ 100 ETF", "zh": "纳斯达克100 ETF (低成本)", "keywords": ["qqqm", "nasdaq 100", "invesco", "low cost"]},
    # NASDAQ 100 Components
    "GOOG": {"en": "Alphabet Inc. (Class C)", "zh": "谷歌(无投票权)", "keywords": ["google", "alphabet", "goog"]},
    "COST": {"en": "Costco", "zh": "好市多", "keywords": ["costco", "wholesale"]},
    "PEP": {"en": "PepsiCo", "zh": "百事公司", "keywords": ["pepsi", "pepsico", "frito-lay"]},
    "CMCSA": {"en": "Comcast", "zh": "康卡斯特", "keywords": ["comcast", "nbcuniversal", "xfinity"]},
    "TXN": {"en": "Texas Instruments", "zh": "德州仪器", "keywords": ["texas instruments", "ti"]},
    "AMGN": {"en": "Amgen", "zh": "安进", "keywords": ["amgen", "biotech"]},
    "HON": {"en": "Honeywell", "zh": "霍尼韦尔", "keywords": ["honeywell"]},
    "INTU": {"en": "Intuit", "zh": "财捷", "keywords": ["intuit", "turbotax", "quickbooks"]},
    "AMAT": {"en": "Applied Materials", "zh": "应用材料", "keywords": ["applied materials"]},
    "BKNG": {"en": "Booking Holdings", "zh": "缤客", "keywords": ["booking", "priceline", "kayak"]},
    "ISRG": {"en": "Intuitive Surgical", "zh": "直觉外科", "keywords": ["intuitive surgical", "da vinci"]},
    "SBUX": {"en": "Starbucks", "zh": "星巴克", "keywords": ["starbucks", "coffee"]},
    "MDLZ": {"en": "Mondelez International", "zh": "亿滋国际", "keywords": ["mondelez", "oreo", "cadbury"]},
    "GILD": {"en": "Gilead Sciences", "zh": "吉利德科学", "keywords": ["gilead", "hiv", "hepatitis"]},
    "ADP": {"en": "Automatic Data Processing", "zh": "自动数据处理", "keywords": ["adp", "payroll"]},
    "LRCX": {"en": "Lam Research", "zh": "泛林集团", "keywords": ["lam research", "semiconductor equipment"]},
    "REGN": {"en": "Regeneron", "zh": "再生元", "keywords": ["regeneron", "biotech"]},
    "VRTX": {"en": "Vertex Pharmaceuticals", "zh": "福泰制药", "keywords": ["vertex", "cystic fibrosis"]},
    "FISV": {"en": "Fiserv", "zh": "费哲金融服务", "keywords": ["fiserv", "fintech"]},
    "KLAC": {"en": "KLA Corporation", "zh": "科磊", "keywords": ["kla", "semiconductor inspection"]},
    "SNPS": {"en": "Synopsys", "zh": "新思科技", "keywords": ["synopsys", "eda"]},
    "CDNS": {"en": "Cadence Design Systems", "zh": "楷登电子", "keywords": ["cadence", "eda"]},
    "NXPI": {"en": "NXP Semiconductors", "zh": "恩智浦半导体", "keywords": ["nxp", "semiconductor"]},
    "MRVL": {"en": "Marvell Technology", "zh": "迈威尔科技", "keywords": ["marvell"]},
    "ORLY": {"en": "O'Reilly Automotive", "zh": "奥莱利汽车", "keywords": ["oreilly", "auto parts"]},
    "CSX": {"en": "CSX Corporation", "zh": "CSX运输", "keywords": ["csx", "railroad"]},
    "MAR": {"en": "Marriott International", "zh": "万豪国际", "keywords": ["marriott", "hotel"]},
    "MELI": {"en": "MercadoLibre", "zh": "自由市场", "keywords": ["mercadolibre", "ecommerce", "latam"]},
    "CTAS": {"en": "Cintas Corporation", "zh": "辛塔斯", "keywords": ["cintas", "uniforms"]},
    "PAYX": {"en": "Paychex", "zh": "沛齐", "keywords": ["paychex", "payroll"]},
    "CHTR": {"en": "Charter Communications", "zh": "特许通讯", "keywords": ["charter", "spectrum"]},
    "ABNB": {"en": "Airbnb", "zh": "爱彼迎", "keywords": ["airbnb", "vacation rental"]},
    "DXCM": {"en": "DexCom", "zh": "德康医疗", "keywords": ["dexcom", "cgm", "glucose monitor"]},
    "IDXX": {"en": "IDEXX Laboratories", "zh": "爱德士", "keywords": ["idexx", "veterinary"]},
    "PCAR": {"en": "PACCAR", "zh": "帕卡", "keywords": ["paccar", "kenworth", "peterbilt"]},
    "MNST": {"en": "Monster Beverage", "zh": "怪兽饮料", "keywords": ["monster", "energy drink"]},
    "AZN": {"en": "AstraZeneca", "zh": "阿斯利康", "keywords": ["astrazeneca", "pharma"]},
    "BIIB": {"en": "Biogen", "zh": "百健", "keywords": ["biogen", "alzheimer"]},
    "ALGN": {"en": "Align Technology", "zh": "隐适美", "keywords": ["align", "invisalign"]},
    "SIRI": {"en": "Sirius XM", "zh": "天狼星XM", "keywords": ["sirius", "satellite radio"]},
    "VRSK": {"en": "Verisk Analytics", "zh": "韦睿司", "keywords": ["verisk", "analytics"]},
    "CCEP": {"en": "Coca-Cola Europacific Partners", "zh": "可口可乐欧洲太平洋", "keywords": ["coca-cola", "coke", "bottler"]},
    "CPRT": {"en": "Copart", "zh": "科帕特", "keywords": ["copart", "auto auction"]},
    "MCHP": {"en": "Microchip Technology", "zh": "微芯科技", "keywords": ["microchip", "mcu"]},
    "TTD": {"en": "The Trade Desk", "zh": "广告达人", "keywords": ["trade desk", "adtech"]},
    "PDD": {"en": "PDD Holdings", "zh": "拼多多", "keywords": ["pinduoduo", "pdd", "temu"]},
    "XEL": {"en": "Xcel Energy", "zh": "Xcel能源", "keywords": ["xcel", "utility"]},
    "EXC": {"en": "Exelon", "zh": "爱克斯龙", "keywords": ["exelon", "utility"]},
    "AEP": {"en": "American Electric Power", "zh": "美国电力", "keywords": ["aep", "electric utility"]},
    "EA": {"en": "Electronic Arts", "zh": "艺电", "keywords": ["ea", "electronic arts", "fifa", "madden"]},
    "CTSH": {"en": "Cognizant", "zh": "高知特", "keywords": ["cognizant", "it services"]},
    "ZS": {"en": "Zscaler", "zh": "Zscaler", "keywords": ["zscaler", "cybersecurity", "zero trust"]},
    "FAST": {"en": "Fastenal", "zh": "快扣", "keywords": ["fastenal", "industrial supply"]},
    "ANSS": {"en": "ANSYS", "zh": "ANSYS", "keywords": ["ansys", "simulation"]},
    "BKR": {"en": "Baker Hughes", "zh": "贝克休斯", "keywords": ["baker hughes", "oilfield"]},
    "DDOG": {"en": "Datadog", "zh": "Datadog", "keywords": ["datadog", "monitoring", "observability"]},
    "ODFL": {"en": "Old Dominion Freight Line", "zh": "老自治领货运", "keywords": ["old dominion", "trucking"]},
    "GFS": {"en": "GlobalFoundries", "zh": "格芯", "keywords": ["globalfoundries", "semiconductor foundry"]},
    "ROST": {"en": "Ross Stores", "zh": "罗斯百货", "keywords": ["ross", "discount retail"]},
    "LULU": {"en": "Lululemon", "zh": "露露乐蒙", "keywords": ["lululemon", "athleisure"]},
    "VRSN": {"en": "VeriSign", "zh": "威瑞信", "keywords": ["verisign", "dns", "domain"]},
    "CSGP": {"en": "CoStar Group", "zh": "科斯塔集团", "keywords": ["costar", "real estate data"]},
    "ON": {"en": "ON Semiconductor", "zh": "安森美半导体", "keywords": ["on semiconductor", "onsemi"]},
    "CRWD": {"en": "CrowdStrike", "zh": "CrowdStrike", "keywords": ["crowdstrike", "cybersecurity", "endpoint"]},
    "SMCI": {"en": "Super Micro Computer", "zh": "超微电脑", "keywords": ["supermicro", "server"]},
    "TROW": {"en": "T. Rowe Price", "zh": "普信集团", "keywords": ["t rowe price", "asset management"]},
    "FANG": {"en": "Diamondback Energy", "zh": "响尾蛇能源", "keywords": ["diamondback", "oil", "permian"]},
    "GEHC": {"en": "GE HealthCare", "zh": "GE医疗", "keywords": ["ge healthcare", "medical imaging"]},
    "MPWR": {"en": "Monolithic Power Systems", "zh": "芯源系统", "keywords": ["monolithic power", "mps"]},
    "MNDY": {"en": "monday.com", "zh": "monday.com", "keywords": ["monday", "project management"]},
    "KDP": {"en": "Keurig Dr Pepper", "zh": "胡椒博士", "keywords": ["keurig", "dr pepper", "coffee"]},
    "ENPH": {"en": "Enphase Energy", "zh": "Enphase能源", "keywords": ["enphase", "solar", "microinverter"]},
    "DLTR": {"en": "Dollar Tree", "zh": "美元树", "keywords": ["dollar tree", "discount store"]},
    "PTON": {"en": "Peloton", "zh": "Peloton", "keywords": ["peloton", "fitness", "bike"]},
}

_config: Optional[Dict] = None


def _load_config() -> Dict:
    global _config
    if _config is not None:
        return _config
    return _DEFAULT_CONFIG


def reload_config(config_path: Optional[str] = None) -> Dict:
    """从外部 JSON 文件加载配置以覆盖默认值；传 None 则恢复默认。"""
    global _config
    if config_path is None:
        _config = None
        return _DEFAULT_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        _config = json.load(f)
    return _config


def get_company_name_en(ticker: str, fallback: Optional[str] = None) -> str:
    """获取美股公司英文名称。"""
    config = _load_config()
    entry = config.get(ticker.upper())
    if entry:
        return entry["en"]
    return fallback if fallback is not None else f"US:{ticker}"


def get_company_name_zh(ticker: str, fallback: Optional[str] = None) -> str:
    """获取美股公司中文名称。"""
    config = _load_config()
    entry = config.get(ticker.upper())
    if entry:
        return entry["zh"]
    return fallback if fallback is not None else f"美股{ticker}"


def get_search_keywords(ticker: str) -> List[str]:
    """获取股票代码对应的搜索关键词列表（用于新闻相关性匹配）。"""
    config = _load_config()
    entry = config.get(ticker.upper()) or config.get(ticker.lower())
    if entry:
        return entry.get("keywords", [])
    return []


def get_search_string(ticker: str) -> str:
    """获取用于新闻搜索的 OR 分隔字符串。例如 "Apple" 或 "Meta OR Facebook"。"""
    config = _load_config()
    entry = config.get(ticker.upper())
    if entry:
        keywords = entry.get("keywords", [])
        if keywords:
            return " OR ".join(k.capitalize() for k in keywords)
        return entry["en"]
    return ticker


def get_all_tickers() -> List[str]:
    """获取所有已配置的股票代码列表。"""
    return list(_load_config().keys())


def get_keywords_map(ticker: str) -> Dict[str, List[str]]:
    """获取小写 ticker -> 关键词列表的映射。"""
    config = _load_config()
    entry = config.get(ticker.upper())
    if entry:
        return {ticker.lower(): entry.get("keywords", [])}
    return {}
