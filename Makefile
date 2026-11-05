.PHONY: calidad lint tipos arquitectura test cobertura seguridad secretos complejidad fix

UV ?= uv

calidad: secretos lint tipos arquitectura complejidad test seguridad

lint:
	$(UV) run ruff check .

fix:
	$(UV) run ruff check . --fix
	$(UV) run ruff format apps/m01_identidad contratos/puertos/correo.py apps/m13_plataforma/adapters apps/m13_plataforma/middleware.py

tipos:
	$(UV) run mypy apps contratos config etl

arquitectura:
	$(UV) run lint-imports

test:
	$(UV) run pytest tests/unit -m unit --cov=apps --cov=contratos --cov=etl --cov-report=term-missing

cobertura: test

seguridad:
	$(UV) run bandit -r apps config etl contratos -x tests -ll

secretos:
	$(UV) run python scripts/scan_secrets.py

complejidad:
	$(UV) run python scripts/complejidad.py
