# SiliconDNA Assembler ✍️

OPCODES = {
    "LOAD_A": 0x01,
    "STORE_A": 0x02,
    "ADD_B": 0x03,
    "LOAD_B": 0x04,
    "HALT": 0xFF
}

def assemble(source_code):
    binary = []
    lines = source_code.strip().split("\n")
    for line in lines:
        parts = line.split()
        if not parts: continue
        
        mnemonic = parts[0].upper()
        if mnemonic in OPCODES:
            binary.append(OPCODES[mnemonic])
            if len(parts) > 1: # It has an address argument
                binary.append(int(parts[1]))
        else:
            raise SyntaxError(f"Unknown Instruction: {mnemonic}")
    return binary

if __name__ == "__main__":
    code = """
    LOAD_A 10
    LOAD_B 11
    ADD_B
    STORE_A 12
    HALT
    """
    machine_code = assemble(code)
    print(f"Machine Code Generated: {machine_code}")
