#!/usr/bin/env python3
"""Opt-in authenticated Runtime Guard cancellation/recovery observations.

Adapted from Outbound Guard client_cancellation_probe.py at
f5aaf302ec756c02bddb8c7246ba3c9aef4eeed5 (GPL-3.0-or-later).
Run one account-backed probe at a time; existing authentication and model usage
are required. No VM, namespace, sudo, external target or runtime dependency.
"""
from client_probe_diagnostics import classify_limit
import sys,os,json,pathlib,subprocess,tempfile,time,threading,queue,shutil,hashlib,atexit,signal
assert len(sys.argv)==3 and sys.argv[1] in ('claude','codex','cursor'), 'usage: client_cancellation_probe.py claude|codex|cursor INSTALLED_PYTHON'
binary=str(pathlib.Path(sys.argv[2]).absolute())
assert pathlib.Path(binary).is_file(), 'installed Python executable is missing'
script_dir=pathlib.Path(__file__).resolve().parent
root=pathlib.Path(tempfile.mkdtemp(prefix='runtime-guard-cancel-'));root.chmod(0o700)
p = None
watchdog = None
cleaned = False
def cleanup():
 global cleaned
 if cleaned:return
 cleaned=True
 if watchdog is not None:watchdog.cancel()
 if p is not None:
  try:os.killpg(p.pid, signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid, signal.SIGKILL);p.wait(timeout=5)
 shutil.rmtree(root)
atexit.register(cleanup)
bridge=[str(script_dir/'client_cancellation_bridge.py'),binary,str(root)]
config=root/'mcp.json';config.write_text(json.dumps({'mcpServers':{'runtime_guard':{'command':'python3','args':bridge}}}))
(root/'.cursor').mkdir()
(root/'.cursor/mcp.json').write_text(config.read_text())
prompt='Use ONLY the runtime_guard dry_run_command MCP tool exactly once with command git status. This is text inspection; do not execute a shell or use any other tools. Wait for its actual result.'
clienthome=root/'codex';clienthome.mkdir(mode=0o700)
auth=pathlib.Path.home()/'.codex/auth.json'
if auth.exists():(clienthome/'auth.json').symlink_to(auth)
(clienthome/'config.toml').write_text('approval_policy="never"\nsandbox_mode="read-only"\n[mcp_servers.runtime_guard]\ncommand="python3"\nargs='+json.dumps(bridge)+'\nenabled_tools=["dry_run_command"]\nrequired=true\n[mcp_servers.runtime_guard.tools.dry_run_command]\napproval_mode="approve"\n')
name=sys.argv[1]
cmd=['claude','-p','--restricted','--strict-mcp-config','--mcp-config',str(config),'--allowedTools','mcp__runtime_guard__dry_run_command','--tools','','--permission-mode','dontAsk','--no-session-persistence','--output-format','stream-json','--input-format','stream-json','--verbose'] if name=='claude' else ([str(pathlib.Path.home()/'.local/bin/agent'),'--approve-mcps','--trust','acp'] if name=='cursor' else ['codex','app-server','--listen','stdio://'])
env=os.environ.copy()
if name=='codex':env['CODEX_HOME']=str(clienthome)
p=subprocess.Popen(cmd,cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(root/'client.stderr','w'),text=True,bufsize=1,start_new_session=True)
def expire():
 try:os.killpg(p.pid, signal.SIGTERM)
 except ProcessLookupError:pass
watchdog=threading.Timer(150,expire);watchdog.daemon=True;watchdog.start()
q=queue.Queue(maxsize=1024)
def read():
 for line in p.stdout:
  with open(root/'client.jsonl','a') as f:f.write(line)
  try:
   message=json.loads(line)
   if message.get('method')=='session/request_permission':
    params=message['params'];allowed='dry_run_command' in params['toolCall'].get('title','')
    kind='allow_once' if allowed else 'reject_once'
    option=next(x for x in params['options'] if x['kind']==kind)
    send({'jsonrpc':'2.0','id':message['id'],'result':{'outcome':{'outcome':'selected','optionId':option['optionId']}}})
   else:q.put_nowait(message)
  except ValueError:pass
