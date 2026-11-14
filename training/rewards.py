"""Bounded, discounted potential shaping; no persistent connection bonus bank."""
import math

GAMMA=.999
WEIGHT=.25
HOUSE_CAP=8
REWARD_SCHEMAS={'trips':'trip-delta-v1','connectivity':'trip-plus-connectivity-potential-v1'}


class ConnectionPotential:
    def __init__(self,gamma=GAMMA,weight=WEIGHT,cap=HOUSE_CAP):
        if not 0<gamma<1 or not math.isfinite(weight) or weight<0 or cap<1:
            raise ValueError('Invalid connection-potential parameters')
        self.gamma,self.weight,self.cap=gamma,weight,cap
        self.previous=0.0

    def potential(self,count):
        if not isinstance(count,int) or count<0:
            raise ValueError('Expected nonnegative integer connected-house diagnostic')
        return self.weight*min(count,self.cap)

    def reset(self,count):
        self.previous=self.potential(count)

    def step(self,count,terminated=False):
        # External time limits bootstrap the live potential. True terminal
        # states have potential zero, canceling the remaining shaping balance.
        current=0.0 if terminated else self.potential(count)
        shaping=self.gamma*current-self.previous
        self.previous=current
        return shaping
