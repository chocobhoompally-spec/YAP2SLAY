"""Validated functions exposed to Gemini and the frontend."""
from backend import scheduler_service as svc

def add_task(title: str, due_at: str, est_minutes: int, kind: str = "assignment", priority: int = 2) -> dict:
    """Add a task. due_at is ISO 8601; effort is minutes; priority is 1, 2, or 3."""
    return svc.add_task(title,due_at,est_minutes,kind,priority)
def list_tasks(include_done: bool = False) -> list[dict]:
    """List saved student tasks and their completion status."""
    return svc.list_tasks(include_done)
def set_available_time(date: str, start_time: str, end_time: str) -> dict:
    """Set study availability on YYYY-MM-DD between HH:MM local times."""
    return svc.set_available_time(date,start_time,end_time)
def generate_schedule() -> dict:
    """Rebuild upcoming study blocks and report any task shortfall."""
    return svc.rebuild_and_log()
def report_lost_time(minutes: int, date: str = "") -> dict: return svc.report_lost_time(minutes,date)
def block_time(date: str,start_time: str,end_time: str,reason: str = "") -> dict: return svc.block_time(date,start_time,end_time,reason)
def complete_task(task_id: int) -> dict: return svc.complete_task(task_id)
def delete_task(task_id: int) -> dict:
    """Delete a saved task and rebuild the remaining schedule."""
    return svc.delete_task(task_id)
def log_progress(task_id: int,minutes_done: int) -> dict: return svc.log_progress(task_id,minutes_done)
def update_task(task_id: int,title: str = "",due_at: str = "",est_minutes: int = 0,priority: int = 0) -> dict: return svc.update_task(task_id,title,due_at,est_minutes,priority)
ALL_TOOLS=[add_task,list_tasks,set_available_time,generate_schedule,report_lost_time,block_time,complete_task,delete_task,log_progress,update_task]
