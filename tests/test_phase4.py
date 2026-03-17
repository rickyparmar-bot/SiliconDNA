"""SiliconDNA Tests - DNA Storage and ML Governance"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bio_simulation.dna_storage import DNAStorageEncoder, HelixMapper, Nucleotide
from ml.governance import GovernanceMatrix, DigitalDNA, ChromosomeType


class TestDNAStorageEncoder:
    """Test DNA encoding and decoding algorithms."""

    def setup_method(self):
        self.encoder = DNAStorageEncoder()

    def test_encode_binary_to_dna(self):
        """Test binary data encoding to DNA sequence."""
        test_data = b"Hello"
        dna_sequence = self.encoder.encode(test_data)

        assert isinstance(dna_sequence, str)
        assert all(c in "ATCG" for c in dna_sequence)
        assert len(dna_sequence) == len(test_data) * 4

    def test_decode_dna_to_binary(self):
        """Test DNA sequence decoding back to binary."""
        test_data = b"Test"
        dna_sequence = self.encoder.encode(test_data)
        decoded = self.encoder.decode(dna_sequence)

        assert decoded == test_data

    def test_encode_decode_roundtrip(self):
        """Test complete encode-decode cycle."""
        original = b"Project SiliconDNA"
        encoded = self.encoder.encode(original)
        decoded = self.encoder.decode(encoded)

        assert decoded == original

    def test_calculate_density(self):
        """Test storage density calculations."""
        metrics = self.encoder.calculate_density(1000)

        assert metrics.base_pairs == 1000
        assert metrics.bits_per_base == 2
        assert metrics.total_bits == 2000
        assert metrics.total_bytes == 250

    def test_compare_to_silicon(self):
        """Test comparison to silicon storage."""
        comparison = self.encoder.compare_to_silicon(1.0)

        assert comparison["data_size_gb"] == 1.0
        assert comparison["dna_needed_grams"] > 0
        assert comparison["improvement_factor"] > 1

    def test_validate_sequence(self):
        """Test DNA sequence validation."""
        valid_seq = "ATCGATCG"
        is_valid, errors = self.encoder.validate_sequence(valid_seq)

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_nucleotides(self):
        """Test detection of invalid nucleotides."""
        invalid_seq = "ATCGXYZ"
        is_valid, errors = self.encoder.validate_sequence(invalid_seq)

        assert is_valid is False
        assert len(errors) > 0


class TestHelixMapper:
    """Test 3D helix spatial mapping."""

    def setup_method(self):
        self.mapper = HelixMapper()

    def test_map_position(self):
        """Test 3D position calculation."""
        position = self.mapper.map_position(0)

        assert "x" in position
        assert "y" in position
        assert "z" in position
        assert "angle" in position

    def test_calculate_access_time(self):
        """Test sequential access time calculation."""
        access_time = self.mapper.calculate_access_time(0, 10)

        assert access_time > 0

    def test_spatial_density(self):
        """Test spatial density calculation."""
        density = self.mapper.get_spatial_density(100)

        assert "volume_nm3" in density
        assert density["bases_per_nm3"] > 0


class TestGovernanceMatrix:
    """Test ML governance validation."""

    def setup_method(self):
        self.governance = GovernanceMatrix()

    def test_model_evaluation_pass(self):
        """Test model passes governance checks."""
        metrics = {
            "accuracy": 0.9,
            "prediction_variance": 0.1,
            "model_complexity": 0.7,
            "inference_speed_ms": 50,
            "drift_score": 0.1,
            "error_rate": 0.01,
            "user_satisfaction": 0.9,
            "community_adoption": 0.8,
        }

        dna = self.governance.evaluate_model(metrics, dry_run=True)

        assert isinstance(dna, DigitalDNA)
        assert dna.overall_score > 0

    def test_model_evaluation_fail(self):
        """Test model fails governance with poor metrics."""
        metrics = {
            "accuracy": 0.3,
            "prediction_variance": 2.0,
            "model_complexity": 0.2,
            "inference_speed_ms": 500,
            "drift_score": 0.9,
            "error_rate": 0.5,
            "user_satisfaction": 0.2,
            "community_adoption": 0.1,
        }

        dna = self.governance.evaluate_model(metrics, dry_run=True)

        assert dna.is_valid is False

    def test_chromosome_thresholds(self):
        """Test individual chromosome evaluation."""
        metrics = {
            "accuracy": 0.8,
            "prediction_variance": 0.2,
            "model_complexity": 0.6,
            "inference_speed_ms": 30,
            "drift_score": 0.2,
            "error_rate": 0.02,
            "user_satisfaction": 0.8,
            "community_adoption": 0.7,
        }

        dna = self.governance.evaluate_model(metrics, dry_run=True)

        assert ChromosomeType.ADAPTABILITY in dna.chromosomes
        assert ChromosomeType.TECHNOLOGY in dna.chromosomes
        assert ChromosomeType.GOVERNANCE in dna.chromosomes
        assert ChromosomeType.CULTURE in dna.chromosomes

    def test_governance_summary(self):
        """Test governance summary generation."""
        summary = self.governance.get_governance_summary()

        assert "total_validations" in summary

    def test_promote_model(self):
        """Test model promotion logic."""
        metrics = {
            "accuracy": 0.95,
            "prediction_variance": 0.05,
            "model_complexity": 0.8,
            "inference_speed_ms": 20,
            "drift_score": 0.05,
            "error_rate": 0.005,
            "user_satisfaction": 0.95,
            "community_adoption": 0.9,
        }

        dna = self.governance.evaluate_model(metrics, dry_run=True)
        should_promote = self.governance.promote_model(dna)

        assert should_promote is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
