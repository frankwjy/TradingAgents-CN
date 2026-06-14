"""
Data sources subpackage.
Expose adapters and manager for backward-compatible imports.
"""

from .akshare_adapter import AKShareAdapter
from .baostock_adapter import BaoStockAdapter
from .base import DataSourceAdapter
from .manager import DataSourceManager
from .tushare_adapter import TushareAdapter
