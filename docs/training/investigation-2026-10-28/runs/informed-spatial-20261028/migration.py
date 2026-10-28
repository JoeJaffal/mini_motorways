"""Explicit warm start with new input channels; optimizer is intentionally fresh."""
import torch
from sb3_contrib import MaskablePPO


def warm_start(checkpoint,env,hyperparameters,seed,adapt_inputs=False,architecture='legacy'):
    from train import GridEncoder
    source=MaskablePPO.load(checkpoint,device='cpu')
    policy='MultiInputPolicy'
    spatial=architecture in ['spatial-residual','informed-spatial']
    if spatial:
        from spatial_policy import SpatialResidualPolicy,InformedSpatialPolicy
        policy=InformedSpatialPolicy if architecture=='informed-spatial' else SpatialResidualPolicy
    target=MaskablePPO(policy,env,device='cpu',seed=seed,verbose=0,
                      policy_kwargs=dict(features_extractor_class=GridEncoder,net_arch=[64],normalize_images=False),
                      **{k:v for k,v in hyperparameters.items() if k!='net_arch'})
    state=source.policy.state_dict();expected=target.policy.state_dict()
    for key,value in expected.items():
        source_key=key
        if spatial:
            source_key=key.replace('.global_encoder.','.').replace('mlp_extractor.global_mlp.','mlp_extractor.').replace('action_net.base.','action_net.')
        if source_key not in state:
            if spatial and any(t in key for t in ['.spatial.','.global_context.','.spatial_head.','.prior_strength']):continue
            raise ValueError(f'Unrecognized checkpoint parameter: {key}')
        old=state[source_key]
        if value.shape!=old.shape:
            if not (adapt_inputs and key.endswith('grid.0.weight') and old.shape[1]==50 and value.shape[1]==52):
                raise ValueError(f'Unsupported migration shape for {key}: {old.shape} -> {value.shape}')
            expanded=torch.zeros_like(value);expanded[:,:50]=old;old=expanded
        expected[key]=old
    target.policy.load_state_dict(expected,strict=True)
    print(f'WARM START | {architecture} | policy copied; added input/residual outputs zero; optimizer reset',flush=True)
    return target
