# 🧬 SiliconDNA: Software-Defined 8-Bit CPU

SiliconDNA is a functional 8-bit CPU architecture built entirely from a single logical primitive: the **NAND gate**. This project rejects high-level language operators (like `+` or `-`) to explore how complex mathematical reasoning emerges from raw physical switches.

## 🚀 Architectural Deep Dive
The goal of SiliconDNA is to demonstrate the bridge between **Boolean Logic** and **Turing-Complete Computing**.

### 🛠️ Key Components
- **The NAND Foundation:** Every logical gate (NOT, AND, OR, XOR) is derived in software using only `NAND(a, b)`. There are no "shortcut" operators used in the ALU logic.
- **ALU (Arithmetic Logic Unit):** Features a software-engineered **Ripple Carry Adder** circuit. Addition is performed by chaining 8 full-adders, each composed of discrete NAND-based logic gates.
- **Von Neumann Memory Space:** Implements a unified 256-byte RAM where both program instructions and data live together.
- **Instruction Set Architecture (ISA):**
    - `0x01 LOAD_A`: Load from RAM to Accumulator.
    - `0x02 STORE_A`: Save Accumulator to RAM.
    - `0x03 ADD_B`: Perform ALU addition between ACC and REG_B.
    - `0xFF HALT`: Terminate the machine cycle.
- **The Assembler:** A custom tool that converts human-readable mnemonics into raw binary executables for the SiliconDNA processor.

## 🧪 Demonstration
The repository includes a program to calculate the **Fibonacci Sequence**, proving that the NAND-based architecture is capable of executing complex recursive algorithms.

---
*Part of the MIT Maker Portfolio 2026. Proving that Compute = Logic.* 🧬🖥️
