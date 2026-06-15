"""
Tests for the centralized US stock names configuration module.
"""

import json

import pytest

from tradingagents.config.us_stock_names import (
    _DEFAULT_CONFIG,
    get_all_tickers,
    get_company_name_en,
    get_company_name_zh,
    get_keywords_map,
    get_search_keywords,
    get_search_string,
    reload_config,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the config cache before each test."""
    reload_config()
    yield
    reload_config()


class TestDefaultConfig:
    """Test the default configuration."""

    def test_config_is_dict(self):
        assert isinstance(_DEFAULT_CONFIG, dict)

    def test_minimum_ticker_count(self):
        """Should have at least 100 tickers (NASDAQ 100 + others)."""
        assert len(_DEFAULT_CONFIG) >= 100

    def test_all_entries_have_required_keys(self):
        """Every entry must have en, zh, and keywords."""
        for ticker, entry in _DEFAULT_CONFIG.items():
            assert "en" in entry, f"{ticker} missing 'en'"
            assert "zh" in entry, f"{ticker} missing 'zh'"
            assert "keywords" in entry, f"{ticker} missing 'keywords'"
            assert isinstance(entry["en"], str), f"{ticker} 'en' is not a string"
            assert isinstance(entry["zh"], str), f"{ticker} 'zh' is not a string"
            assert isinstance(entry["keywords"], list), f"{ticker} 'keywords' is not a list"
            assert len(entry["keywords"]) > 0, f"{ticker} has empty keywords"

    def test_all_keys_are_uppercase(self):
        for ticker in _DEFAULT_CONFIG:
            assert ticker == ticker.upper(), f"{ticker} is not uppercase"


class TestNASDAQ100Components:
    """Test that all NASDAQ 100 components from the issue are present."""

    NASDAQ_100_TICKERS = [
        "AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "TSLA",
        "AVGO", "COST", "NFLX", "AMD", "ADBE", "PEP", "CSCO", "INTC",
        "CMCSA", "QCOM", "TXN", "AMGN", "HON", "INTU", "AMAT", "BKNG",
        "ISRG", "MU", "SBUX", "MDLZ", "GILD", "ADP", "LRCX", "REGN",
        "VRTX", "FISV", "KLAC", "SNPS", "CDNS", "NXPI", "MRVL", "ORLY",
        "CSX", "MAR", "MELI", "CTAS", "PAYX", "CHTR", "ABNB", "TEAM",
        "DXCM", "IDXX", "PCAR", "MNST", "AZN", "BIIB", "ALGN", "SIRI",
        "VRSK", "CCEP", "CPRT", "MCHP", "ASML", "TTD", "PDD", "XEL",
        "EXC", "AEP", "EA", "CTSH", "ZS", "FAST", "ANSS", "BKR",
        "DDOG", "ODFL", "GFS", "ROST", "LULU", "VRSN", "CSGP", "ON",
        "CRWD", "SMCI", "TROW", "FANG", "GEHC", "MPWR", "MNDY", "KDP",
        "ENPH", "DLTR", "PTON",
    ]

    def test_all_nasdaq_100_present(self):
        for ticker in self.NASDAQ_100_TICKERS:
            assert ticker in _DEFAULT_CONFIG, f"NASDAQ 100 ticker {ticker} is missing"

    @pytest.mark.parametrize("ticker", NASDAQ_100_TICKERS)
    def test_ticker_has_valid_entry(self, ticker):
        entry = _DEFAULT_CONFIG[ticker]
        assert entry["en"], f"{ticker} has empty en"
        assert entry["zh"], f"{ticker} has empty zh"
        assert len(entry["keywords"]) > 0, f"{ticker} has empty keywords"


class TestGetCompanyNameEn:
    def test_known_ticker(self):
        assert get_company_name_en("AAPL") == "Apple"
        assert get_company_name_en("TSLA") == "Tesla"
        assert get_company_name_en("NVDA") == "NVIDIA"

    def test_case_insensitive(self):
        assert get_company_name_en("aapl") == "Apple"
        assert get_company_name_en("Tsla") == "Tesla"

    def test_unknown_ticker_default_fallback(self):
        assert get_company_name_en("XYZABC") == "US:XYZABC"

    def test_unknown_ticker_custom_fallback(self):
        assert get_company_name_en("XYZABC", fallback="N/A") == "N/A"


class TestGetCompanyNameZh:
    def test_known_ticker(self):
        assert get_company_name_zh("AAPL") == "苹果公司"
        assert get_company_name_zh("TSLA") == "特斯拉"
        assert get_company_name_zh("NVDA") == "英伟达"

    def test_case_insensitive(self):
        assert get_company_name_zh("aapl") == "苹果公司"

    def test_unknown_ticker_default_fallback(self):
        assert get_company_name_zh("XYZABC") == "美股XYZABC"

    def test_unknown_ticker_custom_fallback(self):
        assert get_company_name_zh("XYZABC", fallback="未知") == "未知"


class TestGetSearchKeywords:
    def test_known_ticker(self):
        keywords = get_search_keywords("AAPL")
        assert "apple" in keywords
        assert "iphone" in keywords

    def test_unknown_ticker(self):
        assert get_search_keywords("XYZABC") == []


class TestGetSearchString:
    def test_multi_keyword_ticker(self):
        result = get_search_string("META")
        assert "Meta" in result or "Facebook" in result

    def test_unknown_ticker(self):
        assert get_search_string("XYZABC") == "XYZABC"


class TestGetKeywordsMap:
    def test_returns_dict_with_lowercase_key(self):
        result = get_keywords_map("AAPL")
        assert "aapl" in result
        assert "apple" in result["aapl"]

    def test_unknown_ticker(self):
        assert get_keywords_map("XYZABC") == {}


class TestGetAllTickers:
    def test_returns_list(self):
        tickers = get_all_tickers()
        assert isinstance(tickers, list)
        assert "AAPL" in tickers
        assert len(tickers) >= 100


class TestReloadConfig:
    def test_reload_from_custom_path(self, tmp_path):
        config_file = tmp_path / "custom_stocks.json"
        config_file.write_text(
            json.dumps({"TEST": {"en": "TestCo", "zh": "测试公司", "keywords": ["test"]}}),
            encoding="utf-8",
        )

        config = reload_config(str(config_file))
        assert get_company_name_en("TEST", fallback="") == "TestCo"
        assert get_company_name_zh("TEST", fallback="") == "测试公司"
