# 🧬 SiliconDNA: Software-Defined 8-Bit CPU

![Architecture](https://img.shields.io/badge/Architecture-8--Bit-red) ![Primitive](https://img.shields.io/badge/Logic-NAND--Only-orange) ![Language](https://img.shields.io/badge/Python-3.14-yellow)

SiliconDNA is a functional 8-bit CPU architecture built entirely from a single logical primitive: the **NAND gate**. It explores the fundamental bridge between Boolean logic and recursive computation.

## 🚀 Architectural Design
This project rejects high-level arithmetic abstractions. Every operation is built from the ground up using simulated electrical switches.

### 🛠️ Key Systems
- **The ALU:** A Ripple Carry Adder built by chaining software-defined half-adders and full-adders.
- **Von Neumann RAM:** A 256-byte unified memory space where the program instructions and data cohabitate.
- **Control Unit:** A hardware-accurate Fetch-Decode-Execute cycle loop.

---

## 📜 Instruction Set (ISA)
| Opcode | Mnemonic | Description |
| :--- | :--- | :--- |
| `0x01` | `LOAD_A` | Load value from memory address into Accumulator |
| `0x02` | `STORE_A` | Store Accumulator value into memory address |
| `0x03` | `ADD_B` | Add ACC and REG_B (NAND-logic addition) |
| `0x04` | `LOAD_B` | Load value into secondary Register B |
| `0xFF` | `HALT` | Terminate program execution |

## 💻 How to Run
1. **Run the CPU:** Execute the processor script which loads a sample program (Addition or Fibonacci).
   ```bash
   python3 processor.py
   ```
2. **Assemble Custom Code:** (Coming Soon)
   ```bash
   python3 assembler.py my_program.asm
   ```

---

## 📂 Project Structure
```text
SiliconDNA/
├── processor.py    # Main CPU Execution Loop
├── cpu_logic.py    # NAND-based logical gates & ALU
├── assembler.py    # Mnemonic to Binary converter
├── fibonacci.py    # Sample algorithm implementation
└── README.md       # Surface documentation
```

## 🗺️ Future Research
- [ ] **Multi-Core Simulation:** Distributing logic across multiple virtual sockets.
- [ ] **Graphic Output:** Building a 16x16 pixel frame buffer.
- [ ] **Machine Learning on NAND:** Implementing a perceptron using only bitwise logic.

---
