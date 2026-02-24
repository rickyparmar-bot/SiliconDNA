# SiliconDNA: Fibonacci Challenge 🌀
from processor import SiliconCPU
from assembler import assemble
from cpu_logic import int_to_bits, bits_to_int

def run_fib():
    # Program: Calculate Fibonacci sequence iteratively
    # Note: To keep it simple with our current basic ISA, we add A+B and store it.
    
    source = """
    LOAD_A 20
    LOAD_B 21
    ADD_B
    STORE_A 22
    HALT
    """
    
    binary = assemble(source)
    cpu = SiliconCPU()
    cpu.load_program(binary)
    
    # Init Fibonacci starting values
    cpu.RAM[20] = int_to_bits(1) # Fib(n-1)
    cpu.RAM[21] = int_to_bits(1) # Fib(n-2)
    
    print("🛸 SiliconDNA Running Assembly Program...")
    cpu.run()
    
    res = bits_to_int(cpu.RAM[22])
    print(f"✅ Calculation Complete. 1 + 1 = {res}")

if __name__ == "__main__":
    run_fib()
