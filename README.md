# SiliconDNA: A CPU Built from Scratch 🧬🖥️

SiliconDNA is a software-defined 8-bit CPU architecture built entirely from a single logic primitive: the **NAND gate**. This project explores the fundamental bridge between mathematical logic and physical computing.

## 🚀 Architectural Overview
Most software projects rely on high-level abstractions like the `+` operator. SiliconDNA rejects these abstractions, building an entire processing unit from the bottom up.

### Key Components:
*   **The NAND Foundation:** Every logical operation (NOT, AND, OR, XOR) is derived from a single `NAND(a, b)` function.
*   **8-Bit ALU:** An Arithmetic Logic Unit that performs addition and comparisons using a Ripple Carry Adder circuit built from software-defined gates.
*   **Von Neumann Architecture:** A unified memory space (RAM) storing both instructions and data.
*   **Fetch-Decode-Execute Cycle:** A real processor loop that manages the Program Counter (PC) and register states.
*   **Custom ISA & Assembler:** Includes a mnemonic-to-binary assembler to write programs in a human-readable assembly language.

## 🛠️ Instruction Set (ISA)
*   `LOAD_A [addr]` - Load value from RAM to Accumulator.
*   `LOAD_B [addr]` - Load value from RAM to Register B.
*   `ADD_B` - Add Accumulator and Register B (using ALU logic).
*   `STORE_A [addr]` - Save Accumulator value to RAM.
*   `HALT` - Stop execution.

## 🧪 Demonstration
The included `fibonacci.py` script assembles and executes a program to calculate sequences on the virtual silicon, proving the Turing-completeness of the NAND-based architecture.

---
*Developed for the MIT Maker Portfolio 2026. Proving that Compute = Logic.*
