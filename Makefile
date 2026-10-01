.PHONY: install backend-test frontend-build dev docker-up

install:
	python -m venv .venv
	.venv/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

backend-test:
	PYTHONPATH=. ../.venv/bin/pytest -q

frontend-build:
	cd frontend && npm run build

dev:
	( cd backend && PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 ) & \
	( cd frontend && npm run dev -- --host 0.0.0.0 )

docker-up:
	docker compose up --build
