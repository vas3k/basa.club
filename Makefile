SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:

.PHONY: docker-run-production
docker-run-production:
	python manage.py migrate --noinput
	python manage.py update_categories || true
	python manage.py collectstatic --noinput
	exec gunicorn vas3k_base.wsgi:application \
		--bind 0.0.0.0:8000 \
		--workers 2 --worker-class gthread --threads 2 \
		--user 1000 --group 1000 \
		--timeout 60 --graceful-timeout 30 \
		--max-requests 300 --max-requests-jitter 50 \
		--access-logfile - --error-logfile - \
		--access-logformat '%(h)s %(m)s %(U)s %(s)s %(L)s'
