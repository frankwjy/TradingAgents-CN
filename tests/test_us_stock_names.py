"""Tests for us_stock_names module."""

import pytest
from tradingagents.config.us_stock_names import (
    _DEFAULT_CONFIG,
    get_all_tickers,
    get_company_name_en,
    get_company_name_zh,
    get_search_keywords,
    get_search_string,
    reload_config,
)


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


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_company_name_en(self):
        assert get_company_name_en("AAPL") == "Apple"
        assert get_company_name_en("UNKNOWN") == "US:UNKNOWN"

    def test_get_company_name_en_fallback(self):
        assert get_company_name_en("UNKNOWN", fallback="N/A") == "N/A"

    def test_get_company_name_zh(self):
        assert get_company_name_zh("AAPL") == "苹果公司"
        assert get_company_name_zh("UNKNOWN") == "美股UNKNOWN"

    def test_get_company_name_zh_fallback(self):
        assert get_company_name_zh("UNKNOWN", fallback="未知") == "未知"

    def test_get_search_keywords(self):
        keywords = get_search_keywords("AAPL")
        assert "apple" in keywords

    def test_get_search_keywords_unknown(self):
        assert get_search_keywords("UNKNOWN") == []

    def test_get_search_string(self):
        result = get_search_string("AAPL")
        assert "Apple" in result or "OR" in result

    def test_get_all_tickers(self):
        tickers = get_all_tickers()
        assert len(tickers) >= 100
        assert "AAPL" in tickers

    def test_reload_config_none(self):
        result = reload_config(None)
        assert result is _DEFAULT_CONFIG
