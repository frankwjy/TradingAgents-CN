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
