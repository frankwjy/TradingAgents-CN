"""
统一时间估算算法测试
验证 MemoryStateManager 和 RedisProgressTracker 使用相同算法
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.memory_state_manager import calculate_estimated_duration_static, MemoryStateManager
from app.services.progress.tracker import RedisProgressTracker


def test_static_function():
    """测试静态估算函数"""
    print("=" * 70)
    print("测试静态估算函数 (calculate_estimated_duration_static)")
    print("=" * 70)

    # 场景1: 标准 + 3分析师 + dashscope
    result = calculate_estimated_duration_static("标准", ["market", "fundamentals", "news"], "dashscope")
    expected = 240 * 2.0 * 1.0  # 480s
    assert abs(result - expected) < 1, f"场景1失败: {result} != {expected}"
    print(f"  标准+3分析师+dashscope: {result:.0f}s (预期 {expected:.0f}s) ✓")

    # 场景2: 快速 + 1分析师 + deepseek
    result = calculate_estimated_duration_static("快速", ["market"], "deepseek")
    expected = 150 * 1.0 * 0.8  # 120s
    assert abs(result - expected) < 1, f"场景2失败: {result} != {expected}"
    print(f"  快速+1分析师+deepseek: {result:.0f}s (预期 {expected:.0f}s) ✓")

    # 场景3: 全面 + 4分析师 + google
    result = calculate_estimated_duration_static("全面", ["market", "fundamentals", "news", "social"], "google")
    expected = 480 * 2.4 * 1.2  # 1382.4s
    assert abs(result - expected) < 1, f"场景3失败: {result} != {expected}"
    print(f"  全面+4分析师+google: {result:.0f}s (预期 {expected:.0f}s) ✓")

    # 场景4: 空分析师列表
    result = calculate_estimated_duration_static("标准", [], "dashscope")
    expected = 240 * 1.0 * 1.0  # 240s (analyst_count defaults to 1)
    assert abs(result - expected) < 1, f"场景4失败: {result} != {expected}"
    print(f"  标准+空分析师+dashscope: {result:.0f}s (预期 {expected:.0f}s) ✓")

    # 场景5: 5分析师 (超过4个的非线性缩放)
    result = calculate_estimated_duration_static("标准", ["a", "b", "c", "d", "e"], "dashscope")
    expected = 240 * (2.4 + 0.3) * 1.0  # 648s
    assert abs(result - expected) < 1, f"场景5失败: {result} != {expected}"
    print(f"  标准+5分析师+dashscope: {result:.0f}s (预期 {expected:.0f}s) ✓")

    print()


def test_unified_algorithm():
    """验证 MemoryStateManager 和 RedisProgressTracker 使用相同算法"""
    print("=" * 70)
    print("测试算法一致性: MemoryStateManager vs RedisProgressTracker")
    print("=" * 70)

    test_cases = [
        ("标准", ["market", "fundamentals", "news"], "dashscope"),
        ("快速", ["market"], "deepseek"),
        ("深度", ["market", "fundamentals"], "qwen"),
        ("全面", ["market", "fundamentals", "news", "social"], "google"),
    ]

    for depth, analysts, provider in test_cases:
        # MemoryStateManager 通过 _calculate_estimated_duration
        manager = MemoryStateManager()
        params = {
            "research_depth": depth,
            "selected_analysts": analysts,
            "llm_provider": provider,
        }
        manager_result = manager._calculate_estimated_duration(params)

        # RedisProgressTracker 通过 _get_base_total_time
        tracker = RedisProgressTracker(
            task_id="test_unify",
            analysts=analysts,
            research_depth=depth,
            llm_provider=provider,
        )
        tracker_result = tracker._get_base_total_time()

        assert abs(manager_result - tracker_result) < 1, \
            f"不一致: depth={depth}, analysts={len(analysts)}, provider={provider}: " \
            f"MemoryStateManager={manager_result}, RedisProgressTracker={tracker_result}"
        print(f"  {depth}+{len(analysts)}分析师+{provider}: "
              f"Memory={manager_result:.0f}s, Redis={tracker_result:.0f}s ✓")

    print()


def test_task_state_time_fields():
    """测试 TaskState.to_dict() 包含时间字段"""
    print("=" * 70)
    print("测试 TaskState.to_dict() 时间字段")
    print("=" * 70)

    import asyncio
    from datetime import datetime

    manager = MemoryStateManager()

    # 创建任务
    task = asyncio.get_event_loop().run_until_complete(
        manager.create_task(
            task_id="test_time_fields",
            user_id="user1",
            stock_code="000001",
            parameters={"research_depth": "标准", "selected_analysts": ["market", "fundamentals"], "llm_provider": "dashscope"},
        )
    )

    d = task.to_dict()
    assert "elapsed_time" in d, "缺少 elapsed_time"
    assert "remaining_time" in d, "缺少 remaining_time"
    assert "estimated_total_time" in d, "缺少 estimated_total_time"
    assert d["remaining_time"] > 0, "remaining_time 应大于 0"
    assert d["estimated_total_time"] > 0, "estimated_total_time 应大于 0"
    print(f"  elapsed_time: {d['elapsed_time']:.1f}s ✓")
    print(f"  remaining_time: {d['remaining_time']:.1f}s ✓")
    print(f"  estimated_total_time: {d['estimated_total_time']:.1f}s ✓")

    print()


if __name__ == "__main__":
    try:
        test_static_function()
        test_unified_algorithm()
        test_task_state_time_fields()
        print("=" * 70)
        print("✅ 所有测试通过！")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
