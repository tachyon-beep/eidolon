.PHONY: up down sample

up:
	docker compose up -d

sample:
	uv run python sample_telemetry.py

stack-test: up sample
	@echo "Telemetry sent; check Grafana/Prometheus"
	docker compose down

