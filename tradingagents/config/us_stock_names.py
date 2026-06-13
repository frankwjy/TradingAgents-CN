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
