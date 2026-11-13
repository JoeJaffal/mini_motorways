"""Check parallel budgets, determinism, isolation, viewer events and host cleanup."""
from __future__ import annotations
import argparse
import copy
import random
import threading
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from alphazero import Edge, Network, Node, search
from actions import Candidate, _features
from environment import HOST_DLL, Host, TrafficEnv, SnapshotBranch, ReplayBranch
from parallel_search import SearchPool
from proposals import ActionGuard
from train import run_episode


def checks(dotnet, host_dll):
    torch.set_num_threads(1)
    torch.manual_seed(123)
    model = Network(value_scale=100)
    with Host(dotnet=dotnet,dll=host_dll) as live, Host(dotnet=dotnet,dll=host_dll) as other:
        env = TrafficEnv(live,cap_seconds=3.25)
        serial = SnapshotBranch(other,env)
        plain = run_episode(env,serial,"DarEsSalaam",200000,model,8,random.Random(91),False,
                            collect_samples=False,progress_every=0)
        with SearchPool(serial,1) as pool:
            single = run_episode(env,pool,"DarEsSalaam",200000,model,8,random.Random(91),False,
                                 collect_samples=False,progress_every=0)
        assert plain[2] == single[2], "One worker changed serial search"
        for kind in (SnapshotBranch,ReplayBranch):
            pids=[]
            with SearchPool(kind(other,env),3) as pool:
                pids=[branch.env.host.process for branch in pool.branches[1:]]
                assert len({branch.env.host.process.pid for branch in pool.branches}) == 3
                barrier=threading.Barrier(3)
                def together():
                    barrier.wait(timeout=5)
                    return threading.get_ident()
                assert len(set(pool.run([(together,()) for _ in range(3)]))) == 3
                root=env.reset("DarEsSalaam",200000)
                original=copy.deepcopy(root)
                pool.start(root)
                guard=ActionGuard()
                history=[]
                def probe(budget, observer=None):
                    return search(model,env,pool,history,budget,4,random.Random(555),discount=.999,
                                  guard=guard,observer=observer)
                for budget in (1,2,7,8,16):
                    items,visits,stats=probe(budget)
                    assert visits.sum() == budget and stats["rolloutsCompleted"] == budget
                    assert stats["expandedOutcomes"] <= budget and stats["maxDepthReached"] <= 4
                    assert stats["simulatorTransitions"] <= budget*4
                    assert stats["rootComparisonActionsVisited"] == stats["rootComparisonActions"]
                    assert sum(row["visits"] for row in stats["rootActionStats"]) == budget
                    repeated=probe(budget)
                    assert items == repeated[0] and np.array_equal(visits,repeated[1])
                    assert stats == repeated[2], "Completion order changed results"
                events=[]
                before=probe(8)
                observed=probe(8,lambda *a,**kw:events.append((threading.get_ident(),a,kw)))
                assert np.array_equal(before[1],observed[1]) and before[2] == observed[2]
                assert events and all(event[0] == threading.get_ident() for event in events)
                assert {event[2]["simulation"] for event in events} == set(range(1,9))
                assert live.call(command="observe")["observation"] == original
                assert guard.driveways == {} and guard.rejected == {}
                # One option can fill both pending slots before a batch is full.
                # Finish a smaller wave rather than stalling or losing rollouts.
                def only_wait(model, observation, terminal=False, guard=None, host=None, truncated=False):
                    ended=terminal or truncated
                    return Node(observation,[] if ended else [Candidate({"command":"wait"},"wait",_features(0))],
                                .25,[] if ended else [Edge(1.0)],ended,guard)
                with patch("alphazero.make_node",side_effect=only_wait):
                    _,visits,stats=probe(17)
                    assert visits.tolist() == [17] and stats["rolloutsCompleted"] == 17
                    assert stats["maxDepthReached"] <= 4
                # Failed work is drained before another search or model update can start.
                with patch.object(pool.branches[0],"transition",side_effect=RuntimeError("injected worker failure")):
                    try:
                        probe(8)
                    except RuntimeError as exc:
                        assert "injected worker failure" in str(exc)
                    else:
                        raise AssertionError("Worker failure was swallowed")
                probe(8)
                outcome=env.step(items[0].request)
                pool.commit(items[0].request,outcome.observation)
                history.append(items[0].request)
                probe(8)
            assert all(process.poll() is not None for process in pids), "Extra host leaked"
        with SearchPool(SnapshotBranch(other,env),3) as pool:
            _,result,trace=run_episode(env,pool,"DarEsSalaam",200000,model,8,random.Random(91),False,
                                    collect_samples=False,progress_every=0)
            assert result["time"] == 3.25 and result["truncated"] and not result["terminated"]
            assert len(trace["actions"]) == 4
            assert all(action["search"]["rolloutsCompleted"] == 8 for action in trace["actions"])
    print("PASS: serial parity, actual thread overlap, fixed budgets, deterministic parallel search, "
          "snapshots/replay, live/guard isolation, callbacks, failure recovery, fractional cutoff, cleanup")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet",default="dotnet")
    parser.add_argument("--host-dll",type=Path,default=HOST_DLL)
    args=parser.parse_args()
    checks(args.dotnet,args.host_dll)
