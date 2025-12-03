.PHONY: help install run docker-build docker-up docker-down docker-logs

help:
	@echo "Infinity Balance Bot - Commands"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run bot locally"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start bot in Docker"
	@echo "  make docker-down  - Stop bot"
	@echo "  make docker-logs  - View logs"

install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

run:
	./venv/bin/python bot.py

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f bot
