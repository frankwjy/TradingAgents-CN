# 测试指南

## 测试目录结构

```
tests/
├── config/           # 配置相关测试
├── dataflows/        # 数据流测试
├── integration/      # 集成测试
├── middleware/       # 中间件测试
├── services/         # 服务层测试
├── system/           # 系统测试
├── tradingagents/    # 核心代理测试
├── unit/             # 单元测试
│   ├── dataflows/    # 数据流单元测试
│   └── tools/        # 工具单元测试
└── debug_archive/    # 归档的调试测试（不参与CI）
```

## 测试命名规范

1. **测试文件命名**: `test_<module_name>.py`
2. **测试函数命名**: `test_<function_name>_<scenario>`
3. **测试类命名**: `Test<ClassName>`

## 测试编写规范

### 1. 测试独立性
- 每个测试应该独立运行，不依赖其他测试的结果
- 使用 `monkeypatch` 或 `unittest.mock` 来隔离外部依赖

### 2. 测试数据
- 使用工厂模式或 fixtures 创建测试数据
- 避免在测试中硬编码敏感信息（如API密钥）

### 3. 断言
- 使用明确的断言，避免过于宽泛的断言
- 每个测试应该有明确的断言消息

### 4. 异步测试
- 使用 `pytest-asyncio` 进行异步测试
- 异步测试函数应该标记 `@pytest.mark.asyncio`

## 测试运行

### 运行所有测试
```bash
python -m pytest tests/ -v
```

### 运行特定目录的测试
```bash
python -m pytest tests/config -v
python -m pytest tests/services -v
python -m pytest tests/unit -v
```

### 运行带标记的测试
```bash
# 运行集成测试（默认跳过）
python -m pytest tests/ -m integration -v

# 跳过特定测试
python -m pytest tests/ -k "not test_server_config" -v
```

## 测试覆盖率

### 生成覆盖率报告
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

### 覆盖率目标
- 单元测试覆盖率: ≥ 80%
- 集成测试覆盖率: ≥ 60%

## Mock 和 Fixture 指南

### 1. MongoDB Mock
```python
class _FakeColl:
    def __init__(self):
        self.last_ops = None

    async def create_index(self, *args, **kwargs):
        return "ok"

    async def bulk_write(self, ops, ordered=False):
        self.last_ops = ops
        return _FakeResult(len(ops))

    async def update_one(self, *args, **kwargs):
        return _FakeResult(0)

    def find(self, *args, **kwargs):
        return _FakeCursor()
```

### 2. 数据源 Mock
```python
class _FakeManager:
    def get_realtime_quotes_with_fallback(self):
        return {
            "000001": {"close": 10.2, "pct_chg": 0.2, "amount": 1.1e8},
            "600000": {"close": 9.7, "pct_chg": -0.4, "amount": 7.1e7},
        }, "fake"

    def find_latest_trade_date_with_fallback(self):
        return "20250102"
```

### 3. 异步测试 Mock
```python
class _FakeCursor:
    def __init__(self, data=None):
        self._data = data or []

    async def to_list(self, length=None):
        return self._data
```

## 常见问题解决

### 1. MongoDB 连接错误
确保测试环境中的 MongoDB 配置正确，或者使用 Mock 来隔离数据库依赖。

### 2. 模块导入错误
确保 `conftest.py` 中正确配置了项目根目录：
```python
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
```

### 3. 异步测试超时
对于异步测试，确保使用正确的事件循环配置：
```python
@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

## 测试质量检查清单

- [ ] 测试是否独立运行？
- [ ] 测试是否有明确的断言？
- [ ] 测试是否使用了适当的 Mock？
- [ ] 测试是否覆盖了正常路径和异常路径？
- [ ] 测试是否有清晰的命名？
- [ ] 测试是否有适当的注释（如果需要）？

## 持续集成

测试在以下情况下自动运行：
1. 代码提交到 main 分支
2. Pull Request 创建或更新
3. 定时任务（每日构建）

## 测试报告

测试报告生成在以下位置：
- 覆盖率报告: `htmlcov/index.html`
- 测试结果: `reports/test-results.xml`
