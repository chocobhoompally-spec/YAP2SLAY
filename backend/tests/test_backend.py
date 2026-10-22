from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from backend import db, scheduler, tools
TZ=ZoneInfo('Asia/Kolkata')
@pytest.fixture(autouse=True)
def database(tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'test.sqlite3')); monkeypatch.setenv('TIMEZONE','Asia/Kolkata'); db.init()
    yield

def test_closer_deadline_prioritized():
    now=datetime(2030,1,1,8,tzinfo=TZ); slots=[now+timedelta(minutes=30*i) for i in range(4)]
    tasks=[scheduler.Task(1,'later',now+timedelta(days=2),30),scheduler.Task(2,'soon',now+timedelta(hours=2),30)]
    blocks,_=scheduler.build_schedule(tasks,slots,now); assert blocks[0][0]==2

def test_shortfall_reported():
    n=datetime(2030,1,1,8,tzinfo=TZ); blocks,short=scheduler.build_schedule([scheduler.Task(1,'x',n+timedelta(hours=1),120)], [n,n+timedelta(minutes=30)], n)
    assert len(blocks)==1 and blocks[0][2]-blocks[0][1]==timedelta(hours=1) and short=={1:60}

def test_max_run_switches_when_alternative():
    n=datetime(2030,1,1,8,tzinfo=TZ); tasks=[scheduler.Task(1,'a',n+timedelta(days=1),120,3),scheduler.Task(2,'b',n+timedelta(days=1),60,1)]
    blocks,_=scheduler.build_schedule(tasks,[n+timedelta(minutes=30*i) for i in range(6)],n)
    assert blocks[2][0] != blocks[1][0]

def test_no_overlap_and_past_excluded():
    n=datetime(2030,1,1,8,tzinfo=TZ); blocks,_=scheduler.build_schedule([scheduler.Task(1,'x',n+timedelta(days=1),60)], [n-timedelta(minutes=30),n,n+timedelta(minutes=30)],n)
    assert blocks[0][1]==n and blocks[0][2]-blocks[0][1]==timedelta(hours=1)

def test_db_persists_and_tool_replans():
    due=(datetime.now(TZ)+timedelta(days=2)).isoformat()
    assert tools.add_task('Essay',due,60)['ok']
    assert db.list_tasks()[0]['title']=='Essay'
    assert tools.set_available_time((datetime.now(TZ)+timedelta(days=1)).date().isoformat(),'09:00','11:00')['ok']
    assert db.get_blocks() and db.actions_since(0)

def test_invalid_time_and_failed_task_do_not_log_success():
    before=db.latest_action_id()
    assert not tools.set_available_time('nonsense','10:00','09:00')['ok']
    assert not tools.complete_task(987)['ok']
    assert db.latest_action_id()==before

def test_complete_frees_future_blocks():
    due=(datetime.now(TZ)+timedelta(days=2)).isoformat(); task=tools.add_task('Essay',due,60)
    day=(datetime.now(TZ)+timedelta(days=1)).date().isoformat(); tools.set_available_time(day,'09:00','11:00')
    assert db.get_blocks(); assert tools.complete_task(task['task_id'])['ok']; assert db.get_blocks()==[]

def test_lost_time_replans_and_reports_shortfall():
    due=(datetime.now(TZ)+timedelta(days=2)).isoformat(); tools.add_task('Study',due,180)
    day=(datetime.now(TZ)+timedelta(days=1)).date().isoformat(); tools.set_available_time(day,'09:00','11:00')
    result=tools.report_lost_time(60,day)
    assert result['ok'] and result['schedule']['unscheduled'][0]['remaining_minutes']==120
    assert len(db.get_blocks())==1 and db.get_blocks()[0]['start_at'].endswith('10:00:00+05:30')

def test_progress_updates_effort_and_replans():
    task=tools.add_task('Reading',(datetime.now(TZ)+timedelta(days=2)).isoformat(),90)
    result=tools.log_progress(task['task_id'],30)
    assert result['ok'] and db.list_tasks()[0]['done_minutes']==30
    assert db.actions_since(0)[-1]['tool']=='log_progress'

def test_assistant_missing_key_fallback(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    from backend import assistant
    result=assistant.send(assistant.new_chat(),'hello')
    assert 'not configured' in result['reply'].lower() and result['actions']==[]
