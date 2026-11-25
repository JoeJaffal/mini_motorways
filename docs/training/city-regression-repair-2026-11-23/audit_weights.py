from pathlib import Path
import json
import torch
from sb3_contrib import MaskablePPO
from prepare_city_policy import sha256

torch.set_num_threads(1)
archive = Path(__file__).parent
config = json.loads(Path('output/training/city-established-start-01/config.json').read_text())
old = MaskablePPO.load(config['source'], device='cpu')
start = MaskablePPO.load('output/training/city-established-start-01/start.zip', device='cpu')

def exact(a, b):
    if isinstance(a, torch.Tensor):
        torch.testing.assert_close(a, b, atol=0, rtol=0)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a: exact(a[k], b[k])
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        for x,y in zip(a,b): exact(x,y)
    else: assert a == b, (a,b)

exact(old.policy.optimizer.state_dict(), start.policy.optimizer.state_dict())
assert sha256(Path(config['source'])) == config['source_sha256']
root = Path('output/training/city-established-pilot-01')
results = []
for row in json.loads((root/'state.json').read_text())['checkpoints']:
    path = root/row['path']
    assert sha256(path) == row['sha256']
    model = MaskablePPO.load(path, device='cpu')
    before = start.policy.state_dict()
    changes = {k: float((v-before[k]).abs().max()) for k,v in model.policy.state_dict().items()}
    allowed = lambda k: 'opening_reference' not in k and ('.growth_' in k or k.startswith('value_net.'))
    assert all(v == 0 for k,v in changes.items() if not allowed(k))
    assert any(v > 0 for k,v in changes.items() if '.growth_roads.' in k and allowed(k))
    assert any(v > 0 for k,v in changes.items() if '.growth_grid.' in k and allowed(k))
    assert all(not p.requires_grad for p in model.policy.features_extractor.opening_reference.parameters())
    results.append(dict(checkpoint=str(path), sha256=row['sha256'], changes=changes))
(archive/'weight-audit.json').write_text(json.dumps(dict(optimizer_transfer_exact=True, source_hash_unchanged=True, checkpoints=results), indent=2)+'\n')
print('Exact optimizer transfer; source unchanged; both saves retain protected weights and update spatial growth weights.')
