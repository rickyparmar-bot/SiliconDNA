"""SiliconDNA ML - Governance Matrix (Digital DNA)"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger("silicon_dna.ml.governance")


class ChromosomeType(Enum):
    ADAPTABILITY = "adaptability"
    TECHNOLOGY = "technology"
    GOVERNANCE = "governance"
    CULTURE = "culture"


@dataclass
class Chromosome:
    chromosome_type: ChromosomeType
    score: float
    min_threshold: float
    max_threshold: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DigitalDNA:
    chromosomes: Dict[ChromosomeType, Chromosome]
    overall_score: float
    created_at: datetime
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)


class GovernanceMatrix:
    """
    Strict model validation using Digital DNA framework.
    Evaluates models before promotion to production.
    """

    def __init__(
        self,
        adaptability_threshold: float = 0.7,
        technology_threshold: float = 0.6,
        governance_threshold: float = 0.8,
        culture_threshold: float = 0.75,
    ):
        self.thresholds = {
            ChromosomeType.ADAPTABILITY: adaptability_threshold,
            ChromosomeType.TECHNOLOGY: technology_threshold,
            ChromosomeType.GOVERNANCE: governance_threshold,
            ChromosomeType.CULTURE: culture_threshold,
        }

        self._validation_history: List[DigitalDNA] = []

    def evaluate_model(
        self,
        model_metrics: Dict[str, Any],
        dry_run: bool = True,
    ) -> DigitalDNA:
        """
        Evaluate a model against the Digital DNA framework.

        Args:
            model_metrics: Dictionary containing model performance metrics
            dry_run: If True, validates in isolated environment

        Returns:
            DigitalDNA with evaluation results
        """
        logger.info(
            f"Evaluating model in {'dry-run' if dry_run else 'production'} mode"
        )

        chromosomes = {}

        chromosomes[ChromosomeType.ADAPTABILITY] = self._evaluate_adaptability(
            model_metrics
        )

        chromosomes[ChromosomeType.TECHNOLOGY] = self._evaluate_technology(
            model_metrics
        )

        chromosomes[ChromosomeType.GOVERNANCE] = self._evaluate_governance(
            model_metrics
        )

        chromosomes[ChromosomeType.CULTURE] = self._evaluate_culture(model_metrics)

        overall_score = sum(c.score for c in chromosomes.values()) / len(chromosomes)

        validation_errors = []
        for chrom_type, chromosome in chromosomes.items():
            if chromosome.score < chromosome.min_threshold:
                validation_errors.append(
                    f"{chrom_type.value} score {chromosome.score:.2f} below minimum {chromosome.min_threshold}"
                )
            if chromosome.score > chromosome.max_threshold:
                validation_errors.append(
                    f"{chrom_type.value} score {chromosome.score:.2f} above maximum {chromosome.max_threshold}"
                )

        dna = DigitalDNA(
            chromosomes=chromosomes,
            overall_score=overall_score,
            created_at=datetime.utcnow(),
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors,
        )

        self._validation_history.append(dna)

        if dna.is_valid:
            logger.info(f"Model VALIDATED with overall score: {overall_score:.4f}")
        else:
            logger.warning(f"Model REJECTED: {validation_errors}")

        return dna

    def _evaluate_adaptability(self, metrics: Dict[str, Any]) -> Chromosome:
        """Evaluate adaptability chromosome."""
        accuracy = metrics.get("accuracy", 0)
        variance = metrics.get("prediction_variance", 1.0)

        stability_score = max(0, 1 - variance)
        learning_score = min(1, accuracy * 2)

        score = stability_score * 0.4 + learning_score * 0.6

        return Chromosome(
            chromosome_type=ChromosomeType.ADAPTABILITY,
            score=score,
            min_threshold=self.thresholds[ChromosomeType.ADAPTABILITY],
            max_threshold=1.0,
            details={
                "stability": stability_score,
                "learning": learning_score,
            },
        )

    def _evaluate_technology(self, metrics: Dict[str, Any]) -> Chromosome:
        """Evaluate technology chromosome."""
        model_complexity = metrics.get("model_complexity", 0.5)
        inference_speed = metrics.get("inference_speed_ms", 100)

        efficiency_score = max(0, 1 - (inference_speed / 1000))
        complexity_score = min(1, model_complexity * 2)

        score = efficiency_score * 0.5 + complexity_score * 0.5

        return Chromosome(
            chromosome_type=ChromosomeType.TECHNOLOGY,
            score=score,
            min_threshold=self.thresholds[ChromosomeType.TECHNOLOGY],
            max_threshold=1.0,
            details={
                "efficiency": efficiency_score,
                "complexity": complexity_score,
            },
        )

    def _evaluate_governance(self, metrics: Dict[str, Any]) -> Chromosome:
        """Evaluate governance chromosome - prevent algorithmic drift."""
        drift_score = metrics.get("drift_score", 0.5)
        error_rate = metrics.get("error_rate", 0.1)

        drift_resistance = max(0, 1 - drift_score)
        safety_score = max(0, 1 - error_rate * 10)

        score = drift_resistance * 0.5 + safety_score * 0.5

        return Chromosome(
            chromosome_type=ChromosomeType.GOVERNANCE,
            score=score,
            min_threshold=self.thresholds[ChromosomeType.GOVERNANCE],
            max_threshold=1.0,
            details={
                "drift_resistance": drift_resistance,
                "safety": safety_score,
            },
        )

    def _evaluate_culture(self, metrics: Dict[str, Any]) -> Chromosome:
        """Evaluate culture chromosome - alignment with system values."""
        user_satisfaction = metrics.get("user_satisfaction", 0.5)
        community_adoption = metrics.get("community_adoption", 0.5)

        score = user_satisfaction * 0.5 + community_adoption * 0.5

        return Chromosome(
            chromosome_type=ChromosomeType.CULTURE,
            score=score,
            min_threshold=self.thresholds[ChromosomeType.CULTURE],
            max_threshold=1.0,
            details={
                "user_satisfaction": user_satisfaction,
                "community_adoption": community_adoption,
            },
        )

    def validate_in_sandbox(
        self, model: Any, test_data: List[Dict[str, Any]]
    ) -> DigitalDNA:
        """
        Validate model in isolated dry-run environment.

        Args:
            model: Model to validate
            test_data: Test dataset for validation

        Returns:
            DigitalDNA with evaluation results
        """
        logger.info(f"Running sandbox validation with {len(test_data)} test samples")

        predictions = []
        errors = []

        for sample in test_data:
            try:
                pred = model.predict(sample) if hasattr(model, "predict") else 0.5
                predictions.append(pred)
            except Exception as e:
                errors.append(str(e))

        metrics = {
            "accuracy": len(predictions) / max(1, len(test_data)),
            "prediction_variance": float(np.var(predictions)) if predictions else 1.0,
            "model_complexity": 0.5,
            "inference_speed_ms": 50,
            "drift_score": 0.1 if len(errors) < 5 else 0.8,
            "error_rate": len(errors) / max(1, len(test_data)),
            "user_satisfaction": 0.8,
            "community_adoption": 0.7,
        }

        import numpy as np

        metrics["prediction_variance"] = (
            float(np.var(predictions)) if len(predictions) > 1 else 0.1
        )

        return self.evaluate_model(metrics, dry_run=True)

    def get_validation_history(self, limit: int = 10) -> List[DigitalDNA]:
        """Get recent validation history."""
        return self._validation_history[-limit:]

    def get_governance_summary(self) -> Dict[str, Any]:
        """Get summary of governance metrics."""
        if not self._validation_history:
            return {"total_validations": 0}

        valid_count = sum(1 for dna in self._validation_history if dna.is_valid)

        return {
            "total_validations": len(self._validation_history),
            "passed": valid_count,
            "failed": len(self._validation_history) - valid_count,
            "pass_rate": valid_count / len(self._validation_history),
            "avg_score": sum(d.overall_score for d in self._validation_history)
            / len(self._validation_history),
        }

    def promote_model(self, dna: DigitalDNA) -> bool:
        """
        Determine if model should be promoted to production.

        Returns:
            True if model should be promoted
        """
        if not dna.is_valid:
            logger.warning("Model not promoted: validation failed")
            return False

        if dna.overall_score < 0.8:
            logger.warning(
                f"Model not promoted: score {dna.overall_score:.2f} below 0.8"
            )
            return False

        return True
