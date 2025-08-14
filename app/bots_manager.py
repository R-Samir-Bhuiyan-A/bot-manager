# app/bots_manager.py
import os
import json
import signal
import shutil
import psutil
import tomli
import tomli_w
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .schemas import BotConfig, ScheduleItem
from .utils import assure_dir

ROOT = Path(__file__).resolve().parent.parent

# Keep templates in the image; put instances in /data
TEMPLATES_DIR = Path(os.environ.get("TEMPLATES_DIR", "/app/templates"))
INSTANCES_DIR = Path(os.environ.get("BOTS_ROOT", "/data/bots"))

DISCUM_TEMPLATE = TEMPLATES_DIR / "discum_selfbot"

class BotProc:
    def __init__(self, bot_id: str, path: Path):
        self.bot_id = bot_id
        self.path = path
        self.proc: Optional[subprocess.Popen] = None
        self.logfile = self.path / "logs" / "bot.log"
        self.status = "stopped"
        self.started_at: Optional[datetime] = None
        self.last_exit: Optional[int] = None
        self.pid: Optional[int] = None

    def is_running(self) -> bool:
        if self.proc is not None and self.proc.poll() is None:
            return True
        if self.pid:
            try:
                p = psutil.Process(self.pid)
                return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
            except Exception:
                return False
        return False


