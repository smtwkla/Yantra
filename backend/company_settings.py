"""Business configuration — flat constants, checked in, changed rarely (base pattern
§ Business Settings).  Values an IT admin changes at run time live in app_settings instead.
"""

# Access log (S013 § 2: ISO 27001 A.8.15 asks for a stated period; India's CERT-In
# directions of April 2022 ask for at least 180 days; 365 covers an annual review)
ACCESS_LOG_RETENTION_DAYS = 365
# A repeat of the same sighting within this window is not written again (S013 § 5.4)
SIGHTING_WINDOW_MINUTES = 10
# How long each process keeps the internal network ranges before reading them again
NETWORKS_CACHE_SECONDS = 300

# Job queue (S013 § 5.5, § 5.6)
DONE_TASK_RETENTION_DAYS = 90
# A running task whose lock has expired is taken to belong to a dead worker
TASK_LOCK_MINUTES = 10
# A failed attempt n waits n x this before the next one
TASK_RETRY_BACKOFF_MINUTES = 5
WORKER_POLL_SECONDS = 5
# Rows deleted per transaction by the access-log purge
PURGE_BATCH_ROWS = 10_000
# A retry delay a task asks for (RetryLater: a push service's Retry-After, S021 § 5.1) is
# capped here, so a send task cannot park itself for a day
TASK_RETRY_DELAY_MAX_SECONDS = 3600

# Web push (S021 § 3): requests has no timeout by default, so a hung push service would hold
# the worker; a send that takes longer is retried with the back-off
PUSH_TIMEOUT_SECONDS = 10
