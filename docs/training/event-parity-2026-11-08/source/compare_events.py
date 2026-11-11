"""Observed-event mismatch gate; passing would not certify unobserved original state."""
import json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
data=json.loads((root/'measurements/first-three-deliveries.json').read_text(encoding='utf-8'));rows=[]
for event in data['observations']:
 lo,hi=event['estimatedGameInterval'];at=event['simulationFactorAndAverage'];rows.append(dict(delivery=event['score'],originalEstimatedInterval=[lo,hi],simulation=at,consistentWithinOneTick=lo-.05<=at<=hi+.05))
result=dict(status='OBSERVED_TIMINGS_CONSISTENT' if all(r['consistentWithinOneTick'] for r in rows) else 'NOT_MATCHED',canCertifyExactOriginalParity=False,checks=rows,limits=data['limits'])
(root/'measurements/event-gate.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));raise SystemExit(0 if result['status']=='OBSERVED_TIMINGS_CONSISTENT' else 1)
