# Data-to-Dirt Master Makefile
# Pure offline build and launch system

SHELL := /bin/bash
PYTHON ?= python3

.PHONY: all build run test clean check-env

all: build

check-env:
	@echo "=================================================="
	@echo "  DATA-TO-DIRT: Verifying Runtime & Toolchain     "
	@echo "=================================================="
	@which $(PYTHON) > /dev/null || (echo "[-] Error: python3 not found." && exit 1)
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'"
	@echo "[+] Python version: $$($(PYTHON) --version)"
	@$(PYTHON) -c "import flask, numpy; print('[+] Python packages: flask, numpy verified')"

build: check-env
	@echo "[+] Verifying UI assets and application structure..."
	@test -f src/ui/index.html || (echo "[-] Error: src/ui/index.html missing" && exit 1)
	@test -f src/app/server.py || (echo "[-] Error: src/app/server.py missing" && exit 1)
	@if [ -d src/engine ] && [ -f src/engine/Makefile ]; then \
		echo "[+] Compiling native acceleration modules..."; \
		$(MAKE) -C src/engine; \
	fi
	@echo "=================================================="
	@echo "  [✓] Build Succeeded (Zero external downloads)   "
	@echo "=================================================="

run: build
	@echo "[+] Starting Data-to-Dirt desktop application..."
	@$(PYTHON) src/app/server.py --launch-window

test:
	@echo "=================================================="
	@echo "  DATA-TO-DIRT: Executing Test Suite              "
	@echo "=================================================="
	@TEST_MODE=1 $(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
	@echo "=================================================="
	@echo "  [✓] All tests passed!                           "
	@echo "=================================================="

clean:
	@rm -rf `find . -type d -name "__pycache__"`
	@rm -rf `find . -type d -name ".pytest_cache"`
	@rm -f `find . -type f -name "*.pyc"`
	@rm -f data/test_app_state.json
	@if [ -d src/engine ] && [ -f src/engine/Makefile ]; then \
		$(MAKE) -C src/engine clean; \
	fi
	@echo "[✓] Cleaned cache files."
