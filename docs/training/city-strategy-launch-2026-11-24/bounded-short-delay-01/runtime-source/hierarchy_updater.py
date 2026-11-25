"""PPO update engine. Importing/validating never trains; update() is explicit.

Prepared minibatches must contain the already checked hierarchy returns. This
module does not guess trace units, lambda, level weighting or joint entropy.
"""
from dataclasses import dataclass
from time import monotonic
import torch
from hierarchy_objective import clipped_ppo_terms,joint_log_probability

@dataclass(frozen=True)
class UpdateSettings:
    epochs:int=4
    clip_range:float=.2
    entropy_coefficient:float=.01
    value_coefficient:float=.5
    max_gradient_norm:float=.5
    target_kl:float=.02

class HierarchyUpdater:
    def __init__(self,policy,settings=UpdateSettings()):
        self.policy,self.settings=policy,settings
        if settings.epochs<1 or settings.max_gradient_norm<=0 or settings.target_kl<=0:
            raise ValueError('Invalid update settings')

    def loss(self,batch):
        """Forward-only loss evaluation; no backward or parameter changes."""
        p=self.policy
        from parallel_stage1 import batch_to_device
        batch=batch_to_device(batch,p.device)
        obs,actions,masks=batch['observations'],batch['actions'],batch['masks']
        values,logp,entropy=p.evaluate_actions(obs,actions,action_masks=masks)
        secondary_values=None
        if batch['role']=='manager':
            secondary_values,secondary_logp,_=p.evaluate_actions(batch['secondary_observations'],batch['secondary_actions'],
                                                action_masks=batch['secondary_masks'])
            logp=joint_log_probability(logp,secondary_logp*batch['secondary_present'])
            # An explicitly supplied estimator must include conditional dependence.
            entropy=batch['joint_entropy_estimator'](p,batch)
        elif batch['role']!='executor':raise ValueError('Unknown update role')
        terms=clipped_ppo_terms(new_log_probability=logp,old_log_probability=batch['old_log_probability'],
            advantages=batch['advantages'],values=values,returns=batch['returns'],entropy=entropy,
            clip_range=self.settings.clip_range,normalize_advantage=batch.get('normalize_advantage',True))
        if secondary_values is not None:
            present=batch['secondary_present']
            target=batch['returns'].detach()
            primary_error=(values.reshape(-1)-target).square()
            secondary_error=(secondary_values.reshape(-1)-target).square()
            terms['value_loss']=((primary_error+present*secondary_error)/(1+present)).mean()
        total=terms['policy_loss']+self.settings.value_coefficient*terms['value_loss']+self.settings.entropy_coefficient*terms['entropy_loss']
        return total,terms

    def update(self,epoch_batches,*,training_authorized=False,deadline=None):
        if training_authorized is not True:
            raise PermissionError('Training is disabled; explicit run authorization is required')
        # Materialize before any update so missing role weights cannot cause a
        # partially applied collection. Data preparation owns masks/returns.
        batches=list(epoch_batches)
        if not batches:raise ValueError('No update minibatches')
        for batch in batches:
            if batch.get('role') not in ('manager','executor') or not 0<batch.get('level_weight',0)<=1:
                raise ValueError('Explicit positive level weight required')
            if batch['role']=='manager' and not callable(batch.get('joint_entropy_estimator')):
                raise ValueError('Explicit conditional manager entropy estimator required')
        if abs(sum(b['level_weight'] for b in batches)-1)>1e-6:
            raise ValueError('Minibatch weights must sum to one')
        records=[]
        self.policy.set_training_mode(True)
        for epoch in range(self.settings.epochs):
            if deadline is not None and monotonic()>=deadline:break
            # Check the entire epoch before changing any parameters.
            with torch.no_grad():
                kl=0.
                for batch in batches:
                    total,terms=self.loss(batch)
                    if not torch.isfinite(total):raise FloatingPointError('Nonfinite loss')
                    kl+=batch['level_weight']*terms['approximate_kl'].item()
            if kl>1.5*self.settings.target_kl:return records
            self.policy.optimizer.zero_grad(set_to_none=True)
            try:
                # Accumulate a role-balanced objective before one shared Adam step.
                # Separate Adam steps would undo much of the intended role weighting.
                for batch in batches:
                    total,terms=self.loss(batch)
                    if not torch.isfinite(total):raise FloatingPointError('Nonfinite loss')
                    (batch['level_weight']*total).backward()
                norm=torch.nn.utils.clip_grad_norm_(self.policy.parameters(),self.settings.max_gradient_norm,error_if_nonfinite=True)
                self.policy.optimizer.step()
            except BaseException:
                self.policy.optimizer.zero_grad(set_to_none=True)
                raise
            records.append(dict(epoch=epoch,approximate_kl=kl,gradient_norm=float(norm)))
        return records
