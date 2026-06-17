from celery import Celery
from app.core.config import get_settings

settings = get_settings()

app = Celery(
    "github-code-review-agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "review.*": {"queue": "review"},
    },
    task_default_queue="default",
    task_track_started=True,
    task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    task_time_limit=settings.CELERY_TASK_TIMEOUT + 60,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    task_always_eager=settings.CELERY_ALWAYS_EAGER,
    task_eager_propagates=True,
)

app.autodiscover_tasks(["app.tasks"])
