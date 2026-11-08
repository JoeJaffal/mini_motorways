"""Build engine variants with individual 75/77 rules disabled and replay reward-fixture-v4 on each."""
import json, pathlib, shutil, subprocess, sys

REPO = pathlib.Path(__file__).resolve().parents[4]
S = REPO / "tmp" / "variants"  # git-ignored scratch copies of the engine, one per variant
sys.path.insert(0, str(REPO / "training"))

ATTACH_OFF = ("void AttachNativeDrivewaysAt(Cell cell)\n        {\n            nativeJoinVersion=-1;",
              "void AttachNativeDrivewaysAt(Cell cell)\n        {\n            nativeJoinVersion=-1;return;")
JOIN_OFF = ("if(Rules.Version!=GameVersion.OriginalReference)return false;\n            if(nativeJoinVersion",
            "return false;\n            if(nativeJoinVersion")
DEDUP_OFF = ("if(!accesses.Add(access))continue;", "")
SPAWN_OFF = ("AttachNativeDrivewaysAt(outside);\n            Changed();\n            foreach", "Changed();\n            foreach")

EDITS = {
    "base": [],
    "noattach": [("NativeDriveways.cs", ATTACH_OFF)],
    "nojoin": [("NativeDriveways.cs", JOIN_OFF)],
    "nodedup": [("NativeDriveways.cs", DEDUP_OFF)],
    "noattach_nojoin": [("NativeDriveways.cs", ATTACH_OFF), ("NativeDriveways.cs", JOIN_OFF)],
    "spawnonly_off": [("CityDemand.cs", SPAWN_OFF)],
}


def build(name):
    target = S / name / "simulation"
    shutil.rmtree(S / name, ignore_errors=True)
    shutil.copytree(REPO / "simulation/Assets/Simulation", target / "Assets/Simulation")
    (target / "Headless").mkdir(parents=True)
    for f in ["Program.cs", "TrafficHost.csproj"]:
        shutil.copy(REPO / "simulation/Headless" / f, target / "Headless" / f)
    for fname, (old, new) in EDITS[name]:
        p = S / name / "simulation/Assets/Simulation" / fname
        t = p.read_text().replace("\r\n", "\n")
        assert t.count(old) == 1, (name, fname, old[:40])
        p.write_text(t.replace(old, new))
    r = subprocess.run(["dotnet", "build", str(S / name / "simulation/Headless"), "-c", "Debug", "-nologo", "-v", "q"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]
    return S / name / "simulation/Headless/bin/Debug/net8.0/TrafficHost.dll"


def replay(dll):
    import environment
    orig = environment.Host.__init__
    environment.Host.__init__ = lambda self, dotnet, dll_=None: orig(self, dotnet, dll)
    try:
        rec = json.loads((REPO / "docs/training/event-parity-2026-11-08/reward-fixture-v4.json").read_text())
        env = environment.TrafficEnv(seeds=[rec["seed"]]); env.reset(seed=42); first = None
        for i, ev in enumerate(rec["actions"]):
            req = {k: v for k, v in ev.items() if k in ["command", "tool", "x", "y", "toX", "toY", "id", "choice"]}
            if req["command"] == "wait": req = None
            a, r, t, tr, info = env._advance(req)
            if first is None and (ev["afterTrips"] != info["trips"] or bool(ev["accepted"]) != bool(info["accepted"])):
                first = (i, ev["afterTime"], ev["afterTrips"], info["trips"])
        out = dict(trips=info["trips"], terminated=bool(t), time=env.raw["time"], firstDivergence=first)
        env.close(); return out
    finally:
        environment.Host.__init__ = orig


if __name__ == "__main__":
    for name in (sys.argv[1:] or EDITS):
        print(name, replay(build(name)), flush=True)
