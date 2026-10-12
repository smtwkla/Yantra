"""Gunicorn production configuration."""

bind = "0.0.0.0:5000"
workers = 3
worker_class = "sync"
timeout = 120

# On SIGTERM (a deploy), let workers finish the request they are serving instead
# of dropping it. An operator mid-entry then gets a completed save rather than a
# connection reset — see stop_grace_period on the backend service, which must be
# at least this long or Docker SIGKILLs before the drain finishes.
graceful_timeout = 30

# Logging
accesslog = "-"   # stdout
errorlog = "-"    # stderr
loglevel = "info"
