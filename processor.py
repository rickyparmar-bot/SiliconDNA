# SiliconDNA: The Virtual CPU 🧬
from cpu_logic import add_8bit, int_to_bits, bits_to_int, XOR, NOT, AND

class SiliconCPU:
    def __init__(self):
        self.RAM = [[0]*8 for _ in range(256)] # 256 bytes of memory
        self.ACC = [0]*8                       # Accumulator Register
        self.REG_B = [0]*8                     # Secondary Register
        self.PC = 0                            # Program Counter
        self.running = True

    def load_program(self, binary_data):
        for i, byte in enumerate(binary_data):
            self.RAM[i] = int_to_bits(byte)

    def step(self):
        # 1. FETCH
        instruction_bits = self.RAM[self.PC]
        opcode = bits_to_int(instruction_bits)
        self.PC += 1

        # 2. DECODE & EXECUTE (Instruction Set)
        
        if opcode == 0x01: # LOAD_A [addr]
            addr = bits_to_int(self.RAM[self.PC])
            self.ACC = self.RAM[addr]
            self.PC += 1
            
        elif opcode == 0x02: # STORE_A [addr]
            addr = bits_to_int(self.RAM[self.PC])
            self.RAM[addr] = self.ACC
            self.PC += 1

        elif opcode == 0x03: # ADD_B
            # Real ALU math using our NAND-based logic
            res, _ = add_8bit(self.ACC, self.REG_B)
            self.ACC = res

        elif opcode == 0x04: # LOAD_B [addr]
            addr = bits_to_int(self.RAM[self.PC])
            self.REG_B = self.RAM[addr]
            self.PC += 1

        elif opcode == 0xFF: # HALT
            self.running = False

    def run(self):
        print("🖥️  CPU Booting...")
        while self.running:
            self.step()
        print("🛑 CPU Halted.")

if __name__ == "__main__":
    cpu = SiliconCPU()
    
    # Simple Program: Add two numbers from memory and store result
    # 0x01 (LOAD_A), 0x0A (Address 10)
    # 0x04 (LOAD_B), 0x0B (Address 11)
    # 0x03 (ADD_B)
    # 0x02 (STORE_A), 0x0C (Address 12)
    # 0xFF (HALT)
    
    program = [0x01, 10, 0x04, 11, 0x03, 0x02, 12, 0xFF]
    cpu.load_program(program)
    
    # Initialize Data in RAM
    cpu.RAM[10] = int_to_bits(100) # Number 1
    cpu.RAM[11] = int_to_bits(50)  # Number 2
    
    cpu.run()
    
    result = bits_to_int(cpu.RAM[12])
    print(f"✨ Result in RAM[12]: {result}")