send_lock=threading.Lock()
def send(m):
 with send_lock:
  p.stdin.write(json.dumps(m)+'\n');p.stdin.flush()
threading.Thread(target=read,daemon=True).start()
def response(id_):
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  try:m=q.get(timeout=max(.01,deadline-time.monotonic()))
  except queue.Empty:break
  if m.get('id')==id_ and 'method' not in m:
   assert 'result' in m, 'client returned a control API error'
   return m['result']
 raise AssertionError('client control API response deadline exceeded')
try:
 if name=='claude':send({'type':'user','message':{'role':'user','content':prompt}})
 elif name=='cursor':
  send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':1,'clientCapabilities':{}}});response(1)
  send({'jsonrpc':'2.0','id':2,'method':'session/new','params':{'cwd':str(root),'mcpServers':[{'name':'runtime_guard','command':'python3','args':bridge,'env':[]}]}});sid=response(2)['sessionId']
  send({'jsonrpc':'2.0','id':3,'method':'session/prompt','params':{'sessionId':sid,'prompt':[{'type':'text','text':prompt}]}})
 else:
  send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'runtime_cancel_probe','version':'1'}}});response(1)
  send({'method':'initialized','params':{}})
  send({'id':2,'method':'thread/start','params':{'cwd':str(root),'approvalPolicy':'never','sandbox':'read-only','ephemeral':True}})
  tid=response(2)['thread']['id']
  send({'id':3,'method':'turn/start','params':{'threadId':tid,'input':[{'type':'text','text':prompt}]}})
  turn=response(3)['turn']['id']
 start=time.monotonic()
 while not (root/'started').exists():
  assert p.poll() is None,'client exited'
  assert time.monotonic()-start<80,'fixture never started'
  time.sleep(.01)
 stop=time.monotonic()
 if name=='claude':send({'type':'control_request','request_id':'interrupt-probe','request':{'subtype':'interrupt'}})
 elif name=='cursor':send({'jsonrpc':'2.0','method':'session/cancel','params':{'sessionId':sid}})
 else:
  send({'id':4,'method':'turn/interrupt','params':{'threadId':tid,'turnId':turn}});response(4)
 time.sleep(0.3)
 (root/'release').touch()
 deadline=time.monotonic()+6
 while not (root/'policy_finished').exists() and time.monotonic()<deadline:time.sleep(.01)
 assert (root/'policy_finished').exists(), 'fixture did not finish'
 finished_after=round(time.monotonic()-stop,3)
 time.sleep(.2)
 if name=='codex':
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   messages=[json.loads(line) for line in (root/'client.jsonl').read_text().rsplit('\n',1)[0].splitlines()]
   if any(m.get('method')=='turn/completed' and m.get('params',{}).get('turn',{}).get('id')==turn for m in messages):break
   time.sleep(.02)
 recovery='Use ONLY runtime_guard dry_run_command exactly once with command git status. Do not execute it. Report its actual status/rule; no other tools or retries.'
 if name=='claude':send({'type':'user','message':{'role':'user','content':recovery}})
 elif name=='cursor':
  response(3)
  send({'jsonrpc':'2.0','id':5,'method':'session/prompt','params':{'sessionId':sid,'prompt':[{'type':'text','text':recovery}]}})
 else:
  send({'id':5,'method':'turn/start','params':{'threadId':tid,'input':[{'type':'text','text':recovery}]}});response(5)
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  lines=(root/'wire.jsonl').read_text().splitlines()
  if len([json.loads(line) for line in lines if json.loads(line).get('method')=='tools/call']) >= 2 and any(json.loads(line).get('rule')=='READ_ONLY_COMMAND' for line in lines[1:]):
   events_now=[json.loads(line) for line in lines]; calls_now=[e for e in events_now if e.get('method')=='tools/call']
   if any(e['direction']=='out' and e.get('id')==calls_now[-1]['id'] and e.get('rule')=='READ_ONLY_COMMAND' for e in events_now):break
  time.sleep(.02)
 events=[json.loads(s) for s in (root/'wire.jsonl').read_text().splitlines()]
 cancels=[e for e in events if e.get('method')=='notifications/cancelled']
 fetches=[e for e in events if e.get('method')=='tools/call']
 matching=bool(cancels and cancels[0]['requestId']==fetches[0]['id'])
 cancelled_reply=any(e['direction']=='out' and e.get('id')==fetches[0]['id'] for e in events)
 if matching:assert not cancelled_reply, 'server replied after matching cancellation'
 if not any(e.get('rule')=='READ_ONLY_COMMAND' and e.get('id')==fetches[-1]['id'] for e in events):
  errors=[m.get('params',{}).get('error',{}).get('codexErrorInfo') for m in [json.loads(line) for line in (root/'client.jsonl').read_text().splitlines()] if m.get('method')=='error']
  print(json.dumps({'client_error_classes':errors}),flush=True)
 assert len(fetches)==2 and any(e.get('rule')=='READ_ONLY_COMMAND' and e.get('id')==fetches[-1]['id'] for e in events), 'recovery did not succeed'
 assert p.poll() is None
 assert len([e for e in events if e.get('method')=='fixture_started'])==1, 'client restarted the fixture process'
 messages=[json.loads(line) for line in (root/'client.jsonl').read_text().rsplit('\n',1)[0].splitlines()]
 if name=='claude':
  control_ack=any(m.get('type')=='control_response' and m.get('response',{}).get('request_id')=='interrupt-probe' and m['response'].get('subtype')=='success' for m in messages)
 elif name=='codex':
  control_ack=any(m.get('method')=='turn/completed' and m.get('params',{}).get('turn',{}).get('id')==turn and m['params']['turn'].get('status')=='interrupted' for m in messages)
 else:
  control_ack=any(m.get('id')==3 and m.get('result',{}).get('stopReason')=='cancelled' for m in messages)
 assert control_ack, 'client did not acknowledge interruption'
 import sqlite3
 with sqlite3.connect(root/'audit.sqlite') as database:
  audit=database.execute('SELECT tool,status,rule FROM decisions ORDER BY rowid').fetchall()
 assert audit==[('dry_run_command','SAFE','READ_ONLY_COMMAND')]*2, 'audit did not preserve both completed policy checks'
 report={'status':'PASS_OBSERVATION','client':name,'client_version':subprocess.check_output([cmd[0],'--version'],text=True,timeout=10).strip(),
         'control_path':{'claude':'stream-json interrupt','codex':'app-server turn/interrupt','cursor':'ACP session/cancel'}[name],
         'live_client':True,'client_control_acknowledged':control_ack,'matching_wire_cancellation':matching,
         'cancelled_call_replied':cancelled_reply,'cancel_notifications':len(cancels),
         'tool_calls':len(fetches),'fixture_processes':1,'protocol_versions':sorted({e['protocol_version'] for e in events if 'protocol_version' in e}),'policy_finished_after_seconds':finished_after,
         'recovery_safe':True,'audit_decisions':len(audit),
         'scope':'real client control API; installed dispatcher/policy with test-only delayed first call; not desktop/terminal UI, preemption or saturated queue'}
 print(json.dumps(report),flush=True)
except (AssertionError, subprocess.TimeoutExpired, queue.Empty):
 text='\n'.join(path.read_text(errors='replace') for path in (root/'client.jsonl', root/'client.stderr') if path.exists())
 limit_class=classify_limit(text)
 print(json.dumps({'status':'INCONCLUSIVE','client':name,'limit_indicator':limit_class,'reason':'client control/fixture/recovery did not complete; no passing cancellation claim'}),flush=True)
 raise SystemExit(2)
finally:
 cleanup()
