#!/usr/bin/env python3
"""
Test 2: GLV Endomorphism & Algebraic Structure (FINAL FIX)
"""
import numpy as np
from ecdsa import SECP256k1, SigningKey
from scipy import stats
import random

# secp256k1 GLV lambda
LAMBDA = 0x5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72

def test_glv_structure():
    print("="*60)
    print("TEST 2: GLV Endomorphism & Algebraic Structure")
    print("="*60)
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    n = sk.curve.order  # ✅ order is an attribute, not a method
    
    NUM = 400
    xs_normal, xs_endo = [], []
    
    print(f"⏳ Generating {NUM} points...")
    for _ in range(NUM):
        k = random.getrandbits(256)
        P = k * G
        
        xs_normal.append(int(P.x()))
        
        # Endomorphism proxy: (1 + λ)*G sequence behavior
        k_endo = (k * (1 + LAMBDA)) % n
        P_endo = k_endo * G
        xs_endo.append(int(P_endo.x()))
    
    xs_normal = np.array(xs_normal, dtype=np.float64)
    xs_endo = np.array(xs_endo, dtype=np.float64)
    
    # Statistical comparison
    print("📊 Distribution stats:")
    print(f"Normal x-coords: μ={xs_normal.mean():.2e}, σ={xs_normal.std():.2e}")
    print(f"Endo x-coords:   μ={xs_endo.mean():.2e}, σ={xs_endo.std():.2e}")
    
    # Kolmogorov-Smirnov test
    ks_stat, ks_p = stats.ks_2samp(xs_normal, xs_endo)
    print(f"\nKS Test (distributions equal?): stat={ks_stat:.4f}, p={ks_p:.4f}")
    print("Interpretation: p < 0.01 → distributions differ (structure detected)")
    
    # ✅ FIX: Correlation requires float arrays. Large ints cause dtype=object crash.
    ks = np.array([random.getrandbits(256) for _ in range(NUM)], dtype=np.float64)
    xs_endo_full = []
    for k_float in ks:
        k_int = int(k_float)
        k_endo = (k_int * (1 + LAMBDA)) % n
        P_endo = k_endo * G
        xs_endo_full.append(int(P_endo.x()))
    
    xs_endo_full = np.array(xs_endo_full, dtype=np.float64)
    corr, _ = stats.pearsonr(ks, xs_endo_full)
    
    print(f"Pearson(k, x(φ(P))): {corr:.4f}")
    print("Interpretation: |r| > 0.3 → scalar leaks into x-coords")
    
    if ks_p < 0.01 or abs(corr) > 0.3:
        print("✅ INTERESTING: Endomorphism changes distribution or leaks k!")
        return True
    print("❌ Endomorphism preserves cryptographic scrambling. No structural leak.")
    return False

if __name__ == "__main__":
    test_glv_structure()