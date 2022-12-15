from enum import auto
from typing import Tuple
import torch.nn as nn

from ..utils import AutoStrEnum
from ..config import Config
from ..features.ifeature import Feature
from ..modules.io import ModuleFactory
from ..modules.loss_functions import MeanL1Prop


__all__ = [
    "InputSpec",
    "TargetSpec",
    "IOSpec"
]


class InputSpec(Config):
    var_name: str
    data_key: str
    feature: Feature
    module: ModuleFactory.Config

    def __post_init__(self):
        # wire feature and module
        params = getattr(self.module, "module_params", {})
        if hasattr(self.feature, "class_size") and hasattr(params, "class_size"):
            params.class_size = self.feature.class_size
        if hasattr(self.feature, "out_dim") and hasattr(params, "in_dim"):
            params.in_dim = self.feature.out_dim


class ObjectiveType(AutoStrEnum):
    mean_l1_prop = auto()
    cross_entropy = auto()


class TargetSpec(Config):
    var_name: str
    data_key: str
    feature: Feature
    module: ModuleFactory.Config
    objective: ObjectiveType

    def __post_init__(self):
        params = getattr(self.module, "module_params", {})
        if hasattr(self.feature, "class_size") and hasattr(params, "out_dim"):
            params.out_dim = self.feature.class_size

    @staticmethod
    def cross_entropy(output, target):
        criterion = nn.CrossEntropyLoss(reduction="mean")
        L = criterion(output.view(-1, output.size(-1)), target.view(-1))
        return {"loss": L}

    @staticmethod
    def mean_l1_prop(output, target):
        criterion = MeanL1Prop()
        return {"loss": criterion(output, target)}


class IOSpec(Config):
    inputs: Tuple[InputSpec, ...]
    targets: Tuple[TargetSpec, ...]

    def batch(self):
        inputs = {spec.var_name: spec.feature for spec in self.inputs}
        targets = {spec.var_name: spec.feature for spec in self.targets}
        return inputs, targets

    def loss_fn(self):
        funcs = {str(trgt.objective) for trgt in self.targets}
        assert len(funcs) == 1, "only one objective per IOSpec supported"
        return getattr(TargetSpec, funcs.pop())
