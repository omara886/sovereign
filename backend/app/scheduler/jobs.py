from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler(timezone="Asia/Riyadh")


def _noop(name: str):
    print(f"job:{name}")


def register_jobs() -> None:
    scheduler.add_job(lambda: _noop("monday_strategy_run"), CronTrigger(day_of_week="mon", hour=8, minute=0))
    scheduler.add_job(lambda: _noop("monday_plan_notification"), CronTrigger(day_of_week="mon", hour=9, minute=0))
    scheduler.add_job(lambda: _noop("sunday_analytics_run"), CronTrigger(day_of_week="sun", hour=18, minute=0))
    scheduler.add_job(lambda: _noop("process_publish_queue"), CronTrigger(minute="*/5"))


register_jobs()
