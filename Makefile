.PHONY: check format lint test clean

# 1) 格式化与自动修复（让机器先修掉低级错误）
format:
	@echo "Formatting..."
	python -m ruff format .
	python -m ruff check . --fix

# 2) 静态检查（只报硬伤，不报风格建议）
lint:
	@echo "Linting..."
	python -m ruff check .

# 3) 运行测试（关键验收步骤）
test:
	@echo "Running tests..."
	python -m pytest -vv --tb=short tests/

# 4) 一键验收（Agent 的最终目标）
check: format lint test
	@echo "All checks passed!"

clean:
	@echo "Cleaning..."
	python -c "import shutil; shutil.rmtree('.pytest_cache', ignore_errors=True)"
	python -c "import shutil; shutil.rmtree('.ruff_cache', ignore_errors=True)"

