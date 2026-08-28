from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from itertools import product

from rs_benchmark.models.experiment import ExperimentConfig
from rs_benchmark.models.sweep import ParameterSweepConfig, SweepDefinition, SweepMode

PARAMETER_ORDER = (
    "feature_detection_quality",
    "max_features_per_image",
    "image_overlap",
    "max_feature_reprojection_error",
)


class ExperimentGenerator:
    """Pure experiment-design service. It never starts RealityScan."""

    def generate(self, config: ParameterSweepConfig) -> list[ExperimentConfig]:
        varied = tuple(_varied_parameters(config))
        if config.mode is SweepMode.FULL_FACTORIAL:
            combinations = product(*(config.parameter_values[name] for name in PARAMETER_ORDER))
            rows = [dict(zip(PARAMETER_ORDER, values, strict=True)) for values in combinations]
            roles = ["SWEEP"] * len(rows)
        else:
            assert config.baseline is not None
            baseline = config.baseline.to_dict()
            rows = [baseline]
            roles = ["BASELINE"]
            for name in PARAMETER_ORDER:
                seen: set[object] = set()
                for value in config.parameter_values[name]:
                    if value == baseline[name] or value in seen:
                        continue
                    seen.add(value)
                    rows.append({**baseline, name: value})
                    roles.append("SWEEP")

        return [
            self._experiment(row, role, config, varied)
            for row, role in zip(rows, roles, strict=True)
        ]

    @staticmethod
    def _experiment(
        values: dict[str, object],
        role: str,
        config: ParameterSweepConfig,
        varied: tuple[str, ...],
    ) -> ExperimentConfig:
        quality = str(values["feature_detection_quality"])
        features = int(values["max_features_per_image"])
        overlap = str(values["image_overlap"])
        reprojection = float(values["max_feature_reprojection_error"])
        machine_name = f"Q{quality}_F{features}_O{overlap}_R{reprojection:.1f}"
        display_features = (
            f"{features // 1000}k" if features >= 1000 and features % 1000 == 0 else str(features)
        )
        return ExperimentConfig(
            name=f"{quality} | {display_features} | {overlap} | {reprojection:.1f}px",
            machine_name=machine_name,
            feature_detection_quality=quality,
            max_features_per_image=features,
            image_overlap=overlap,
            max_feature_reprojection_error=reprojection,
            experiment_role=role,
            sweep_id=config.sweep_id,
            sweep_mode=config.mode.value,
            generated_at=config.generated_at,
            baseline_config=config.baseline.to_dict() if config.baseline else None,
            varied_parameters=varied,
        )

    @staticmethod
    def definition(
        config: ParameterSweepConfig, experiments: Iterable[ExperimentConfig]
    ) -> SweepDefinition:
        items = list(experiments)
        varied = _varied_parameters(config)
        return SweepDefinition(config, [item.experiment_id for item in items], varied)


def partition_duplicates(
    generated: Iterable[ExperimentConfig], existing: Iterable[ExperimentConfig]
) -> tuple[list[ExperimentConfig], list[ExperimentConfig]]:
    signatures = {item.parameter_signature for item in existing}
    unique: list[ExperimentConfig] = []
    duplicates: list[ExperimentConfig] = []
    for item in generated:
        target = duplicates if item.parameter_signature in signatures else unique
        target.append(item)
        signatures.add(item.parameter_signature)
    return unique, duplicates


def _varied_parameters(config: ParameterSweepConfig) -> list[str]:
    if config.mode is SweepMode.FULL_FACTORIAL:
        return [name for name, values in config.parameter_values.items() if len(values) > 1]
    assert config.baseline is not None
    baseline = config.baseline.to_dict()
    return [
        name for name, values in config.parameter_values.items()
        if any(value != baseline[name] for value in values)
    ]


def duplicate_with_new_id(config: ExperimentConfig, *, name: str | None = None) -> ExperimentConfig:
    """Create an independent manual copy without retaining sweep identity."""
    from uuid import uuid4

    return replace(
        config,
        name=name or f"{config.name} 副本",
        experiment_id=f"exp_{uuid4().hex[:12]}",
        experiment_role="MANUAL",
        sweep_id=None,
        sweep_mode=None,
        generated_at=None,
        baseline_config=None,
        varied_parameters=(),
    )
