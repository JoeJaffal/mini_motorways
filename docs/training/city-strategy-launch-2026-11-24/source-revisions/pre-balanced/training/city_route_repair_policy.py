"""Learn an opening-specific correction from visible driveway geometry."""

import torch
from torch import nn

from city_road_policy import CityActionDistribution, CityActionHead, CityEdgeFeatures, CityLatents, CityRoadPolicy, ROAD_SLOTS
from environment import DIRS
from visible_observation import CELLS, HEIGHT, WIDTH


class RouteRepairFeatures(CityEdgeFeatures):
    def __init__(self, observation_space, *, frontier=False, progress=False, calibrated=False):
        super().__init__(observation_space)
        cells = torch.arange(CELLS)
        xy = torch.stack((cells % WIDTH, cells // WIDTH), dim=1).float()
        directions = torch.tensor(DIRS,dtype=torch.float32)
        self.register_buffer('coordinates',xy,persistent=False)
        self.register_buffer('direction_vectors',directions,persistent=False)
        self.register_buffer('starts',cells.repeat_interleave(4),persistent=False)
        self.register_buffer('edge_delta',directions[:4].repeat(CELLS,1),persistent=False)
        self.register_buffer('ends',self.neighbors[:CELLS,:4].reshape(-1).clamp_max(CELLS-1),persistent=False)
        self._features_dim += 1
        self.frontier = frontier
        self.progress = progress
        self.calibrated = calibrated
        if calibrated:
            if not progress:
                raise ValueError('Calibration requires progress-conditioned decisions')
            self.route_alignment = nn.Parameter(torch.tensor(8.0))
            self.route_hold = nn.Parameter(torch.tensor(3.25))
        if progress:
            if not frontier:
                raise ValueError('Progress conditioning requires connected road features')
            self._features_dim += ROAD_SLOTS + 1
            self.route_progress_weight = nn.Parameter(torch.tensor(7.5))
            self.route_direction_weight = nn.Parameter(torch.tensor(2.5))
            self.route_wait_coupling = nn.Parameter(torch.tensor(6.0))
        self.route_edges = nn.Sequential(nn.Linear(22 if frontier else 18,32),nn.SiLU(),nn.Linear(32,24),nn.SiLU(),nn.Linear(24,1))
        self.route_wait = nn.Sequential(nn.Linear(9 if frontier else 8,24),nn.SiLU(),nn.Linear(24,1))
        self.route_scale = nn.Parameter(torch.tensor(-1.1 if frontier else 0.))
        for module in (self.route_edges,self.route_wait):
            nn.init.zeros_(module[-1].weight)
            nn.init.zeros_(module[-1].bias)
        if frontier:
            nn.init.constant_(self.route_wait[-1].bias,1.5)

    def connected_ends(self,grid,home,shop):
        """Mark roads reachable over existing visible links from the two driveway approaches."""
        points = torch.stack((home,shop),dim=1).long()
        indices = (points[:,:,1]*WIDTH+points[:,:,0]).clamp(0,CELLS-1)
        reach = torch.zeros((len(grid),2,CELLS+1),dtype=torch.bool,device=grid.device)
        reach.scatter_(2,indices[:,:,None],True)
        present = grid[:,9:17].transpose(1,2).bool()
        present = torch.nn.functional.pad(present,(0,0,0,1))
        for _ in range(8):
            reach = reach | (reach[:,:,self.neighbors] & present[:,None]).any(dim=-1)
        connected = (reach[:,0] & reach[:,1]).any(dim=1,keepdim=True)
        ends = torch.cat((reach[:,:,self.starts],reach[:,:,self.ends]),dim=1).transpose(1,2)
        return ends.to(grid.dtype),connected.to(grid.dtype),reach[:,:,:CELLS]

    def observed_progress(self, reach, ends):
        # Geometric clearance between current components. Terrain and future roads
        # do not enter this distance transform. Legality is applied separately.
        region = reach.reshape(-1,2,HEIGHT,WIDTH).float()
        distance = 1. - region
        for _ in range(7):
            region = torch.nn.functional.max_pool2d(region,3,stride=1,padding=1)
            distance = distance + 1. - region
        to_home,to_shop = distance.flatten(2).unbind(dim=1)
        gap = to_shop.masked_fill(~reach[:,0],8).amin(dim=1,keepdim=True)
        home_start,shop_start,home_end,shop_end = ends.unbind(dim=2)
        a = (gap-to_shop[:,self.ends]).clamp(0,1)*home_start*(1-home_end)
        b = (gap-to_shop[:,self.starts]).clamp(0,1)*home_end*(1-home_start)
        c = (gap-to_home[:,self.ends]).clamp(0,1)*shop_start*(1-shop_end)
        d = (gap-to_home[:,self.starts]).clamp(0,1)*shop_end*(1-shop_start)
        return torch.maximum(torch.maximum(a,b),torch.maximum(c,d))

    def forward(self, observations):
        with torch.no_grad():
            base = super().forward(observations)
        grid = observations['grid'].flatten(2)
        houses = grid[:,19] * grid[:,29]
        destinations = grid[:,20] * grid[:,29]
        home_count = houses.sum(dim=1,keepdim=True)
        shop_count = destinations.sum(dim=1,keepdim=True)
        colors = grid[:,21:29]
        common = ((colors * houses[:,None]).sum(dim=2) * (colors * destinations[:,None]).sum(dim=2)).sum(dim=1)
        active = ((home_count==1) & (shop_count==1) & (common[:,None]==1)).to(grid.dtype)

        drive = torch.matmul(grid[:,30:38].transpose(1,2),self.direction_vectors)
        approaches = self.coordinates + drive
        home = (approaches*houses[:,:,None]).sum(dim=1)
        shop = (approaches*destinations[:,:,None]).sum(dim=1)
        if self.progress:
            # The opening specialist was calibrated on local gaps within this range.
            active = active*((home-shop).abs().amax(dim=1,keepdim=True)<=6)
        first = self.coordinates[self.starts]
        second = first + self.edge_delta
        home_first = (first-home[:,None])/8
        home_second = (second-home[:,None])/8
        shop_first = (first-shop[:,None])/8
        shop_second = (second-shop[:,None])/8
        degree = grid[:,9:17].sum(dim=1)/8
        board_metrics = torch.stack((grid[:,5],degree,grid[:,29]),dim=-1)
        edge_input = torch.cat((
            home_first,home_second,shop_first,shop_second,
            home_first.abs().amax(dim=2,keepdim=True),home_second.abs().amax(dim=2,keepdim=True),
            shop_first.abs().amax(dim=2,keepdim=True),shop_second.abs().amax(dim=2,keepdim=True),
            board_metrics[:,self.starts],board_metrics[:,self.ends],
        ),dim=2)
        if self.frontier:
            frontier, connected, reach = self.connected_ends(grid,home,shop)
            edge_input = torch.cat((edge_input,frontier),dim=2)
        correction = self.route_edges(edge_input).squeeze(-1)
        base_roads = base[:,:ROAD_SLOTS]
        roads = base_roads + active*(correction + self.route_scale.tanh()*base_roads)
        visible = grid[:,0].sum(dim=1).clamp_min(1)
        wait_input = torch.cat((
            observations['global'][:,[0,24,25,26,27]],
            (grid[:,3].sum(dim=1)/visible)[:,None],
            ((home-shop).abs().amax(dim=1)/8)[:,None],
            (grid[:,5].sum(dim=1)/visible)[:,None],
        ),dim=1)
        if self.frontier:
            wait_input = torch.cat((wait_input,connected),dim=1)
        wait = active*self.route_wait(wait_input)
        if self.progress:
            evidence = active*self.observed_progress(reach,frontier)
            hs,ss,he,se = frontier.unbind(dim=2)
            to_shop = (shop_first.norm(dim=2)-shop_second.norm(dim=2))*8
            to_home = (home_first.norm(dim=2)-home_second.norm(dim=2))*8
            direction = torch.maximum((hs-he)*to_shop,(ss-se)*to_home).clamp(0,1)
            preference = self.route_progress_weight+self.route_direction_weight*direction
            coupling = active*self.route_wait_coupling
            if self.calibrated:
                unit = self.edge_delta/self.edge_delta.norm(dim=1,keepdim=True)
                def bearing(offset, sign):
                    return sign*(offset*unit).sum(dim=2)/offset.norm(dim=2).clamp_min(.001)
                home_bearing = hs*(1-he)*bearing(shop_first,-1) + he*(1-hs)*bearing(shop_second,1)
                shop_bearing = ss*(1-se)*bearing(home_first,-1) + se*(1-ss)*bearing(home_second,1)
                alignment = torch.maximum(home_bearing,shop_bearing).clamp(0,1)
                preference = preference+self.route_alignment*alignment
                wait = wait+.4*active*self.route_hold
                coupling = coupling+active*self.route_hold
            roads = roads + evidence*preference
            return torch.cat((roads,base[:,ROAD_SLOTS:],wait,evidence,coupling),dim=1)
        return torch.cat((roads,base[:,ROAD_SLOTS:],wait),dim=1)


class RouteRepairLatents(CityLatents):
    def forward_critic(self, features):
        return features[:,ROAD_SLOTS:-1]


class RouteRepairHead(CityActionHead):
    def forward(self, features):
        logits = super().forward(features[:,:-1])
        return torch.cat((logits[:,:1]+features[:,-1:],logits[:,1:]),dim=1)


class RouteRepairPolicy(CityRoadPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.mlp_extractor = RouteRepairLatents()
        self.action_net = RouteRepairHead(self.features_extractor.context_width)
        for name, parameter in self.features_extractor.named_parameters():
            parameter.requires_grad_(name.startswith('route_'))
        self.action_net.requires_grad_(False)
        self.optimizer = self.optimizer_class(filter(lambda p:p.requires_grad,self.parameters()),
                                              lr=lr_schedule(1),**self.optimizer_kwargs)


class ProgressLatents(RouteRepairLatents):
    def forward_critic(self, features):
        return super().forward_critic(features[:,:-(ROAD_SLOTS+1)])


class ProgressHead(RouteRepairHead):
    def forward(self, features):
        ordinary = super().forward(features[:,:-(ROAD_SLOTS+1)])
        return torch.cat((ordinary,features[:,-(ROAD_SLOTS+1):]),dim=1)


class ProgressDistribution(CityActionDistribution):
    def proba_distribution(self, action_logits):
        self.progress_scores = action_logits[:,ROAD_SLOTS+1:-1]
        self.coupling = action_logits[:,-1:]
        return super().proba_distribution(action_logits[:,:ROAD_SLOTS+1])

    def apply_masking(self, masks):
        original = self.raw_logits
        evidence = self.progress_scores
        if masks is not None:
            legal = torch.as_tensor(masks,device=evidence.device,dtype=torch.bool).reshape_as(original)
            evidence = evidence.masked_fill(~legal[:,1:],0)
        best = evidence.amax(dim=1,keepdim=True)
        wait = original[:,:1] + self.coupling*(.6-best)
        self.raw_logits = torch.cat((wait,original[:,1:]),dim=1)
        try:
            super().apply_masking(masks)
        finally:
            self.raw_logits = original


class RouteProgressPolicy(RouteRepairPolicy):
    def _build(self, lr_schedule):
        super()._build(lr_schedule)
        self.action_dist = ProgressDistribution(self.action_space.n)
        self.mlp_extractor = ProgressLatents()
        self.action_net = ProgressHead(self.features_extractor.context_width)
        self.action_net.requires_grad_(False)
        self.optimizer = self.optimizer_class(filter(lambda p:p.requires_grad,self.parameters()),
                                              lr=lr_schedule(1),**self.optimizer_kwargs)
