"""Export the recovery experiment's completed measurements without assuming unfinished stages succeeded."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean


def load(path,default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    args=parser.parse_args()
    root=args.run
    status=load(root/"pipeline-status.json",{"stage":"unknown"})
    controls=load(root/"baseline-comparison.json",[])
    summary={"pipeline":status,"oldControls":[{key:r[key] for key in
        ("checkpoint","mode","meanTrips","meanWaiting","meanCost")} for r in controls],
        "lossComparison":load(root/"loss-ablation-v2/results.json"),
        "generatorComparison":load(root/"generator-ablation.json"),
        "budgetComparison":load(root/"budget-sweep.json"),
        "selection":load(root/"final-selection.json"),"test":load(root/"final-test.json")}
    rows=[]
    controlled=root/"controlled-v3"
    for name in ("training.jsonl","validation.jsonl","baseline-validation.jsonl"):
        path=controlled/name
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                row=json.loads(line)
                row.update(row.pop("optimizer",{}))
                rows.append(row)
    columns=("phase","episode","checkpointEpisode","mode","map","seed","time","trips",
        "waitingSeconds","modificationCost","invalidActions","reversals","drivewayChanges",
        "motorwayChanges","meanSearchDepthReached","wallSeconds","policyLoss","valueLoss",
        "policyEncoderGradient","valueEncoderGradient","gradientCosine","valueRMSE")
    with (root/"learning-metrics.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)
    summary["completedTrainingEpisodes"]=sum(r.get("phase")=="train" for r in rows)
    (root/"experiment-summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    text=["# Recovery experiment measurements","",f"Pipeline stage: **{status['stage']}**.",
          f"Completed controlled training episodes: **{summary['completedTrainingEpisodes']}**.","",
          "## Old checkpoints on fixed validation seeds","",
          "| Checkpoint | Mode | Mean completed trips |","| --- | --- | ---: |"]
    for row in summary["oldControls"]:
        text.append(f"| {row['checkpoint']} | {row['mode']} | {row['meanTrips']:.1f} |")
    text += ["","Original heuristic reference: **58 mean trips**.","",
             "## Current generator and loss-model controls","",
             "| Policy | Mean trips | Waiting seconds/trip | Modification units/trip | Rejected | Reversals |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    groups=[]
    generator=summary["generatorComparison"]
    if generator:
        for budget in (-1,-2):
            subset=[r for r in generator["rows"] if r["simulations"]==budget]
            groups.append(("Current-generator heuristic" if budget==-1 else "Guarded heuristic",subset))
    for loss in ("mse","huber"):
        result=load(root/f"value-policy-{loss}.json")
        if result:groups.append((f"Normalized {loss} policy",result["rows"]))
    for name,subset in groups:
        trips=sum(r["trips"] for r in subset)
        text.append(f"| {name} | {mean(r['trips'] for r in subset):.1f} | "
                    f"{sum(r['waitingSeconds'] for r in subset)/max(1,trips):.2f} | "
                    f"{sum(r['modificationCost'] for r in subset)/max(1,trips):.2f} | "
                    f"{sum(r['invalidActions'] for r in subset)} | {sum(r['reversals'] for r in subset)} |")
    budgets=summary["budgetComparison"]
    if budgets:
        text += ["","## Fixed-model search budgets","",
                 "Common simulated horizon: 300 seconds. Wall times include the recorded background workload.","",
                 "| Simulations | Mean trips | Mean reached depth | Mean wall seconds | Rejected | Reversals |",
                 "| ---: | ---: | ---: | ---: | ---: | ---: |"]
        for result in budgets["results"]:
            text.append(f"| {result['simulations']} | {result['rank'][0]:.1f} | {result['meanDepth']:.2f} | "
                        f"{result['meanWallSeconds']:.1f} | {result['rejected']} | {result['reversals']} |")
    if summary["selection"]:
        selected=summary["selection"]["best"]
        text += ["","## Locked selection","",f"{selected['name']}, {selected['simulations']} search simulations, "
                 f"validation mean {selected['rank'][0]:.1f} trips."]
    if summary["test"]:
        text += ["","## Held-out London test","",
                 "| Mode | Mean completed trips | Mean wall seconds | Rejected | Reversals |",
                 "| --- | ---: | ---: | ---: | ---: |"]
        for result in summary["test"]["results"]:
            text.append(f"| {result['simulations']} | {result['rank'][0]:.1f} | {result['meanWallSeconds']:.1f} | "
                        f"{result['rejected']} | {result['reversals']} |")
    text += ["","All development comparisons use only two Dar es Salaam seeds. "
             "Unfinished stages are not evidence of success. Final test scores do not select checkpoints.",""]
    (root/"EXPERIMENT_REPORT.md").write_text("\n".join(text),encoding="utf-8")
    print(root/"EXPERIMENT_REPORT.md")


if __name__=="__main__":main()
