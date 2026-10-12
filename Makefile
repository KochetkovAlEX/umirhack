# Команды для Linux/macOS/Git Bash. Для Windows PowerShell есть tasks.ps1
PY ?= .venv/bin/python
ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python
endif

.PHONY: venv models predict eval backend frontend bot build-frontend

venv:
	python3.12 -m venv .venv || py -3.12 -m venv .venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -r requirements/dev.txt

models:
	$(PY) scripts/download_models.py

predict:
	$(PY) scripts/predict.py --manifest data/documents.json --questions data/questions.json --base data \
		--input image --out results.json --reference data/reference_results.json

eval:
	$(PY) data/evaluate.py --reference data/reference_results.json --predictions results.json

build-frontend:
	cd frontend && npm install && npm run build

backend:
	cd backend && $(abspath $(PY)) manage.py migrate && $(abspath $(PY)) manage.py runserver 0.0.0.0:8000

frontend:
	cd frontend && npm run dev

bot:
	$(PY) -m bot
