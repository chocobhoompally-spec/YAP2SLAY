"""Deterministic 30-minute-slot study scheduler; independent of Gemini and SQLite."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

SLOT = timedelta(minutes=30)
MAX_BLOCK = timedelta(minutes=90)
@dataclass(frozen=True)
class Task:
    id: int
    title: str
    due_at: datetime
    remaining: int
    priority: int = 2

def urgency(task: Task, slot_start: datetime, remaining: int | None = None) -> float:
    if task.due_at.tzinfo is None or slot_start.tzinfo is None:
        raise ValueError("Scheduler datetimes must be timezone-aware")
    hours=max((task.due_at-slot_start).total_seconds()/3600, 1/60)
    return task.priority * (task.remaining if remaining is None else remaining) / hours

def build_schedule(tasks: Iterable[Task], free_slots: Iterable[datetime], now: datetime | None = None):
    tasks=list(tasks)
    if len({t.id for t in tasks}) != len(tasks): raise ValueError("Task IDs must be unique")
    slots=list(free_slots)
    tz=tasks[0].due_at.tzinfo if tasks else (slots[0].tzinfo if slots else None)
    if now is None:
        now=datetime.min.replace(tzinfo=tz) if tz else None
    if now is not None and now.tzinfo is None: raise ValueError("now must be timezone-aware")
    for t in tasks:
        if t.due_at.tzinfo is None: raise ValueError("Task deadlines must be timezone-aware")
    for s in slots:
        if s.tzinfo is None: raise ValueError("Free slots must be timezone-aware")
    slots=sorted(set(s for s in slots if s >= now))
    rem={t.id:max(0,int(t.remaining)) for t in tasks}
    blocks=[]; last_id=None; run=timedelta(0)
    byid={t.id:t for t in tasks}
    for s in slots:
        eligible=[t for t in tasks if rem[t.id]>0 and t.due_at >= s+SLOT]
        if last_id is not None and run >= MAX_BLOCK:
            alternates=[t for t in eligible if t.id != last_id]
            if alternates: eligible=alternates
        if not eligible:
            last_id=None; run=timedelta(0); continue
        pick=max(eligible,key=lambda t:(urgency(t,s,rem[t.id]),t.priority,-t.due_at.timestamp(),-t.id))
        rem[pick.id]=max(0,rem[pick.id]-30)
        if blocks and blocks[-1][0]==pick.id and blocks[-1][2]==s and run < MAX_BLOCK:
            blocks[-1]=(pick.id,blocks[-1][1],s+SLOT); run+=SLOT
        else:
            blocks.append((pick.id,s,s+SLOT)); run=SLOT
        last_id=pick.id
    return blocks,{k:v for k,v in rem.items() if v>0}

def slots_from_availability(windows: Iterable[dict], tz, now: datetime) -> list[datetime]:
    slots=[]
    for w in windows:
        day=datetime.fromisoformat(w["date"]).date()
        start=datetime.strptime(w["start_time"],"%H:%M").time()
        end=datetime.strptime(w["end_time"],"%H:%M").time()
        cur=datetime.combine(day,start,tzinfo=tz); stop=datetime.combine(day,end,tzinfo=tz)
        while cur+SLOT<=stop:
            slots.append(cur); cur+=SLOT
    return [s for s in slots if s>=now]
