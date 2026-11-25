"""Prepare score-only two-level PPO batches. No parameter updates.

Initial integration choice: gamma=1, lambda=1 at both levels. This avoids an
arbitrary token-count decay through paused edits; variance remains an empirical
risk. Choices are provisional engineering settings, not new user approvals.
"""
import numpy as np
import torch
from hierarchy_rollout import FocusAssembler,generalized_advantages


def conditional_entropy(policy,batch):
    """Importance-weighted entropy of primary plus conditional secondary.

    Secondary is conditioned on a primary sampled from the frozen behavior
    policy. The primary importance ratio supplies the missing gradient of its
    current-policy expectation; simply adding sampled entropies would omit it.
    """
    _,logp,h=policy.evaluate_actions(batch['observations'],batch['actions'],action_masks=batch['masks'])
    _,_,conditional=policy.evaluate_actions(batch['secondary_observations'],batch['secondary_actions'],action_masks=batch['secondary_masks'])
    ratio=(logp-batch['old_primary_log_probability']).exp()
    return h+batch['secondary_present']*ratio*conditional


def prepare_batches(collection,*,device,minibatch_size=128,normalize_advantage=True,direct=False):
    if minibatch_size<1:raise ValueError('Positive minibatch size required')
    records=collection.transitions
    if not records:raise ValueError('Empty collection')
    if any(t.policy_version!=collection.policy_version for t in records):raise ValueError('Mixed behavior versions')
    assembler=FocusAssembler()
    if direct:
        # Direct episodes have one policy decision stream and no focus assembly.
        for index, token in enumerate(records):
            if (token.role != 'executor' or token.next_role != 'executor'
                    or token.mask.ndim != 1 or not 0 <= token.action < len(token.mask)
                    or not token.mask[token.action]
                    or not all(np.isfinite(v) for v in (token.reward, token.value, token.log_probability))
                    or not 0 <= token.start_tick <= token.end_tick
                    or (index < len(records) - 1 and (token.terminated or token.truncated))):
                raise ValueError('Invalid direct transition stream')
    else:
        assembler.append(records)
    if assembler.active is not None or assembler.pending_primary is not None:
        raise ValueError('Collection cuts an unfinished focus; collect to its boundary before updating')
    managers=[]
    for interval in assembler.completed:
        managers.append((interval.primary,interval.secondary,interval.reward,interval.terminated))
    for primary in assembler.partial_selections:
        managers.append((primary,None,0.,primary.terminated))
    # Last partial selection is last in time; normal intervals are already ordered.
    executors=[t for t in records if t.role=='executor']
    prepared=[]
    for role,rows in [('manager',managers),('executor',executors)]:
        if not rows:continue
        first=[row[0] for row in rows] if role=='manager' else rows
        rewards=[row[2] for row in rows] if role=='manager' else [t.reward for t in rows]
        terminal=[row[3] for row in rows] if role=='manager' else [t.terminated for t in rows]
        values=[t.value for t in first]
        next_values=values[1:]+[collection.bootstrap_value]
        advantages,returns=generalized_advantages(rewards=rewards,values=values,next_values=next_values,
            terminated=terminal,trace_ends=[False]*(len(rows)-1)+[True],durations=[1]*len(rows),
            trace_lambda=1.,trace_units='policy_tokens')
        # Normalize over the role's whole rollout, not independently in size-one minibatches.
        if normalize_advantage and len(advantages)>1:advantages=(advantages-advantages.mean())/(advantages.std(ddof=1)+1e-8)
        count=(len(rows)+minibatch_size-1)//minibatch_size
        for start in range(0,len(rows),minibatch_size):
            chosen=first[start:start+minibatch_size]
            def tensor(a,dtype=None):return torch.as_tensor(np.asarray(a),dtype=dtype,device=device)
            def obs(tokens):return {k:tensor([t.observation[k] for t in tokens],torch.float32) for k in chosen[0].observation}
            batch=dict(role=role,observations=obs(chosen),actions=tensor([t.action for t in chosen],torch.long),
                masks=tensor([t.mask for t in chosen],torch.bool),
                advantages=tensor(advantages[start:start+len(chosen)],torch.float32),
                returns=tensor(returns[start:start+len(chosen)],torch.float32),
                level_weight=1./count,normalize_advantage=False)
            if role=='executor':batch['old_log_probability']=tensor([t.log_probability for t in chosen],torch.float32)
            else:
                subset=rows[start:start+len(chosen)]
                secondary=[s if s is not None else p for p,s,_,_ in subset]
                batch.update(secondary_observations=obs(secondary),
                    secondary_actions=tensor([t.action for t in secondary],torch.long),
                    secondary_masks=tensor([t.mask for t in secondary],torch.bool),
                    secondary_present=tensor([s is not None for _,s,_,_ in subset],torch.float32),
                    old_primary_log_probability=tensor([t.log_probability for t in chosen],torch.float32),
                    old_log_probability=tensor([p.log_probability+(s.log_probability if s is not None else 0.) for p,s,_,_ in subset],torch.float32),
                    joint_entropy_estimator=conditional_entropy)
            prepared.append(batch)
    # Equal aggregate role weight; sample-size weight within each role.
    roles={b['role'] for b in prepared}
    for batch in prepared:
        total=sum(len(b['actions']) for b in prepared if b['role']==batch['role'])
        batch['level_weight']=len(batch['actions'])/total/len(roles)
    return prepared
