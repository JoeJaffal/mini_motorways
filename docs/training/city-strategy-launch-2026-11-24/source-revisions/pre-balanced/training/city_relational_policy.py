"""Learn visible supply and congestion interactions without prescribing roads."""
import torch
from torch import nn
from city_established_policy import CityEstablishedFeatures
from city_growth_policy import CityGrowthFeatures
from city_network_service_policy import CityNetworkServiceFeatures
from city_learning_policy import CityLearningPolicy
from city_road_policy import ROAD_SLOTS
from visible_observation import CELLS


class RelativeRateAdam(torch.optim.Adam):
    """Keep a smaller critic rate when SB3 updates the shared base schedule."""
    def step(self, closure=None):
        rates=[g['lr'] for g in self.param_groups]
        try:
            for g,rate in zip(self.param_groups,rates):g['lr']=rate*g.get('lr_scale',1.)
            return super().step(closure)
        finally:
            for g,rate in zip(self.param_groups,rates):g['lr']=rate


class CityRelationalFeatures(CityEstablishedFeatures):
    def __init__(self, observation_space, *, conservative=True, temperature=20.):
        super().__init__(observation_space,conservative=conservative)
        if not 1 <= temperature <= 20:raise ValueError('Temperature out of range')
        self.register_buffer('growth_road_temperature',torch.tensor(float(temperature)))
        self.growth_relations=nn.Linear(8,1,bias=False)
        nn.init.zeros_(self.growth_relations.weight)

    def relation_evidence(self, raw_grid):
        grid=raw_grid.flatten(2);colors=grid[:,21:29].bool();entrance=grid[:,29].bool()
        directions=grid[:,30:38].argmax(dim=1)
        approaches=self.neighbors[self.service_cells,directions]
        labels,_,attached=self.visible_components(grid,directions,approaches)
        roots=labels.gather(1,approaches)
        houses=grid[:,19].bool() & entrance & attached
        shops=grid[:,20].bool() & entrance & attached
        counts=grid.new_zeros((len(grid),8,CELLS+1)).scatter_add_(2,roots[:,None].expand(-1,8,-1),(colors & houses[:,None]).float())
        supplied=self.roots_by_color(roots,colors,shops)
        a,b=labels[:,self.starts],labels[:,self.ends]
        ia,ib=a[:,None].expand(-1,8,-1),b[:,None].expand(-1,8,-1)
        ha,hb=counts.gather(2,ia),counts.gather(2,ib)
        sa,sb=supplied.gather(2,ia),supplied.gather(2,ib)
        gain=(ha*(~sa & sb)+hb*(~sb & sa)).sum(dim=1).clamp(max=6)
        degree=grid[:,9:17].bool().any(dim=1)
        degree=torch.nn.functional.pad(degree,(0,1))
        cycle=(a==b) & degree[:,self.starts] & degree[:,self.ends]
        # Current visible counts and motion-derived stopping, never native routes
        # or internal vehicle speed. Pool only the existing road components.
        cars=(grid[:,57]/(1-grid[:,57]).clamp_min(.05)).clamp(max=20)
        def pooled(values):
            total=grid.new_zeros((len(grid),CELLS+1)).scatter_add_(1,labels[:,:CELLS],values)
            return torch.maximum(total.gather(1,a),total.gather(1,b))
        density=(pooled(cars)/8).clamp(max=4)
        stopped=(pooled(cars*grid[:,62])/4).clamp(max=4)
        advance,_,urgency,*_=self.service_features(raw_grid)
        return torch.stack((gain,gain*stopped,cycle.float(),cycle*stopped,
                            gain*density,cycle*density,urgency,advance),dim=-1)

    def forward(self, observations):
        with torch.no_grad():
            established=self.service_features(observations['grid'])[-2]
            opening=self.opening_reference(observations)
            generic=CityGrowthFeatures.forward(self.opening_reference,observations)
            growing=CityNetworkServiceFeatures.forward(self,observations)
            evidence=self.relation_evidence(observations['grid'])
            # Preserve the service corrections; only soften the generic road prior.
            roads=growing[:,:ROAD_SLOTS]-generic[:,:ROAD_SLOTS]*(1-1/self.growth_road_temperature)
        roads=roads+self.growth_relations(evidence).squeeze(-1)
        features=torch.cat((roads,growing[:,ROAD_SLOTS:]),dim=1)
        return torch.where(established,features,opening)


class CityRelationalPolicy(CityLearningPolicy):
    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        for name,p in self.features_extractor.named_parameters():
            p.requires_grad_(name.startswith('growth_relations.'))
        self.optimizer=RelativeRateAdam([
            dict(params=list(self.features_extractor.growth_relations.parameters()),lr_scale=1.),
            dict(params=list(self.value_net.parameters()),lr_scale=.01),
        ],lr=lr_schedule(1),**self.optimizer_kwargs)


class CityDemandRelationsFeatures(CityRelationalFeatures):
    """Include displayed demand on connected destinations, not future demand."""
    def __init__(self, observation_space, *, conservative=True, temperature=20.):
        super().__init__(observation_space,conservative=conservative,temperature=temperature)
        self.growth_relations=nn.Linear(10,1,bias=False)
        nn.init.zeros_(self.growth_relations.weight)

    def relation_evidence(self, raw_grid):
        evidence=super().relation_evidence(raw_grid)
        grid=raw_grid.flatten(2)
        directions=grid[:,30:38].argmax(dim=1)
        approaches=self.neighbors[self.service_cells,directions]
        labels,_,attached=self.visible_components(grid,directions,approaches)
        roots=labels.gather(1,approaches)
        demand=grid[:,41]*(grid[:,20].bool() & grid[:,29].bool() & attached)
        totals=grid.new_zeros((len(grid),CELLS+1)).scatter_add_(1,roots,demand)
        a,b=labels[:,self.starts],labels[:,self.ends]
        pressure=torch.maximum(totals.gather(1,a),totals.gather(1,b)).clamp(max=4)
        return torch.cat((evidence,(evidence[:,:,0]*pressure)[:,:,None],
                          (evidence[:,:,2]*pressure)[:,:,None]),dim=-1)


class CitySharpRelationsFeatures(CityDemandRelationsFeatures):
    """A saved inference calibration for conditional road sampling, not Wait."""
    def __init__(self, observation_space, *, conservative=True, temperature=20., road_scale=20.):
        super().__init__(observation_space,conservative=conservative,temperature=temperature)
        if not 1 <= road_scale <= 20:raise ValueError('Road scale out of range')
        self.register_buffer('growth_sampling_scale',torch.tensor(float(road_scale)))

    def forward(self, observations):
        features=super().forward(observations)
        with torch.no_grad():established=self.service_features(observations['grid'])[-2]
        roads=torch.where(established,features[:,:ROAD_SLOTS]*self.growth_sampling_scale,features[:,:ROAD_SLOTS])
        return torch.cat((roads,features[:,ROAD_SLOTS:]),dim=1)
