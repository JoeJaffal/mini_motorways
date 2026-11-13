"""Local, read-only traffic inspection, shared by training and checkpoint runs.

The viewer consumes observations from the existing hosts. It never sends game
commands, calls the model, or consumes the agent's random stream.
"""
from __future__ import annotations

from collections import deque
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
import time

TEMPLATE = Path(__file__).with_name("viewer.html")
STATE_FIELDS = ("width", "height", "time", "terrain", "infrastructure", "connections",
                "pendingRemovals", "inventory", "tripsCompleted", "tripsDispatched",
                "failed", "playableXMin", "playableXMax", "playableYMin", "playableYMax",
                "motorways", "railLines", "trains", "signals", "closedRailCrossings")
BUILDING_FIELDS = ("id", "color", "cell", "entrance", "entrances", "width", "height",
                   "isHouse", "demand", "reserved", "demandCapacity", "overcrowdedFor",
                   "drivewayDirection", "isStation")
VEHICLE_FIELDS = ("id", "color", "x", "y", "headingX", "headingY", "waiting",
                  "stage", "homeId", "shopId", "obstacle", "speed")


def compact(observation):
    state = {key: observation[key] for key in STATE_FIELDS if key in observation}
    state["buildings"] = [{k: b[k] for k in BUILDING_FIELDS if k in b}
                          for b in observation["buildings"]]
    state["vehicles"] = [{k: v[k] for k in VEHICLE_FIELDS if k in v}
                         for v in observation["vehicles"] if v["stage"] != "Home"]
    return state


