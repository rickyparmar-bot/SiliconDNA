"""SiliconDNA ML - Adaptive Intelligence Core (FreqAI-Style)"""

import asyncio
import logging
import random
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


logger = logging.getLogger("silicon_dna.ml.orchestrator")


class ModelType(Enum):
    LINEAR_REGRESSOR = "linear_regressor"
    RANDOM_FOREST = "random_forest"
    LSTM = "lstm"
    TRANSFORMER = "transformer"


@dataclass
class ModelConfig:
    model_type: ModelType
    retrain_interval_seconds: int = 3600
    lookback_window: int = 1000
    prediction_horizon: int = 10
    dry_run: bool = True


@dataclass
class TrainedModel:
    model_type: ModelType
    parameters: Dict[str, Any]
    accuracy: float
    trained_at: datetime
    validation_score: float


class GeneticOptimizer:
    """
    Parameter-less genetic algorithm for autonomous strategy evolution.
    """

    def __init__(self, population_size: int = 20, mutation_rate: float = 0.1):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.population: List[Dict[str, Any]] = []

    def initialize(self, seed_strategy: Dict[str, Any]):
        """Initialize population from seed strategy."""
        self.population = []
        for _ in range(self.population_size):
            individual = seed_strategy.copy()
            self._mutate(individual)
            self.population.append(individual)

    def _mutate(self, individual: Dict[str, Any]):
        """Apply mutations to individual."""
        for key in individual:
            if isinstance(individual[key], list) and len(individual[key]) > 0:
                if random.random() < self.mutation_rate:
                    idx = random.randint(0, len(individual[key]) - 1)
                    individual[key][idx] += (
                        random.uniform(-0.1, 0.1) * individual[key][idx]
                    )
            elif isinstance(individual[key], (int, float)):
                if random.random() < self.mutation_rate:
                    individual[key] *= random.uniform(0.9, 1.1)

    def evolve(self, fitness_scores: List[float]) -> Dict[str, Any]:
        """Evolve population based on fitness scores."""
        if len(fitness_scores) != len(self.population):
            return self.population[0] if self.population else {}

        sorted_indices = np.argsort(fitness_scores)[::-1]
        survivors = [
            self.population[i] for i in sorted_indices[: self.population_size // 2]
        ]

        new_population = survivors.copy()

        while len(new_population) < self.population_size:
            parent = random.choice(survivors)
            offspring = parent.copy()
            self._mutate(offspring)
            new_population.append(offspring)

        self.population = new_population
        return survivors[0]

    def get_best(self, fitness_scores: List[float]) -> Dict[str, Any]:
        """Get the best individual from population."""
        if not self.population or not fitness_scores:
            return {}
        best_idx = np.argmax(fitness_scores)
        return self.population[best_idx].copy()


class MLOrchestrator:
    """
    Continuous ML retraining loop inspired by FreqAI.
    Fetches telemetry from MongoDB, trains models, handles dry-run validation.
    """

    def __init__(
        self,
        mongodb_manager,
        config: Optional[ModelConfig] = None,
    ):
        self.mongodb = mongodb_manager
        self.config = config or ModelConfig(model_type=ModelType.LINEAR_REGRESSOR)
        self.genetic_optimizer = GeneticOptimizer()

        self._is_running = False
        self._training_task: Optional[asyncio.Task] = None
        self._current_model: Optional[TrainedModel] = None
        self._model_history: List[TrainedModel] = []
        self._strategy_params: Dict[str, Any] = {}

    async def start(self):
        """Start the continuous training loop."""
        if self._is_running:
            logger.warning("ML Orchestrator already running")
            return

        self._is_running = True
        self._training_task = asyncio.create_task(self._training_loop())

        logger.info("ML Orchestrator started")

    async def stop(self):
        """Stop the continuous training loop."""
        self._is_running = False
        if self._training_task:
            self._training_task.cancel()
            try:
                await self._training_task
            except asyncio.CancelledError:
                pass
        logger.info("ML Orchestrator stopped")

    async def _training_loop(self):
        """Main continuous training loop."""
        await asyncio.sleep(5)

        await self._fetch_and_train()

        while self._is_running:
            await asyncio.sleep(self.config.retrain_interval_seconds)

            if not self.config.dry_run:
                await self._fetch_and_train()
            else:
                logger.info("Dry-run mode: Skipping model promotion")

    async def _fetch_and_train(self):
        """Fetch telemetry data and train models."""
        try:
            logger.info("Fetching historical telemetry for training...")

            data = await self._fetch_telemetry()

            if len(data) < 10:
                logger.warning("Insufficient data for training")
                return

            await self._train_model(data)

        except Exception as e:
            logger.error(f"Training failed: {e}")
            if self.mongodb:
                await self.mongodb.log_error(
                    error_type="MLTraining",
                    error_message=str(e),
                    component="MLOrchestrator",
                )

    async def _fetch_telemetry(self) -> List[Dict[str, Any]]:
        """Fetch historical telemetry from MongoDB."""
        if not self.mongodb or not self.mongodb.is_connected:
            return self._generate_synthetic_data(100)

        try:
            cursor = (
                self.mongodb.db.telemetry.find()
                .sort("timestamp", -1)
                .limit(self.config.lookback_window)
            )
            return await cursor.to_list(length=self.config.lookback_window)
        except Exception as e:
            logger.warning(f"Failed to fetch from MongoDB: {e}")
            return self._generate_synthetic_data(100)

    def _generate_synthetic_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate synthetic training data."""
        data = []
        base_time = datetime.utcnow()
        for i in range(count):
            data.append(
                {
                    "metric_name": "synthetic_signal",
                    "value": random.uniform(0, 100),
                    "timestamp": base_time - timedelta(seconds=count - i),
                    "tags": {"source": "synthetic"},
                }
            )
        return data

    async def _train_model(self, data: List[Dict[str, Any]]):
        """Train a model on the fetched data."""
        logger.info(
            f"Training {self.config.model_type.value} on {len(data)} samples..."
        )

        features = np.array([d.get("value", 0) for d in data]).reshape(-1, 1)

        if len(features) > self.config.prediction_horizon:
            targets = features[self.config.prediction_horizon :].flatten()
            features = features[: -self.config.prediction_horizon]
        else:
            targets = features.flatten()

        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import r2_score

        if self.config.model_type == ModelType.LINEAR_REGRESSOR:
            model = LinearRegression()
        elif self.config.model_type == ModelType.RANDOM_FOREST:
            model = RandomForestRegressor(n_estimators=10, max_depth=3)
        else:
            model = LinearRegression()

        model.fit(features[: len(targets)], targets)

        predictions = model.predict(features[: len(targets)])
        accuracy = r2_score(targets, predictions) if len(targets) > 1 else 0.0

        self._current_model = TrainedModel(
            model_type=self.config.model_type,
            parameters=model.get_params() if hasattr(model, "get_params") else {},
            accuracy=accuracy,
            trained_at=datetime.utcnow(),
            validation_score=accuracy,
        )

        self._model_history.append(self._current_model)

        logger.info(f"Model trained with accuracy: {accuracy:.4f}")

        if self.mongodb:
            await self.mongodb.log_telemetry(
                metric_name="ml_model_accuracy",
                value=accuracy,
                tags={"model_type": self.config.model_type.value},
            )

    async def predict(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a prediction using the current model."""
        if not self._current_model:
            logger.warning("No trained model available")
            return None

        try:
            value = input_data.get("value", 0)

            from sklearn.linear_model import LinearRegression
            from sklearn.ensemble import RandomForestRegressor

            if self._current_model.model_type == ModelType.LINEAR_REGRESSOR:
                model = LinearRegression()
            elif self._current_model.model_type == ModelType.RANDOM_FOREST:
                model = RandomForestRegressor(n_estimators=10, max_depth=3)
            else:
                model = LinearRegression()

            model.set_params(**self._current_model.parameters)

            prediction = model.predict([[value]])[0]

            result = {
                "prediction": float(prediction),
                "confidence": float(self._current_model.accuracy),
                "model_type": self._current_model.model_type.value,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if self.mongodb:
                await self.mongodb.log_ml_prediction(
                    model_name=self._current_model.model_type.value,
                    input_features=input_data,
                    prediction=prediction,
                    confidence=self._current_model.accuracy,
                )

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def run_genetic_evolution(self, fitness_function: Callable) -> Dict[str, Any]:
        """
        Run genetic algorithm to evolve strategy parameters.

        Args:
            fitness_function: Function that takes strategy params and returns fitness score

        Returns:
            Best evolved strategy parameters
        """
        if not self._strategy_params:
            self._strategy_params = {
                "learning_rate": [0.01, 0.05, 0.1],
                "lookback": [100, 500, 1000],
                "threshold": [0.5, 0.7, 0.9],
                "patience": [3, 5, 10],
            }
            self.genetic_optimizer.initialize(self._strategy_params)

        fitness_scores = [
            fitness_function(ind) for ind in self.genetic_optimizer.population
        ]

        best_strategy = self.genetic_optimizer.evolve(fitness_scores)

        logger.info(
            f"Genetic evolution complete. Best fitness: {max(fitness_scores):.4f}"
        )

        return best_strategy

    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status."""
        return {
            "is_running": self._is_running,
            "current_model": {
                "type": self._current_model.model_type.value
                if self._current_model
                else None,
                "accuracy": self._current_model.accuracy
                if self._current_model
                else None,
                "trained_at": self._current_model.trained_at.isoformat()
                if self._current_model
                else None,
            },
            "history_count": len(self._model_history),
            "dry_run": self.config.dry_run,
        }