class BotRegistry:
    def __init__(self):
        self.bots: Dict[str, BotProc] = {}
        self.scheduler = BackgroundScheduler(daemon=True)
        self.scheduler.start()

        # Ensure dirs exist
        assure_dir(TEMPLATES_DIR)
        assure_dir(INSTANCES_DIR)

        # Sanity check template
        if not (DISCUM_TEMPLATE / "bot.py").exists():
            raise FileNotFoundError(f"Template missing: {DISCUM_TEMPLATE}/bot.py")

        self._discover()

    def _discover(self):
        for p in INSTANCES_DIR.glob("bot_*"):
            if (p / "bot.py").exists():
                bot_id = p.name
                bp = BotProc(bot_id, p)
                # If a stale PID file exists, pick it up
                pidfile = p / "run.pid"
                if pidfile.exists():
                    try:
                        bp.pid = int(pidfile.read_text().strip())
                    except Exception:
                        pass
                self.bots[bot_id] = bp

    def create_from_template(self, name: str) -> str:
        idx = 1
        while True:
            candidate = f"bot_{idx}"
            dest = INSTANCES_DIR / candidate
            if candidate not in self.bots and not dest.exists():
                break
            idx += 1

        shutil.copytree(DISCUM_TEMPLATE, dest)
        assure_dir(dest / "logs")

        # personalize config name (tolerant if persona missing)
        cfg_path = dest / "config.toml"
        if cfg_path.exists():
            with open(cfg_path, "rb") as f:
                cfg = tomli.load(f)
            persona = cfg.get("persona", {})
            persona["name"] = name
            cfg["persona"] = persona
            with open(cfg_path, "wb") as f:
                tomli_w.dump(cfg, f)

        self.bots[candidate] = BotProc(candidate, dest)
        self._apply_schedules(candidate)
        return candidate

    def delete(self, bot_id: str):
        b = self._get(bot_id)
        if b.is_running():
            raise RuntimeError("Stop the bot before deleting")
        shutil.rmtree(b.path, ignore_errors=True)
        # remove its schedules
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith(f"{bot_id}:"):
                self.scheduler.remove_job(job.id)
        self.bots.pop(bot_id, None)

    def start(self, bot_id: str):
        b = self._get(bot_id)
        if b.is_running():
            return
        assure_dir(b.path / "logs")
        env = os.environ.copy()
        env["BOT_ID"] = bot_id
        env["BOT_COMMAND"] = env.get("BOT_COMMAND", "")

        # Open log file line-buffered for smooth tailing
        logfh = open(b.logfile, "a", encoding="utf-8", buffering=1)
        # Spawn process
        b.proc = subprocess.Popen(
            ["python", "bot.py"],
            cwd=b.path,
            stdout=logfh,
            stderr=subprocess.STDOUT,
            env=env
        )
        b.pid = b.proc.pid
        (b.path / "run.pid").write_text(str(b.pid))
        b.status = "running"
        b.started_at = datetime.utcnow()
        b.last_exit = None

    def stop(self, bot_id: str):
        b = self._get(bot_id)
        if not b.is_running():
            b.status = "stopped"
            return
        try:
            if b.proc and b.proc.poll() is None:
                b.proc.send_signal(signal.SIGTERM)
                b.proc.wait(timeout=10)
            elif b.pid:
                os.kill(b.pid, signal.SIGTERM)
        except Exception:
            try:
                if b.proc and b.proc.poll() is None:
                    b.proc.kill()
                elif b.pid:
                    os.kill(b.pid, signal.SIGKILL)
            except Exception:
                pass
        if b.proc:
            b.last_exit = b.proc.returncode
        b.proc = None
        b.pid = None
        try:
            (b.path / "run.pid").unlink(missing_ok=True)
        except Exception:
            pass
        b.status = "stopped"

    def restart(self, bot_id: str):
        self.stop(bot_id)
        self.start(bot_id)

    def config_path(self, bot_id: str) -> Path:
        return self._get(bot_id).path / "config.toml"

    def read_config(self, bot_id: str) -> BotConfig:
        cfg_path = self.config_path(bot_id)
        raw = {}
        if cfg_path.exists():
            with open(cfg_path, "rb") as f:
                raw = tomli.load(f)
        return BotConfig(**raw)

    def write_config(self, bot_id: str, cfg: BotConfig):
        with open(self.config_path(bot_id), "wb") as f:
            tomli_w.dump(json.loads(cfg.json(by_alias=True)), f)
        self._apply_schedules(bot_id)

    def _apply_schedules(self, bot_id: str):
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith(f"{bot_id}:"):
                self.scheduler.remove_job(job.id)
        cfg = self.read_config(bot_id)
        for i, sch in enumerate(cfg.schedules):
            self._add_schedule(bot_id, i, sch)

    def _add_schedule(self, bot_id: str, idx: int, sch: ScheduleItem):
        job_id = f"{bot_id}:{idx}"

        def do_action():
            os.environ["BOT_COMMAND"] = sch.custom_cmd or ""
            if sch.action == "start":
                self.start(bot_id)
            elif sch.action == "stop":
                self.stop(bot_id)
            elif sch.action == "restart":
                self.restart(bot_id)
            elif sch.action == "custom":
                # By convention, restart to pick up custom command
                self.restart(bot_id)

        if sch.cron:
            trig = CronTrigger.from_crontab(sch.cron)
            self.scheduler.add_job(do_action, trig, id=job_id, replace_existing=True)
        else:
            every = sch.every_seconds if sch.every_seconds else 3600
            self.scheduler.add_job(do_action, "interval", seconds=every, id=job_id, replace_existing=True)

    def _get(self, bot_id: str) -> BotProc:
        if bot_id not in self.bots:
            raise FileNotFoundError(bot_id)
        return self.bots[bot_id]

    def snapshot(self) -> List[dict]:
        items = []
        for bot_id, b in self.bots.items():
            # Normalize running status from actual PID
            running = b.is_running()
            status = "running" if running else "stopped"
            cpu = 0.0
            mem = 0.0
            pid = None
            if running and b.pid:
                try:
                    p = psutil.Process(b.pid)
                    pid = p.pid
                    # Use non-blocking cpu_percent (cached) — avoid interval sleeps
                    _ = p.cpu_percent(interval=None)
                    cpu = p.cpu_percent(interval=None)
                    mem = p.memory_info().rss / (1024 * 1024)
                except Exception:
                    pass

            name = bot_id
            try:
                with open(self.config_path(bot_id), "rb") as f:
                    name = tomli.load(f).get("persona", {}).get("name", bot_id)
            except Exception:
                pass

            items.append({
                "id": bot_id,
                "name": name,
                "status": status,
                "pid": pid,
                "cpu": round(cpu, 1),
                "memory_mb": round(mem, 1),
                "started_at": b.started_at.isoformat() if b.started_at else None,
                "log": str(b.logfile)
            })
        return items
