# TradingAgents-CN Performance Test Suite

This directory contains performance tests for the TradingAgents-CN application.

## Test Categories

### 1. API Performance Tests (`test_api_performance.py`)
- Health check endpoint response time
- Root endpoint response time
- Stock list endpoint performance
- Screening endpoint performance
- Analysis endpoint performance
- Config endpoint performance
- Response consistency tests

### 2. Data Source Performance Tests (`test_data_source_performance.py`)
- AKShare adapter availability and response time
- AKShare stock list retrieval performance
- BaoStock adapter availability and response time
- BaoStock stock list retrieval performance
- Tushare adapter availability
- Cross-source comparison
- Error handling performance

### 3. Database Performance Tests (`test_database_performance.py`)
- Database connection establishment time
- Read operation performance
- Write operation performance
- Filtered query performance
- Aggregation pipeline performance
- Index effectiveness
- Bulk read performance
- Concurrent operations

### 4. Cache Performance Tests (`test_cache_performance.py`)
- Redis connection establishment time
- Write operation performance
- Read operation performance
- Batch write performance
- Batch read performance
- Delete operation performance
- Key pattern matching
- TTL operations

### 5. Concurrent Performance Tests (`test_concurrent_performance.py`)
- Concurrent health check requests
- Mixed endpoint concurrent requests
- High load handling
- Request queue handling
- Sequential vs concurrent comparison

## Running Tests

### Run All Performance Tests
```bash
python tests/performance/run_performance_tests.py -v
```

### Run Specific Test Category
```bash
# API tests only
pytest tests/performance/test_api_performance.py -v

# Data source tests only
pytest tests/performance/test_data_source_performance.py -v

# Database tests only
pytest tests/performance/test_database_performance.py -v

# Cache tests only
pytest tests/performance/test_cache_performance.py -v

# Concurrent tests only
pytest tests/performance/test_concurrent_performance.py -v
```

### Run with pytest Markers
```bash
# Run all performance tests
pytest -m performance -v

# Run only performance tests (excluding integration)
pytest -m "performance and not integration" -v
```

## Performance Baseline

The `performance_baseline.json` file contains threshold values for each test. Tests will fail if they exceed these thresholds.

### Current Baselines
| Test | Threshold |
|------|-----------|
| API Health Check | 1.0s |
| AKShare Stock List | 30.0s |
| BaoStock Stock List | 60.0s |
| Database Read | 2.0s |
| Cache Write | 0.5s |
| Concurrent 10 Requests | 15.0s |
| Concurrent 50 Requests | 60.0s |

## Test Results

After running tests, results are saved to:
- `performance_results.json` - Raw test results
- `performance_report.json` - Summary report with analysis

### Viewing Results
```bash
# Run tests and generate report
python tests/performance/run_performance_tests.py -v --output report.json

# View the report
cat tests/performance/performance_report.json
```

## Performance Metrics Collected

Each test collects:
- **Elapsed time**: Total execution time in seconds
- **Success status**: Whether the operation completed successfully
- **Details**: Additional metrics (record counts, error info, etc.)

## Baseline Recommendations

### API Endpoints
- Simple endpoints (health, root): < 1s
- Complex endpoints (analysis, screening): < 5s
- Data-heavy endpoints (stock list): < 10s

### Data Sources
- Availability check: < 5s
- Stock list retrieval: < 30s (AKShare), < 60s (BaoStock)
- Error handling: < 5s per source

### Database
- Simple reads: < 2s
- Complex queries: < 5s
- Bulk operations: < 10s

### Cache
- Single operations: < 0.5s
- Batch operations: < 2s

### Concurrent
- 10 concurrent requests: < 15s
- 50 concurrent requests: < 60s

## Troubleshooting

### Tests Skipping
Tests will skip if:
- Required services (MongoDB, Redis) are not available
- Data source adapters cannot be initialized
- Test client cannot be created

### Tests Failing
If tests fail with threshold exceeded:
1. Check the actual vs expected times in the error message
2. Review the performance report for details
3. Consider updating baselines if the change is expected
4. Investigate potential performance regressions

### Common Issues
1. **MongoDB connection error**: Ensure MongoDB is running and configured
2. **Redis connection error**: Ensure Redis is running and configured
3. **Data source unavailable**: Check API keys and network connectivity
4. **Import errors**: Ensure all dependencies are installed

## CI/CD Integration

To run performance tests in CI/CD:

```yaml
# Example GitHub Actions step
- name: Run Performance Tests
  run: |
    python tests/performance/run_performance_tests.py -v --output performance_report.json
    
- name: Upload Performance Report
  uses: actions/upload-artifact@v3
  with:
    name: performance-report
    path: tests/performance/performance_report.json
```

## Contributing

When adding new performance tests:
1. Follow the existing test structure
2. Add appropriate baselines to `performance_baseline.json`
3. Update this README if adding new test categories
4. Ensure tests can gracefully skip when services are unavailable
