"""Explicit warm start with new input channels; optimizer is intentionally fresh."""
import torch
from sb3_contrib import MaskablePPO


def warm_start(checkpoint,env,hyperparameters,seed,adapt_inputs=False):
    from train import GridEncoder
    source=MaskablePPO.load(checkpoint,device='cpu')
    target=MaskablePPO('MultiInputPolicy',env,device='cpu',seed=seed,verbose=0,
                      policy_kwargs=dict(features_extractor_class=GridEncoder,net_arch=[64],normalize_images=False),
                      **{k:v for k,v in hyperparameters.items() if k!='net_arch'})
    state=source.policy.state_dict();expected=target.policy.state_dict()
    for key,value in expected.items():
        if key not in state:raise ValueError(f'Unrecognized checkpoint parameter: {key}')
        old=state[key]
        if value.shape!=old.shape:
            if not (adapt_inputs and key.endswith('grid.0.weight') and old.shape[1]==50 and value.shape[1]==52):
                raise ValueError(f'Unsupported migration shape for {key}: {old.shape} -> {value.shape}')
            expanded=torch.zeros_like(value);expanded[:,:50]=old;state[key]=expanded
    target.policy.load_state_dict(state,strict=True)
    print('WARM START | policy weights copied; added input weights zero; optimizer reset',flush=True)
    return target
