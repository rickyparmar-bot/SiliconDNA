# SiliconDNA: A CPU Built from Scratch 🧬
# Step 1: The NAND Primitive

def NAND(a, b):
    """The fundamental building block of all modern computing."""
    return 1 if not (a == 1 and b == 1) else 0

# --- DERIVED GATES (Building everything from NAND) ---

def NOT(a):
    return NAND(a, a)

def AND(a, b):
    return NOT(NAND(a, b))

def OR(a, b):
    return NAND(NOT(a), NOT(b))

def XOR(a, b):
    # (A OR B) AND (A NAND B)
    return AND(OR(a, b), NAND(a, b))

# --- ARITHMETIC CIRCUITS ---

def half_adder(a, b):
    """Adds two bits. Returns (sum, carry)."""
    s = XOR(a, b)
    c = AND(a, b)
    return s, c

def full_adder(a, b, cin):
    """Adds three bits (including carry-in). Returns (sum, carry-out)."""
    s1, c1 = half_adder(a, b)
    s2, c2 = half_adder(s1, cin)
    cout = OR(c1, c2)
    return s2, cout

# --- 8-BIT ADDER (Scaling the logic) ---

def add_8bit(A, B):
    """Adds two 8-bit numbers (lists of bits). Returns (Result, overflow)."""
    result = []
    carry = 0
    # Add from Least Significant Bit (right) to Most Significant Bit (left)
    for i in range(7, -1, -1):
        s, carry = full_adder(A[i], B[i], carry)
        result.insert(0, s)
    return result, carry

# --- UTILS ---
def int_to_bits(n):
    return [int(x) for x in bin(n & 0xFF)[2:].zfill(8)]

def bits_to_int(bits):
    return int("".join(map(str, bits)), 2)

if __name__ == "__main__":
    print("🧠 SiliconDNA Initializing...")
    
    # Test our math
    num1, num2 = 42, 17
    bits1 = int_to_bits(num1)
    bits2 = int_to_bits(num2)
    
    res_bits, overflow = add_8bit(bits1, bits2)
    print(f"Logic Proof: {num1} + {num2} = {bits_to_int(res_bits)}")
    
    if bits_to_int(res_bits) == (num1 + num2):
        print("✅ Digital Logic Verified: We have built a working calculator from a single NAND gate.")
