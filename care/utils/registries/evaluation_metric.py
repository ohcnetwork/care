from enum import Enum


class AllowedEvaluatorContexts(Enum):
    patient = "patient"
    encounter = "encounter"


class AllowedOperations(Enum):
    # Core Supported Operations
    equality = "equality"
    in_range = "in_range"
    has_tag = "has_tag"


class EvaluatorMetricsRegistry:
    _evaluators = []
    _evaluator_cache = {}

    @classmethod
    def init_cache(cls) -> None:
        cls._evaluator_cache = {}
        for evaluator in cls._evaluators:
            cls._evaluator_cache[evaluator.name] = evaluator

    @classmethod
    def register(cls, evaluator_class: type) -> None:
        if evaluator_class not in cls._evaluators:
            cls._evaluators.append(evaluator_class)
            cls.init_cache()

    @classmethod
    def get_evaluator(cls, metric_name) -> type:
        if metric_name in cls._evaluator_cache:
            return cls._evaluator_cache[metric_name]
        raise ValueError("Evaluator not found")

    @classmethod
    def get_all_metrics(cls) -> list[type]:
        return cls._evaluators
