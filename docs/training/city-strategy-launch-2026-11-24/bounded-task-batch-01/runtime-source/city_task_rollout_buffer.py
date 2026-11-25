"""Use PPO's existing advantage normalization within task-homogeneous batches."""
import numpy as np
from sb3_contrib.common.maskable.buffers import MaskableDictRolloutBuffer


class CityTaskRolloutBuffer(MaskableDictRolloutBuffer):
    def __init__(self, *args, worker_tasks, **kwargs):
        self.worker_tasks = tuple(worker_tasks)
        super().__init__(*args, **kwargs)
        if len(self.worker_tasks) != self.n_envs:
            raise ValueError('One fixed task label is required per worker')

    def get(self, batch_size=None):
        if batch_size is None:
            yield from super().get(None)
            return
        if batch_size < 1:
            raise ValueError('Batch size must be positive')
        assert self.full
        if not self.generator_ready:
            for key, observations in self.observations.items():
                self.observations[key] = self.swap_and_flatten(observations)
            for name in ('actions', 'values', 'log_probs', 'advantages', 'returns', 'action_masks'):
                self.__dict__[name] = self.swap_and_flatten(self.__dict__[name])
            self.generator_ready = True
        # SB3 flattens worker-major, then timestep-major. Preserve every row,
        # including its original mask, likelihood, value and native return.
        labels = np.repeat(np.asarray(self.worker_tasks), self.buffer_size)
        batches = []
        for task in np.unique(labels):
            indices = np.random.permutation(np.flatnonzero(labels == task))
            batches.extend(indices[start:start + batch_size]
                           for start in range(0, len(indices), batch_size))
        # Shuffle task order as well as examples, rather than always updating
        # cities first and the small lessons last.
        for index in np.random.permutation(len(batches)):
            yield self._get_samples(batches[index])
