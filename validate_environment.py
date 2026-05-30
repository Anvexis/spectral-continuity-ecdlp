#!/usr/bin/env python3
"""Quick validation that the spectral continuity tests will work."""

import numpy as np
from ecdsa import SECP256k1, SigningKey

def main():
    print("🔍 Validating environment for spectral continuity tests...")
    
    # Test 1: ecdsa library
    try:
        sk = SigningKey.generate(curve=SECP256k1)
        G = sk.verifying_key.pubkey.point
        print("✅ ecdsa: OK")
    except Exception as e:
        print(f"❌ ecdsa: {e}")
        return False
    
    # Test 2: NumPy FFT with large integers
    try:
        x_val = float(int((10 * G).x()))
        arr = np.array([x_val] * 32, dtype=float)
        spectrum = np.fft.fft(arr)
        print("✅ NumPy FFT: OK")
    except Exception as e:
        print(f"❌ NumPy FFT: {e}")
        return False
    
    # Test 3: Point arithmetic
    try:
        p1 = 50 * G
        p2 = p1 + G
        p3 = p1 + (-G)  # Test negation
        print("✅ Point arithmetic: OK")
    except Exception as e:
        print(f"❌ Point arithmetic: {e}")
        return False
    
    print("\n🎉 Environment validated! All tests should work.")
    return True

if __name__ == "__main__":
    main()