class LiveViewer:
    def __init__(self, port=8765, delay=0.1, search_delay=0.1, show_search=False):
        self.delay, self.search_delay, self.show_search = delay, search_delay, show_search
        self.paused = False
        self.lock = threading.Lock()
        self.events = deque(maxlen=512)
        self.seq = 0
        self.session = {"meta":{}, "main":[], "search":[], "status":"Waiting for an episode"}
        self.search_frames = deque(maxlen=512)
        self.server = None
        self.thread = None
        self.port = port

    def __enter__(self):
        viewer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send(self, value, mime="application/json", code=200):
                body = value.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", mime+"; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                from urllib.parse import urlsplit, parse_qs
                url = urlsplit(self.path)
                if url.path == "/":
                    self.send(TEMPLATE.read_text(encoding="utf-8").replace("__SESSION_DATA__", "null"), "text/html")
                elif url.path == "/api/events":
                    try:
                        after = int(parse_qs(url.query).get("after", ["-1"])[0])
                    except ValueError:
                        self.send('{"error":"Invalid cursor"}', code=400)
                        return
                    with viewer.lock:
                        payload = {"seq":viewer.seq, "paused":viewer.paused,
                                   "delay":viewer.delay, "searchDelay":viewer.search_delay,
                                   "status":viewer.session["status"]}
                        if after < 0 or (viewer.events and after < viewer.events[0]["seq"]-1):
                            payload["session"] = viewer.snapshot_unlocked()
                        else:
                            payload["events"] = [event for event in viewer.events if event["seq"] > after]
                        body = json.dumps(payload, separators=(",", ":"), allow_nan=False)
                    self.send(body)
                else:
                    self.send('{"error":"Not found"}', code=404)

            def do_POST(self):
                # Browser controls affect presentation pacing only, never gameplay.
                # Accept same-origin JSON; reject form posts and cross-origin scripts.
                origin = self.headers.get("Origin")
                if (self.path != "/api/control" or self.headers.get("Content-Type") != "application/json"
                        or (origin and origin != "http://"+self.headers.get("Host", ""))):
                    self.send('{"error":"Unsupported request"}', code=403)
                    return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 1024:
                        raise ValueError("Invalid request size")
                    control = json.loads(self.rfile.read(size))
                    with viewer.lock:
                        if "paused" in control:
                            viewer.paused = bool(control["paused"])
                        for key, attr in (("delay", "delay"), ("searchDelay", "search_delay")):
                            if key in control:
                                value = float(control[key])
                                if not 0 <= value <= 5:
                                    raise ValueError("Delay must be between 0 and 5 seconds")
                                setattr(viewer, attr, value)
                    self.send('{"ok":true}')
                except (ValueError, TypeError, json.JSONDecodeError):
                    self.send('{"error":"Invalid control"}', code=400)

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Live viewer: http://127.0.0.1:{self.port} "
              f"({'main run + MCTS rollouts' if self.show_search else 'main run only'}); Ctrl+C stops the command.", flush=True)
        return self

    def snapshot_unlocked(self):
        return {**self.session, "search":list(self.search_frames)}

    def __call__(self, kind, observation, **details):
        if kind == "search" and not self.show_search:
            return
        state = compact(observation)
        with self.lock:
            if kind == "reset":
                details = {**details, "runId":str(time.time_ns())}
                self.session = {"meta":details, "main":[], "search":[], "status":"Running"}
                self.search_frames.clear()
                event = {"kind":"reset", "meta":details, "state":state}
                self.session["main"].append({"state":state, "decision":None})
            elif kind == "main":
                event = {"kind":"main", "state":state, **details}
                self.session["main"].append({"state":state, **details})
            elif kind == "search":
                event = {"kind":"search", "state":state,
                         "decisionIndex":len(self.session["main"])-1, **details}
                self.search_frames.append(event)
            elif kind == "finish":
                self.session["status"] = "Finished"
                self.session["result"] = details["result"]
                event = {"kind":"finish", **details}
            else:
                raise ValueError(f"Unknown viewer event {kind}")
            self.seq += 1
            self.events.append({"seq":self.seq, **event})
        if kind in ("main", "search", "reset"):
            self.publish(event)
            self._pace(self.search_delay if kind == "search" else self.delay)
        elif kind == "finish":
            self.publish(event)

    def publish(self, event):
        pass

    def _pace(self, delay):
        until = time.monotonic() + delay
        while True:
            with self.lock:
                paused = self.paused
            if not paused and time.monotonic() >= until:
                break
            time.sleep(.025)

    def save(self, path):
        with self.lock:
            payload = json.dumps(self.snapshot_unlocked(), separators=(",", ":"), allow_nan=False)
        # Prevent recorded strings from terminating the embedded JSON script.
        payload = payload.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__SESSION_DATA__", payload), encoding="utf-8")
        path.with_suffix(".session.json").write_text(payload, encoding="utf-8")

    def __exit__(self, *_):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)


UNITY_PLAYER = Path(__file__).resolve().parents[1]/"simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe"


