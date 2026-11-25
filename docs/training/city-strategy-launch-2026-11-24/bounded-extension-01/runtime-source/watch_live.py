"""One random frozen-policy game streamed to a local browser; no training."""
import argparse
import json
from pathlib import Path
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from sb3_contrib import MaskablePPO
from environment import ROOT
from train_goal import model_environment


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,default=ROOT/'output/training/upgrades-night-01/validation-best.zip')
    p.add_argument('--seed',type=int,help='Omit for one random seed; no score-based filtering')
    p.add_argument('--speed',type=float,default=4,help='Simulated seconds per wall second, excluding inference cost')
    p.add_argument('--smoke',action='store_true',help='Two simulated seconds; no browser; exit automatically')
    a=p.parse_args()
    if not 0<a.speed<=1000:p.error('Speed must be >0 and <=1000')
    seed=a.seed if a.seed is not None else secrets.randbelow(1000000000)
    out=ROOT/'output/live'/f'{time.strftime("%Y%m%d-%H%M%S")}-{seed}'
    out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2)
    model=MaskablePPO.load(a.checkpoint,device='cpu')
    initial=[v.detach().clone() for v in model.policy.parameters()]
    stop=threading.Event();play=threading.Event()
    shared={'seed':seed,'status':'Loading; press Play','data':None}
    lock=threading.Lock()
    if a.smoke:play.set()

    def worker():
        env=None
        try:
            env=model_environment(model,seconds=2 if a.smoke else 3600,dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),
                                  skip_forced_wait=getattr(model,'skip_forced_wait',False))
            def publish():
                raw=env.base.raw
                data={k:raw[k] for k in ['time','tripsCompleted','inventory','buildings','vehicles','signals']}
                data.update({k:v.tolist() for k,v in env.base.arrays.items()})
                with lock:shared['data']=data
            obs,_=env.reset(seed=seed,options={'scenario_seed':seed});publish()
            original=env.base._advance
            def advance(request=None):
                while not play.wait(.1):
                    if stop.is_set():raise InterruptedError()
                if stop.is_set():raise InterruptedError()
                result=original(request);publish()
                stop.wait(0 if a.smoke else 1/a.speed)
                return result
            env.base._advance=advance
            while not stop.is_set():
                while not play.wait(.1):
                    if stop.is_set():raise InterruptedError()
                action=int(model.predict(obs,deterministic=True,action_masks=env.action_masks())[0])
                obs,_,term,trunc,info=env.step(action)
                if term or trunc:break
            if stop.is_set():raise InterruptedError()
            assert all(torch.equal(x,y) for x,y in zip(initial,model.policy.parameters()))
            replay=env.export_replay();replay['source']='hybrid-live-demonstration'
            (out/'game.json').write_text(json.dumps(replay,indent=2)+'\n',encoding='utf-8')
            with lock:shared['status']=f'Finished: {info["trips"]} trips. Replay saved.'
            print(f'GAME COMPLETE | seed {seed} | {info["trips"]} trips | {out}',flush=True)
        except InterruptedError:
            with lock:shared['status']='Stopped'
        except Exception as exc:
            with lock:shared['status']=f'Error: {exc}'
            print(f'LIVE ERROR: {exc}',flush=True)
        finally:
            if env is not None:env.close()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path=='/state':
                with lock:body=json.dumps(shared).encode()
                kind='application/json'
            elif self.path=='/':
                body=(ROOT/'training/live_view.html').read_bytes();kind='text/html; charset=utf-8'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind)
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.path=='/play':play.set()
            elif self.path=='/pause':play.clear()
            else:self.send_error(404);return
            self.send_response(204);self.end_headers()

    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=worker);thread.start()
    print(f'LIVE | seed {seed} | checkpoint {a.checkpoint} | no training',flush=True)
    try:
        if a.smoke:
            thread.join()
            if not (out/'game.json').exists():raise RuntimeError('Smoke did not complete')
        else:
            url=f'http://127.0.0.1:{server.server_port}/'
            print(f'{url} | Play/Pause in browser. Ctrl+C stops server.',flush=True)
            webbrowser.open(url)
            server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        stop.set();play.set();server.server_close();thread.join(timeout=10)


if __name__=='__main__':main()
