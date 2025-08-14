# app/schemas.py
from pydantic import BaseModel, Field, Extra
from typing import Optional, List

class ScheduleItem(BaseModel):
    name: str = "schedule"
    action: str = "restart"       # start|stop|restart|custom
    cron: Optional[str] = None    # crontab string
    every_seconds: Optional[int] = None
    custom_cmd: Optional[str] = None

class BotConfig(BaseModel, extra=Extra.allow):
    schedules: List[ScheduleItem] = Field(default_factory=list)
