"""Inspect the production features on an exact city miss and a known visible component."""

import argparse
import json
from pathlib import Path
from types import MethodType

import numpy as np
from sb3_contrib import MaskablePPO
import torch

from city_road_pilot import CityRoadEnv, edge_action
from city_road_policy import ROAD_SLOTS
from prepare_city_policy import masked_probs, sha256
from visible_observation import CELLS, WIDTH, bounded


def full_reach(self, anchors, links):
    reached = anchors
    for _ in range(CELLS):
        after = reached | (reached[:, :, self.neighbors] & links[:, None]).any(dim=-1)
        if torch.equal(after, reached):
            return reached
        reached = after
    raise RuntimeError('Visible component failed to converge')


def road_chain(features):
    anchors = torch.zeros((1, 8, CELLS + 1), dtype=torch.bool)
    links = torch.zeros((1, CELLS + 1, 8), dtype=torch.bool)
    first = 12 * WIDTH + 8
    anchors[0, 0, first] = True
    for cell in range(first, first + 16):
        links[0, cell, 0] = links[0, cell + 1, 4] = True
    result = features.connected_roads(anchors, links)
    full = full_reach(features, anchors, links)
    return dict(graph_edges=16, production_reach=int(result.sum()), true_reach=int(full.sum()),
                production_reaches_tail=bool(result[0, 0, first+16]))


def competing_destinations(features, board_shape):
    board = torch.zeros((1, *board_shape))
    board[:, 0:2] = 1

    def parcel(x, y, kind, color, direction):
        board[0, (kind, 21+color, 29, 30+direction), y, x] = 1

    parcel(10, 10, 19, 0, 0)  # First driveway approach at (11,10).
    parcel(13, 10, 20, 0, 4)  # Nearer approach at (12,10).
    parcel(15, 13, 20, 0, 4)  # Farther approach at (14,13).
    parcel(5, 5, 19, 1, 0)
    parcel(7, 5, 20, 1, 4)
    action = edge_action((11,10), (12,11))-1
    advance, _, _, established, _ = features.service_evidence(board)
    short_unbuilt_counts_established = bool(established)
    # Add the two visible driveway links of the independent working pair.
    board[0, 9, 5, 5] = 1
    board[0, (9, 13), 5, 6] = 1
    board[0, 13, 5, 7] = 1
    with_near, _, active, _, _ = features.service_evidence(board)
    assert bool(active)
    board[0, 21, 10, 13] = 0
    board[0, 23, 10, 13] = 1  # Keep the parcel in place, give it a different color.
    without_near, _, active, _, _ = features.service_evidence(board)
    assert bool(active)
    return dict(
        proposed_edge=((11,10), (12,11)),
        shorter_same_color_target_progress=float(with_near[0, action]),
        shorter_other_color_target_progress=float(without_near[0, action]),
        bare_cell_between_matching_driveways_counts_established=short_unbuilt_counts_established,
    )


def measure(model, obs, mask, alternatives):
    features = model.policy.features_extractor
    inputs, _ = model.policy.obs_to_tensor(obs)
    with torch.no_grad():
        advance, join, active, established, quiet = features.service_evidence(inputs['grid'])
        p = masked_probs(model, obs, mask).astype(np.float64)
        p /= p.sum()
        ix = np.array(alternatives)-1
        ranked = p[1:][mask[1:]]
        movement = features(inputs)
        wait_idx = ROAD_SLOTS+features.context_width
        return dict(
            active=bool(active), established=bool(established), quiet=bool(quiet),
            joins=join[0, ix].tolist(), progress=advance[0, ix].tolist(),
            direct_join_probability=float(p[alternatives].sum()),
            best_join_rank=1+int((ranked>p[alternatives].max()).sum()),
            wait_probability=float(p[0]), legal_roads=int(mask[1:].sum()),
            masked_progress_best=float(movement[0,wait_idx+1:-1][mask[1:]].max()),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    torch.set_num_threads(1)
    recorded=json.loads((args.evidence/'same-state-policy-probabilities.json').read_text())
    audit=json.loads((args.evidence/'one-edge-witness.json').read_text())
    witness=next(game for game in audit['games'] if game['seed']==recorded['seed'])
    checkpoint=Path(recorded['models']['eight_hours']['checkpoint'])
    assert sha256(checkpoint)==audit['checkpoint_sha256']
    assert sha256(args.dll)==audit['host_sha256']
    model=MaskablePPO.load(checkpoint,device='cpu')
    features=model.policy.features_extractor
    moves=recorded['ignored_connections']
    env=CityRoadEnv(args.dll)
    try:
        obs,_=env.reset(options={'scenario_seed':witness['seed']})
        for action in witness['actions'][:moves[0]['decision']]:
            obs,_,_,_,info=env.step(action)
        assert info['seconds']==recorded['seconds']
        mask=env.action_masks()
        alternatives=[r['alternative'] for r in moves]
        with torch.no_grad():
            result=dict(
                seed=witness['seed'], second=info['seconds'],
                stock=info['road_stock'], n_buildings=info['buildings'],
                road_chain=road_chain(features),
                competing_destinations=competing_destinations(features,obs['grid'].shape),
                reserve_eligible_stock=[n for n in range(31) if bounded(n,100)<=8/108],
                original=measure(model,obs,mask,alternatives),
                scalar_weights={k:float(v) for k,v in features.named_parameters() if k.startswith('growth_service_')},
            )
            assert abs(result['original']['direct_join_probability']-recorded['models']['eight_hours']['direct_join_probability'])<1e-12
            features.connected_roads=MethodType(full_reach,features)
            result['fixed_point_comparison']=measure(model,obs,mask,alternatives)
    finally:
        env.close()
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
