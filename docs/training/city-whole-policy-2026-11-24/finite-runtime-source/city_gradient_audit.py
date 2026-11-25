"""Bounded, read-only gradient measurements around PPO's global clipping."""
import json
import torch


class GradientAudit:
    def __init__(self, optimizer, path, steps, task=lambda: None):
        if steps<1:raise ValueError('Positive audit step limit required')
        self.path,self.limit,self.task=path,steps,task
        self.count=0;self.squares={};self.handles=[]
        for group in optimizer.param_groups:
            for parameter in group['params']:
                if parameter.requires_grad:
                    self.handles.append(parameter.register_hook(self.capture(id(parameter))))
        self.handles.append(optimizer.register_step_pre_hook(self.before_step))

    def capture(self, identity):
        def hook(gradient):
            if self.count<self.limit:self.squares[identity]=gradient.detach().square().sum()
            # Returning None preserves the gradient exactly.
        return hook

    def before_step(self, optimizer, args, kwargs):
        if self.count>=self.limit:return
        groups=[]
        for index,group in enumerate(optimizer.param_groups):
            before=[self.squares[id(p)] for p in group['params'] if id(p) in self.squares]
            after=[p.grad.detach().square().sum() for p in group['params'] if p.grad is not None]
            groups.append(dict(index=index,lr_scale=group.get('lr_scale',1),
                before_clip=float(torch.sqrt(sum(before)).item()) if before else 0.,
                after_clip=float(torch.sqrt(sum(after)).item()) if after else 0.))
        self.count+=1;self.squares.clear()
        with self.path.open('a') as stream:
            stream.write(json.dumps(dict(update=self.count,task=self.task(),groups=groups))+'\n')

    def close(self):
        for handle in self.handles:handle.remove()
        self.handles.clear();self.squares.clear()
