"""Checked PPO loss terms, without an updater, backward call or optimizer step.

Same clipped surrogate/value conventions as SB3. Manager conditional action
log-probabilities are summed before clipping their joint likelihood ratio.
A verified entropy/estimator must be supplied explicitly; this module does not
pretend conditional heads have independent joint entropy.
"""
import torch


def joint_log_probability(primary,secondary):
    if primary.ndim!=1 or secondary.shape!=primary.shape:
        raise ValueError('Expected aligned conditional log-probability vectors')
    if not torch.isfinite(primary).all() or not torch.isfinite(secondary).all():
        raise ValueError('Nonfinite manager log probability')
    return primary+secondary


def clipped_ppo_terms(*,new_log_probability,old_log_probability,advantages,
                      values,returns,entropy,clip_range=.2,normalize_advantage=True):
    """Return separate differentiable terms/diagnostics; never update a policy.

    Caller combines levels and coefficients explicitly. There is no default
    level weighting or manager entropy approximation. Value clipping is absent,
    matching the published clip_range_vf=None baseline.
    """
    logp=new_log_probability
    if logp.ndim!=1 or not logp.numel():raise ValueError('Empty/malformed PPO minibatch')
    values=values.reshape(-1);returns=returns.reshape(-1)
    arrays=(old_log_probability,advantages,values,returns)
    if any(a.shape!=logp.shape for a in arrays):raise ValueError('PPO batch shapes differ')
    if entropy is None or entropy.shape!=logp.shape:
        raise ValueError('Supply a checked entropy estimate for every sample')
    if not 0<clip_range<1:raise ValueError('Invalid PPO clipping range')
    if not all(torch.isfinite(a).all() for a in (logp,*arrays,entropy)):
        raise ValueError('Nonfinite PPO input')
    old=old_log_probability.detach()
    advantage=advantages.detach()
    targets=returns.detach()
    if normalize_advantage and advantage.numel()>1:
        advantage=(advantage-advantage.mean())/(advantage.std()+1e-8)
    log_ratio=logp-old
    ratio=log_ratio.exp()
    if not torch.isfinite(ratio).all():raise ValueError('PPO likelihood ratio overflow')
    surrogate=advantage*ratio
    clipped=advantage*ratio.clamp(1-clip_range,1+clip_range)
    return dict(policy_loss=-torch.minimum(surrogate,clipped).mean(),
        value_loss=(values-targets).square().mean(),entropy_loss=-entropy.mean(),
        approximate_kl=((ratio-1)-log_ratio).mean(),
        clip_fraction=((ratio-1).abs()>clip_range).float().mean(),samples=logp.numel())