class UnityLiveViewer(LiveViewer):
    """Send observed states to the project's Unity renderer via atomic packets."""
    def __init__(self, executable=UNITY_PLAYER, directory=None, **kwargs):
        super().__init__(**kwargs)
        self.executable = Path(executable)
        root = Path(__file__).resolve().parents[1]
        self.directory = Path(directory or root/"output/mbrl/live"/str(time.time_ns())).resolve()
        self.player = None
        self.last_control = ""
        self.skipped_frames = 0

    def __enter__(self):
        if not self.executable.is_file():
            raise FileNotFoundError(f"Unity player missing: {self.executable}. Build Original with "
                                   "ProjectSetup.BuildOriginalWindows, or supply --unity-exe.")
        self.directory.mkdir(parents=True,exist_ok=True)
        token = str(time.time_ns())
        self.player = subprocess.Popen([str(self.executable.resolve()),"--model-live",str(self.directory),
                                       "--model-token",token,
                                       "-screen-fullscreen","0","-logFile",str(self.directory/"unity.log")])
        until = time.monotonic()+20
        while time.monotonic()<until:
            try:
                if (self.directory/"ready.txt").read_text(encoding="utf-8-sig").strip()==token:
                    break
            except OSError:
                pass
            if self.player.poll() is not None:
                raise RuntimeError(f"Unity viewer exited during startup. See {self.directory/'unity.log'}")
            time.sleep(.1)
        else:
            raise RuntimeError("Unity player did not acknowledge live viewing. Rebuild the Original app "
                               f"with ModelLiveViewer.cs; see {self.directory/'unity.log'}")
        print(f"Unity model viewer launched. Live observation files: {self.directory}",flush=True)
        return self

    def publish(self, event):
        self.directory.mkdir(parents=True,exist_ok=True)
        with self.lock:
            packet = {**event,"meta":self.session["meta"],"status":self.session["status"],"seq":self.seq,
                      "decisionIndex":event.get("decisionIndex",max(0,len(self.session["main"])-2))}
            if "state" not in packet and self.session["main"]:
                packet.update(self.session["main"][-1])
            body = json.dumps(packet,separators=(",",":"),allow_nan=False)
        target = self.directory/("search.json" if event["kind"]=="search" else "main.json")
        temporary = target.with_suffix(".tmp")
        # Windows can briefly lock a replaced file (including during virus scans).
        # Presentation I/O must never abort a model run. Retain the event in the
        # session archive and let the next callback publish a newer live packet.
        for attempt in range(8):
            try:
                temporary.write_text(body,encoding="utf-8")
                temporary.replace(target)
                return
            except PermissionError:
                time.sleep(.005*(attempt+1))
        self.skipped_frames += 1
        if self.skipped_frames == 1:
            print(f"Unity live frame temporarily locked by Windows: {target}. "
                  "Continuing the run; all observations remain in the archive.",flush=True)

    def _pace(self, delay):
        until = time.monotonic()+delay
        while True:
            if self.player is not None and self.player.poll() is not None:
                self.paused = False
                break
            control_file = self.directory/"control.json"
            try:
                control_text = control_file.read_text(encoding="utf-8")
                if control_text != self.last_control:
                    control = json.loads(control_text)
                    self.paused = bool(control.get("paused",False))
                    for key,attr in (("delay","delay"),("searchDelay","search_delay")):
                        value = float(control.get(key,getattr(self,attr)))
                        if math.isfinite(value) and 0<=value<=5:
                            setattr(self,attr,value)
                    self.last_control = control_text
            except (OSError,ValueError,TypeError):
                pass
            if not self.paused and time.monotonic()>=until:
                break
            time.sleep(.025)

    def __exit__(self, *_):
        # Leave the read-only window open at its final observed state.
        if self.session["main"]:
            self.save(self.directory/"run.html")


def add_viewer_arguments(parser):
    parser.add_argument("--live", action="store_true", help="Watch the existing headless simulator in Unity (or --viewer browser)")
    parser.add_argument("--view-mcts", action="store_true", help="Also stream hypothetical MCTS rollouts (requires --live)")
    parser.add_argument("--viewer", choices=("unity","browser"), default="unity", help="Live rendering backend (default: existing Unity app)")
    parser.add_argument("--unity-exe", type=Path, default=UNITY_PLAYER, help="Path to the built Traffic Lab Original app")
    parser.add_argument("--viewer-port", type=int, default=8765, help="Local viewer port; zero chooses a free port")
    parser.add_argument("--view-delay", type=float, default=.1, help="Seconds to display each real decision")
    parser.add_argument("--search-view-delay", type=float, default=.1, help="Seconds to display each MCTS node")


def viewer_context(args):
    from contextlib import nullcontext
    if not 0 <= args.viewer_port <= 65535 or any(not math.isfinite(v) or not 0 <= v <= 5
                                               for v in (args.view_delay,args.search_view_delay)):
        raise ValueError("Invalid viewer port or delay (expected 0 to 5 seconds)")
    if args.view_mcts and not args.live:
        raise ValueError("--view-mcts requires --live")
    if not args.live:
        return nullcontext(None)
    if args.viewer == "unity":
        return UnityLiveViewer(executable=args.unity_exe,delay=args.view_delay,
                               search_delay=args.search_view_delay,show_search=args.view_mcts)
    return LiveViewer(args.viewer_port,args.view_delay,args.search_view_delay,args.view_mcts)
