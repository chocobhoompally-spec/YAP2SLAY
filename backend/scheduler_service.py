"""Validated application operations joining SQLite with the pure scheduler."""
from __future__ import annotations
import os
from datetime import datetime, date as date_type, time, timedelta
from zoneinfo import ZoneInfo
from backend import db
from backend.scheduler import Task, build_schedule, slots_from_availability

def tz(): return ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
def _ensure(): db.init()
def now(): return datetime.now(tz())
def parse_due(value: str) -> datetime:
    try: d=datetime.fromisoformat(value)
    except (TypeError,ValueError): raise ValueError("Deadline must be an ISO 8601 date/time, e.g. 2026-10-23T09:00+05:30")
    if d.tzinfo is None: d=d.replace(tzinfo=tz())
    d=d.astimezone(tz())
    if d<=now(): raise ValueError("Deadline must be in the future")
    return d
def parse_day(value: str) -> str:
    try: return date_type.fromisoformat(value).isoformat()
    except (TypeError,ValueError): raise ValueError("Date must use YYYY-MM-DD")
def parse_window(day, start, end):
    day=parse_day(day)
    try: a=time.fromisoformat(start); b=time.fromisoformat(end)
    except (TypeError,ValueError): raise ValueError("Times must use HH:MM (24-hour format)")
    if a.second or b.second or a.microsecond or b.microsecond or b<=a: raise ValueError("End time must be later than start time")
    if (datetime.combine(date_type.fromisoformat(day),b,tzinfo=tz())-datetime.combine(date_type.fromisoformat(day),a,tzinfo=tz())).total_seconds()<1800: raise ValueError("Availability must be at least 30 minutes")
    return day,a.strftime("%H:%M"),b.strftime("%H:%M")
def rebuild(c=None):
    owned=c is None
    if owned: _ensure(); c=db.connect()
    current=now()
    rows=c.execute("SELECT * FROM tasks WHERE status!='done'").fetchall()
    tasks=[Task(r['id'],r['title'],datetime.fromisoformat(r['due_at']),max(0,r['est_minutes']-r['done_minutes']),r['priority']) for r in rows]
    future_slots=slots_from_availability([dict(x) for x in c.execute("SELECT * FROM availability")],tz(),current)
    # Keep a block that began before now as history, but do not allocate over
    # its still-running tail when a rebuild happens mid-session.
    active=[(datetime.fromisoformat(r['start_at']),datetime.fromisoformat(r['end_at']))
            for r in c.execute("SELECT start_at,end_at FROM blocks WHERE start_at<? AND end_at>?",(current.isoformat(),current.isoformat()))]
    future_slots=[s for s in future_slots if not any(s < end and s+timedelta(minutes=30) > start for start,end in active)]
    blocks,short=build_schedule(tasks,future_slots,current)
    c.execute("DELETE FROM blocks WHERE start_at>=?",(current.isoformat(),))
    for tid,start,end in blocks: c.execute("INSERT INTO blocks(task_id,start_at,end_at) VALUES(?,?,?)",(tid,start.isoformat(),end.isoformat()))
    if owned: c.commit(); c.close()
    return {"blocks":len(blocks),"unscheduled":[{"task_id":i,"title":next(t.title for t in tasks if t.id==i),"remaining_minutes":m} for i,m in short.items()]}
def rebuild_and_log():
    with db.connect() as c:
        plan=rebuild(c)
        summary=f"Built {plan['blocks']} blocks"
        if plan['unscheduled']:
            summary += "; shortfall: "+", ".join(f"{x['title']} ({x['remaining_minutes']} min)" for x in plan['unscheduled'])
        db.log_action(c,"generate_schedule",summary)
        return {"ok":True,"message":summary,"schedule":plan}
def _result(c,tool,summary,extra=None):
    plan=rebuild(c); msg=summary
    if plan['unscheduled']: msg += "; shortfall: "+", ".join(f"{x['title']} ({x['remaining_minutes']} min)" for x in plan['unscheduled'])
    db.log_action(c,tool,msg)
    return {"ok":True,"message":msg,"schedule":plan,**(extra or {})}
