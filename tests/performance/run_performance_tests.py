#!/usr/bin/env python3
"""
Performance test runner for TradingAgents-CN

This script runs all performance tests and generates a comprehensive report.

Usage:
    python run_performance_tests.py [--verbose] [--output report.json]
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_performance_tests(verbose: bool = False, output_file: str = None):
    """Run all performance tests and collect results"""
    import pytest

    # Test files to run
    test_files = [
        "tests/performance/test_api_performance.py",
        "tests/performance/test_data_source_performance.py",
        "tests/performance/test_database_performance.py",
        "tests/performance/test_cache_performance.py",
        "tests/performance/test_concurrent_performance.py",
    ]

    # Build pytest arguments
    pytest_args = [
        "-v" if verbose else "-q",
        "--tb=short",
        "-x",  # Stop on first failure
    ]

    # Add test files
    for test_file in test_files:
        test_path = Path(PROJECT_ROOT) / test_file
        if test_path.exists():
            pytest_args.append(str(test_path))
        else:
            print(f"⚠️  Test file not found: {test_file}")

    # Run tests
    print("=" * 70)
    print("🚀 TradingAgents-CN Performance Test Suite")
    print("=" * 70)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Project: {PROJECT_ROOT}")
    print("=" * 70)

    start_time = time.time()
    exit_code = pytest.main(pytest_args)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"⏱️  Total test time: {elapsed:.2f} seconds")
    print(f"📊 Exit code: {exit_code}")
    print("=" * 70)

    # Collect results
    results_path = Path(PROJECT_ROOT) / "tests" / "performance" / "performance_results.json"
    if results_path.exists():
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        # Generate summary
        summary = generate_summary(results, elapsed, exit_code)

        # Save report
        report_path = Path(output_file) if output_file else Path(PROJECT_ROOT) / "tests" / "performance" / "performance_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n📄 Performance report saved to: {report_path}")
        print_summary(summary)

        return exit_code == 0

    return exit_code == 0


def generate_summary(results: dict, elapsed: float, exit_code: int) -> dict:
    """Generate performance test summary"""
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get("passed", False))
    failed_tests = total_tests - passed_tests

    # Group results by category
    categories = {}
    for test_name, result in results.items():
        category = test_name.split("_")[0]
        if category not in categories:
            categories[category] = {"tests": [], "total_time": 0}
        categories[category]["tests"].append({
            "name": test_name,
            "elapsed": result.get("elapsed_seconds", 0),
            "details": result.get("details", {})
        })
        categories[category]["total_time"] += result.get("elapsed_seconds", 0)

    # Find slowest tests
    slowest_tests = sorted(
        [{"name": k, "elapsed": v.get("elapsed_seconds", 0)} for k, v in results.items()],
        key=lambda x: x["elapsed"],
        reverse=True
    )[:5]

    return {
        "timestamp": datetime.now().isoformat(),
        "total_duration_seconds": round(elapsed, 2),
        "exit_code": exit_code,
        "summary": {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": round(passed_tests / total_tests * 100, 1) if total_tests > 0 else 0
        },
        "categories": categories,
        "slowest_tests": slowest_tests,
        "raw_results": results
    }


def print_summary(summary: dict):
    """Print performance summary to console"""
    print("\n📊 Performance Test Summary")
    print("-" * 70)
    print(f"✅ Passed: {summary['summary']['passed']}")
    print(f"❌ Failed: {summary['summary']['failed']}")
    print(f"📈 Pass Rate: {summary['summary']['pass_rate']}%")
    print(f"⏱️  Total Duration: {summary['total_duration_seconds']}s")

    print("\n📁 Results by Category:")
    for category, data in summary["categories"].items():
        print(f"  {category}: {len(data['tests'])} tests, {data['total_time']:.2f}s total")

    print("\n🐢 Slowest Tests:")
    for test in summary["slowest_tests"]:
        print(f"  {test['name']}: {test['elapsed']:.4f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TradingAgents-CN performance tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output", "-o", type=str, help="Output report file path")

    args = parser.parse_args()

    success = run_performance_tests(verbose=args.verbose, output_file=args.output)
    sys.exit(0 if success else 1)
