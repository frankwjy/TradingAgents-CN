import os
import sys
from unittest.mock import MagicMock

import pytest

# 将项目根目录加入 sys.path，确保 `import tradingagents` 可用
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# 标准 Mock 类（基于 MagicMock，支持属性访问和 dict 式访问）
# ---------------------------------------------------------------------------
# 这些类通过组合（而非继承）使用 MagicMock，避免 MagicMock 子类的元类
# 与自定义 __getattr__/__getitem__ 之间的冲突。


class MockCollection:
    """MongoDB 集合 Mock，预配置常用方法的默认返回值。

    所有方法调用委托给内部 MagicMock，支持 assert_called 等断言。
    find_one() -> None（未找到）
    find()     -> 可迭代空游标（支持链式 .sort().limit()）
    insert_one / update_one / delete_one -> 模拟 WriteResult
    count_documents -> 0
    """

    def __init__(self):
        self._mock = MagicMock(name="MockCollection")
        # find_one: 默认返回 None
        self._mock.find_one.return_value = None
        # find: 返回可迭代游标，支持 .sort()/.limit() 链式调用
        cursor = MagicMock(name="MockCursor")
        cursor.__iter__ = MagicMock(return_value=iter([]))
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        self._mock.find.return_value = cursor
        # 写操作
        self._mock.insert_one.return_value = MagicMock(inserted_id="mock_id")
        self._mock.insert_many.return_value = MagicMock(inserted_ids=["mock_id"])
        self._mock.update_one.return_value = MagicMock(modified_count=1)
        self._mock.update_many.return_value = MagicMock(modified_count=1)
        self._mock.delete_one.return_value = MagicMock(deleted_count=1)
        self._mock.delete_many.return_value = MagicMock(deleted_count=1)
        # 计数
        self._mock.count_documents.return_value = 0
        # 索引
        self._mock.create_index.return_value = "index_name"

    def __getattr__(self, name):
        return getattr(self._mock, name)

    def __repr__(self):
        return f"MockCollection({self._mock._mock_name})"


class MockDatabase:
    """MongoDB 数据库 Mock。

    同时支持属性访问（db.collection_name）和 dict 式访问（db["collection_name"]），
    两种方式返回同一个 MockCollection 实例。
    """

    def __init__(self):
        self._collections: dict[str, MockCollection] = {}

    def _get_collection(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._get_collection(name)

    def __getitem__(self, name: str):
        return self._get_collection(name)

    def __repr__(self):
        return f"MockDatabase(collections={list(self._collections.keys())})"


class MockMongoClient:
    """MongoDB 客户端 Mock。

    client["db_name"] 返回 MockDatabase 实例；重复访问同一数据库名称返回同一实例。
    同时支持 client.get_database("name") 形式。
    """

    def __init__(self):
        self._databases: dict[str, MockDatabase] = {}

    def __getitem__(self, name: str) -> MockDatabase:
        if name not in self._databases:
            self._databases[name] = MockDatabase()
        return self._databases[name]

    def get_database(self, name: str) -> MockDatabase:
        return self[name]

    def __repr__(self):
        return f"MockMongoClient(databases={list(self._databases.keys())})"


class MockAPIClient:
    """通用 HTTP/API 客户端 Mock。

    预配置 get/post/put/delete/patch 方法及常见响应属性。
    content 和 text 设置为空字符串（支持 len()）。
    """

    def __init__(self):
        self._mock = MagicMock(name="MockAPIClient")
        response = MagicMock(name="MockResponse")
        response.status_code = 200
        response.json.return_value = {}
        response.text = ""
        response.content = b""
        response.ok = True
        response.headers = {}
        self._mock.get.return_value = response
        self._mock.post.return_value = response
        self._mock.put.return_value = response
        self._mock.delete.return_value = response
        self._mock.patch.return_value = response

    def __getattr__(self, name):
        return getattr(self._mock, name)

    def __repr__(self):
        return "MockAPIClient()"


# ---------------------------------------------------------------------------
# Pytest Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mongo_collection():
    """提供一个预配置的 MockCollection 实例。"""
    return MockCollection()


@pytest.fixture
def mock_mongo_db():
    """提供一个预配置的 MockDatabase 实例（支持属性和 dict 式集合访问）。"""
    return MockDatabase()


@pytest.fixture
def mock_mongo_client():
    """提供一个预配置的 MockMongoClient 实例。"""
    return MockMongoClient()


@pytest.fixture
def mock_api_client():
    """提供一个预配置的 MockAPIClient 实例。"""
    return MockAPIClient()