def add_task(title,due_at,est_minutes,kind="assignment",priority=2):
    try:
        _ensure()
        title=str(title).strip(); kind=str(kind).strip().lower(); est_minutes=int(est_minutes); priority=int(priority); due=parse_due(due_at)
        if not title or len(title)>200: raise ValueError("Title must contain 1 to 200 characters")
        if kind not in {"exam","assignment","reading","personal","other"}: raise ValueError("Kind must be exam, assignment, reading, personal, or other")
        if not 1<=est_minutes<=100000: raise ValueError("Estimated minutes must be between 1 and 100000")
        if priority not in (1,2,3): raise ValueError("Priority must be 1 (low), 2 (normal), or 3 (high)")
        with db.connect() as c:
            cur=c.execute("INSERT INTO tasks(title,kind,due_at,est_minutes,priority) VALUES(?,?,?,?,?)",(title,kind,due.isoformat(),est_minutes,priority))
            tid=cur.lastrowid; out=_result(c,"add_task",f"Added task: {title}",{"task_id":tid})
        return out
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def list_tasks(include_done=False): return db.list_tasks(bool(include_done))
def set_available_time(date,start_time,end_time):
    try:
        _ensure()
        day,a,b=parse_window(date,start_time,end_time)
        with db.connect() as c:
            c.execute("DELETE FROM availability WHERE date=?",(day,)); c.execute("INSERT INTO availability(date,start_time,end_time) VALUES(?,?,?)",(day,a,b))
            return _result(c,"set_available_time",f"Set study availability on {day} from {a} to {b}")
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def _subtract(c,day,start,end):
    for w in c.execute("SELECT * FROM availability WHERE date=?",(day,)).fetchall():
        lo=max(start,w['start_time']); hi=min(end,w['end_time'])
        if lo>=hi: continue
        c.execute("DELETE FROM availability WHERE id=?",(w['id'],))
        if w['start_time']<lo: c.execute("INSERT INTO availability(date,start_time,end_time) VALUES(?,?,?)",(day,w['start_time'],lo))
        if hi<w['end_time']: c.execute("INSERT INTO availability(date,start_time,end_time) VALUES(?,?,?)",(day,hi,w['end_time']))
def block_time(date,start_time,end_time,reason=""):
    try:
        _ensure()
        day,a,b=parse_window(date,start_time,end_time)
        with db.connect() as c:
            _subtract(c,day,a,b)
            return _result(c,"block_time",f"Blocked {a}-{b} on {day}"+(f": {str(reason)[:120]}" if reason else ""))
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def report_lost_time(minutes,date=""):
    try:
        _ensure()
        minutes=int(minutes)
        if minutes<1: raise ValueError("Lost time must be a positive number of minutes")
        day=parse_day(date or now().date().isoformat()); rem=minutes
        with db.connect() as c:
            windows=c.execute("SELECT * FROM availability WHERE date=? ORDER BY start_time",(day,)).fetchall()
            for w in windows:
                if rem<=0: break
                start=datetime.combine(date_type.fromisoformat(day),time.fromisoformat(w['start_time']),tzinfo=tz())
                end=datetime.combine(date_type.fromisoformat(day),time.fromisoformat(w['end_time']),tzinfo=tz())
                start=max(start,now()); available=max(0,int((end-start).total_seconds()//60)); cut=min(rem,available); rem-=cut
                if cut:
                    cut_end=start+timedelta(minutes=cut)
                    _subtract(c,day,start.strftime('%H:%M'),cut_end.strftime('%H:%M'))
            return _result(c,"report_lost_time",f"Removed {minutes-rem} minutes of study availability on {day}")
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def complete_task(task_id):
    try:
        _ensure()
        tid=int(task_id)
        with db.connect() as c:
            row=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
            if not row: raise ValueError(f"No task exists with ID {tid}")
            if row['status']=='done': return {"ok":True,"message":"Task is already complete","schedule":{"blocks":0,"unscheduled":[]}}
            c.execute("UPDATE tasks SET status='done',done_minutes=est_minutes WHERE id=?",(tid,))
            return _result(c,"complete_task",f"Completed task: {row['title']}")
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def log_progress(task_id,minutes_done):
    try:
        _ensure()
        tid=int(task_id); mins=int(minutes_done)
        if mins<1: raise ValueError("Progress must be a positive number of minutes")
        with db.connect() as c:
            row=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
            if not row: raise ValueError(f"No task exists with ID {tid}")
            if row['status']=='done': raise ValueError("Task is already complete")
            done=min(row['est_minutes'],row['done_minutes']+mins); status='done' if done>=row['est_minutes'] else 'todo'
            c.execute("UPDATE tasks SET done_minutes=?,status=? WHERE id=?",(done,status,tid))
            return _result(c,"log_progress",f"Logged {done-row['done_minutes']} minutes on {row['title']}")
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def update_task(task_id,title="",due_at="",est_minutes=0,priority=0):
    try:
        _ensure()
        tid=int(task_id)
        with db.connect() as c:
            row=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
            if not row: raise ValueError(f"No task exists with ID {tid}")
            newtitle=str(title).strip() if title else row['title']; due=parse_due(due_at).isoformat() if due_at else row['due_at']
            effort=int(est_minutes) if est_minutes else row['est_minutes']; pr=int(priority) if priority else row['priority']
            if not newtitle or len(newtitle)>200: raise ValueError("Title must contain 1 to 200 characters")
            if effort<max(1,row['done_minutes']): raise ValueError("Estimated effort cannot be below completed effort")
            if pr not in (1,2,3): raise ValueError("Priority must be 1, 2, or 3")
            c.execute("UPDATE tasks SET title=?,due_at=?,est_minutes=?,priority=? WHERE id=?",(newtitle,due,effort,pr,tid))
            return _result(c,"update_task",f"Updated task: {newtitle}")
    except (ValueError,TypeError) as e: return {"ok":False,"error":str(e)}
def get_schedule(date=""):
    _ensure()
    blocks=db.get_blocks()
    if date:
        try: day=parse_day(date)
        except ValueError as e: return {"ok":False,"error":str(e)}
        blocks=[b for b in blocks if b['start_at'][:10]==day]
    return {"ok":True,"blocks":blocks}
