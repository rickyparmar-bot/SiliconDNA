"""SiliconDNA Bio-Simulation - DNA Storage Encoding"""

import logging
import math
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


logger = logging.getLogger("silicon_dna.bio_simulation.dna_storage")


class Nucleotide:
    ADENINE = "A"
    THYMINE = "T"
    CYTOSINE = "C"
    GUANINE = "G"

    COMPLEMENT = {
        "A": "T",
        "T": "A",
        "C": "G",
        "G": "C",
    }


@dataclass
class DNAStorageMetrics:
    base_pairs: int
    bits_per_base: int
    total_bits: int
    total_bytes: int
    density_grams_per_byte: float
    theoretical_capacity_grams: float


class DNAStorageEncoder:
    """
    Encode binary data into pseudo-nucleic acid sequences.
    Simulates ultra-high-density biological storage (10^21 bases/gram).
    """

    def __init__(self):
        self.nucleotides = [
            Nucleotide.ADENINE,
            Nucleotide.THYMINE,
            Nucleotide.CYTOSINE,
            Nucleotide.GUANINE,
        ]

    def encode(self, binary_data: bytes) -> str:
        """
        Encode binary data to DNA sequence (A/T/C/G).

        Args:
            binary_data: Raw binary data to encode

        Returns:
            DNA sequence string
        """
        binary_string = "".join(format(byte, "08b") for byte in binary_data)

        dna_sequence = []
        for i in range(0, len(binary_string), 2):
            if i + 2 <= len(binary_string):
                bits = binary_string[i : i + 2]
                nucleotide = self._bits_to_nucleotide(bits)
                dna_sequence.append(nucleotide)

        return "".join(dna_sequence)

    def decode(self, dna_sequence: str) -> bytes:
        """
        Decode DNA sequence back to binary.

        Args:
            dna_sequence: DNA sequence string (A/T/C/G)

        Returns:
            Original binary data
        """
        if not all(c in "ATCG" for c in dna_sequence.upper()):
            raise ValueError("Invalid DNA sequence")

        binary_string = ""
        for nucleotide in dna_sequence.upper():
            bits = self._nucleotide_to_bits(nucleotide)
            binary_string += bits

        bytes_list = []
        for i in range(0, len(binary_string), 8):
            if i + 8 <= len(binary_string):
                byte_bits = binary_string[i : i + 8]
                byte_value = int(byte_bits, 2)
                bytes_list.append(byte_value)

        return bytes(bytes_list)

    def _bits_to_nucleotide(self, bits: str) -> str:
        """Convert 2 bits to nucleotide."""
        mapping = {
            "00": Nucleotide.ADENINE,
            "01": Nucleotide.THYMINE,
            "10": Nucleotide.CYTOSINE,
            "11": Nucleotide.GUANINE,
        }
        return mapping.get(bits, Nucleotide.ADENINE)

    def _nucleotide_to_bits(self, nucleotide: str) -> str:
        """Convert nucleotide to 2 bits."""
        mapping = {
            Nucleotide.ADENINE: "00",
            Nucleotide.THYMINE: "01",
            Nucleotide.CYTOSINE: "10",
            Nucleotide.GUANINE: "11",
        }
        return mapping.get(nucleotide, "00")

    def calculate_density(self, base_pairs: int) -> DNAStorageMetrics:
        """
        Calculate storage density metrics.

        Args:
            base_pairs: Number of base pairs

        Returns:
            DNAStorageMetrics with density calculations
        """
        bits_per_base = 2
        total_bits = base_pairs * bits_per_base
        total_bytes = total_bits // 8

        bases_per_gram = 10**21
        grams_per_base = 1 / bases_per_gram

        grams_per_byte = grams_per_base * 8
        theoretical_capacity_grams = bases_per_gram / 8 / (1024**3)

        return DNAStorageMetrics(
            base_pairs=base_pairs,
            bits_per_base=bits_per_base,
            total_bits=total_bits,
            total_bytes=total_bytes,
            density_grams_per_byte=grams_per_byte,
            theoretical_capacity_grams=theoretical_capacity_grams,
        )

    def compare_to_silicon(self, data_size_gb: float) -> Dict[str, Any]:
        """
        Compare DNA storage to modern SSD.

        Args:
            data_size_gb: Data size in gigabytes

        Returns:
            Comparison metrics
        """
        ssd_density_gb_per_gram = 50

        dna_needed_grams = data_size_gb / 215_000_000
        ssd_needed_grams = data_size_gb / ssd_density_gb_per_gram

        return {
            "data_size_gb": data_size_gb,
            "dna_needed_grams": dna_needed_grams,
            "ssd_needed_grams": ssd_needed_grams,
            "improvement_factor": ssd_needed_grams / dna_needed_grams
            if dna_needed_grams > 0
            else 0,
        }

    def validate_sequence(self, dna_sequence: str) -> Tuple[bool, List[str]]:
        """
        Validate DNA sequence integrity.

        Args:
            dna_sequence: DNA sequence to validate

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        if not dna_sequence:
            errors.append("Empty sequence")
            return False, errors

        invalid_chars = set(c for c in dna_sequence.upper() if c not in "ATCG")
        if invalid_chars:
            errors.append(f"Invalid nucleotides: {invalid_chars}")

        if len(dna_sequence) % 2 != 0:
            errors.append("Sequence length not divisible by 2 (data loss possible)")

        return len(errors) == 0, errors


class HelixMapper:
    """
    Map 3D spatial access patterns for DNA storage.
    """

    def __init__(self, helix_radius_nm: float = 1.0, base_pairs_per_turn: int = 10):
        self.helix_radius_nm = helix_radius_nm
        self.base_pairs_per_turn = base_pairs_per_turn

    def map_position(self, index: int) -> Dict[str, float]:
        """
        Calculate 3D position in helix structure.

        Args:
            index: Position index in sequence

        Returns:
            Dictionary with x, y, z coordinates in nanometers
        """
        angle = (
            (index % self.base_pairs_per_turn) / self.base_pairs_per_turn * 2 * math.pi
        )
        z = index * 0.34

        x = self.helix_radius_nm * math.cos(angle)
        y = self.helix_radius_nm * math.sin(angle)

        return {"x": x, "y": y, "z": z, "angle": angle}

    def calculate_access_time(self, start_index: int, end_index: int) -> float:
        """
        Estimate sequential access time between positions.

        Args:
            start_index: Starting position
            end_index: Ending position

        Returns:
            Estimated time in nanoseconds
        """
        distance = abs(end_index - start_index)
        return distance * 0.34

    def get_spatial_density(self, sequence_length: int) -> Dict[str, float]:
        """
        Calculate spatial density of stored data.

        Args:
            sequence_length: Length of DNA sequence

        Returns:
            Spatial density metrics
        """
        max_z = sequence_length * 0.34
        helix_length_nm = max_z

        volume_nm3 = math.pi * (self.helix_radius_nm**2) * helix_length_nm

        return {
            "volume_nm3": volume_nm3,
            "bases_per_nm3": sequence_length / volume_nm3 if volume_nm3 > 0 else 0,
            "bits_per_nm3": (sequence_length * 2) / volume_nm3 if volume_nm3 > 0 else 0,
        }
