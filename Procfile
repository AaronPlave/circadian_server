web: python -c"import server.sources as sources; sources.refresh_sources(1)" & newrelic-admin run-program gunicorn runserver:app --workers $WEB_CONCURRENCY --log-file - 