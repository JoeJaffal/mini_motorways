"""Explicit optimizer-group overrides without resetting learned Adam state."""
import math


def set_critic_lr_scale(policy, scale):
    """Change only the dedicated value-head group's relative learning rate."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Critic learning-rate scale must be finite and positive')
    value_ids={id(p) for p in policy.value_net.parameters() if p.requires_grad}
    matches=[i for i,g in enumerate(policy.optimizer.param_groups)
             if {id(p) for p in g['params']} == value_ids]
    if not value_ids or len(matches)!=1:
        raise ValueError('A dedicated optimizer group containing exactly the value head is required')
    index=matches[0]
    policy.optimizer.param_groups[index]['lr_scale']=float(scale)
    return index
