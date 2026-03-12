PYTHON     = .venv/bin/python
PIP        = .venv/bin/pip
PYTEST     = .venv/bin/pytest
BLACK      = .venv/bin/black
RUFF       = .venv/bin/ruff
PYTHONPATH = /data/PiesPlanos

.DEFAULT_GOAL := help

# ── Help ───────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@echo ""
	@echo "  Pies Planos — comandos disponibles"
	@echo ""
	@echo "  Setup"
	@echo "    make install       Crear .venv e instalar dependencias"
	@echo ""
	@echo "  Juego"
	@echo "    make play          Arrancar el juego en terminal"
	@echo "    make bot           Arrancar Bot Lovecraft (Telegram)"
	@echo ""
	@echo "  Tests"
	@echo "    make test          Ejecutar todos los tests"
	@echo "    make test-fast     Tests sin los de humo (más rápido)"
	@echo "    make test-bot      Solo tests del bot"
	@echo "    make test-engine   Solo tests del motor de juego"
	@echo "    make coverage      Tests con informe de cobertura"
	@echo ""
	@echo "  Calidad de código"
	@echo "    make fmt           Formatear código con Black"
	@echo "    make lint          Linting con Ruff"
	@echo "    make check         fmt + lint (sin modificar)"
	@echo ""
	@echo "  Base de datos"
	@echo "    make db-setup      Crear DB y usuario en MariaDB (requiere root)"
	@echo "    make db-shell      Conectar a la DB como piesplanos_bot"
	@echo ""
	@echo "  Utilidades"
	@echo "    make clean         Limpiar caches y archivos temporales"
	@echo "    make logs          Ver últimas líneas del log (si LOG_LEVEL != NONE)"
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────

.PHONY: install
install:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo ""
	@echo "  Listo. Copia .env.example a .env y rellena tus claves API."

# ── Juego ──────────────────────────────────────────────────────────────────

.PHONY: play
play:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) main.py

.PHONY: bot
bot:
	@if [ -z "$$TELEGRAM_TOKEN" ] && ! grep -q "TELEGRAM_TOKEN=." .env 2>/dev/null; then \
		echo "  ERROR: TELEGRAM_TOKEN no configurado en .env"; exit 1; \
	fi
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m bot.lovecraft

# ── Tests ──────────────────────────────────────────────────────────────────

.PHONY: test
test:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/ -v

.PHONY: test-fast
test-fast:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/ -v --ignore=tests/test_smoke.py

.PHONY: test-bot
test-bot:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/bot/ -v

.PHONY: test-engine
test-engine:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/ -v --ignore=tests/bot/

.PHONY: coverage
coverage:
	PYTHONPATH=$(PYTHONPATH) $(PYTEST) tests/ --cov=src --cov=bot \
		--cov-report=term-missing --cov-report=html
	@echo ""
	@echo "  Informe HTML en htmlcov/index.html"

# ── Calidad de código ──────────────────────────────────────────────────────

.PHONY: fmt
fmt:
	$(BLACK) src/ bot/ tests/ main.py

.PHONY: lint
lint:
	$(RUFF) check src/ bot/ tests/ main.py

.PHONY: check
check:
	$(BLACK) --check src/ bot/ tests/ main.py
	$(RUFF) check src/ bot/ tests/ main.py

# ── Base de datos ──────────────────────────────────────────────────────────

.PHONY: db-setup
db-setup:
	@echo "  Ejecutando como root en MariaDB..."
	mysql -u root -p -e " \
		CREATE DATABASE IF NOT EXISTS piesplanos \
			CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; \
		CREATE USER IF NOT EXISTS 'piesplanos_bot'@'localhost' \
			IDENTIFIED BY '$$DB_PASSWORD'; \
		GRANT ALL PRIVILEGES ON piesplanos.* TO 'piesplanos_bot'@'localhost'; \
		FLUSH PRIVILEGES;"
	@echo "  DB creada. El bot crea las tablas en el primer arranque."

.PHONY: db-shell
db-shell:
	mysql -u piesplanos_bot -p piesplanos

# ── Utilidades ─────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name .coverage -delete 2>/dev/null || true
	@echo "  Limpio."

.PHONY: logs
logs:
	@if [ -f game.log ]; then tail -50 game.log; \
	else echo "  No hay fichero de log. Pon LOG_LEVEL=DEBUG en .env para activarlo."; fi
