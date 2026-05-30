#!/usr/bin/env python3
"""
Advanced Spectral Tests for ECDLP Acceleration (256-bit Fixed)
Tests: Local Correlation (Clustered), KNN, Bit Prediction (ML), Component-wise Correlation
"""

import numpy as np
from ecdsa import SECP256k1, SigningKey
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import cdist
from scipy import stats
import random
import time

# ==========================================================
# CONFIG
# ==========================================================
NUM_GLOBAL = 400      # Random samples across full 256-bit space
NUM_LOCAL = 100       # Clustered samples for local test
WINDOW_SIZE = 32
NUM_FREQS = 8

# ==========================================================
# ORACLE
# ==========================================================
class SpectralOracle:
    def __init__(self, window_size=32, num_freqs=8):
        self.window_size = window_size
        self.num_freqs = num_freqs

    def compute_signature(self, point, G):
        x_vals = []
        curr = point
        for _ in range(self.window_size):
            x_vals.append(float(int(curr.x())))
            curr = curr + G
        spectrum = np.fft.fft(np.array(x_vals, dtype=float))
        mags = np.abs(spectrum[1:self.num_freqs+1])
        max_mag = np.max(mags)
        if max_mag > 1e-10:
            mags /= max_mag
        return mags

    def distance(self, s1, s2):
        return np.linalg.norm(s1 - s2)

# ==========================================================
# TEST 1: LOCAL CLUSTER CORRELATION (FIXED)
# ==========================================================
def test_local_cluster(k_local, signatures_local):
    print("\n" + "="*60)
    print("TEST 1: Local Correlation (Clustered ±50 steps)")
    print("="*60)
    
    # Compute distances. Convert to float64 explicitly to avoid object dtype issues
    scalar_dists = np.abs(np.subtract.outer(k_local, k_local)).astype(np.float64)
    spectral_dists = cdist(signatures_local, signatures_local).astype(np.float64)
    
    mask = ~np.eye(len(k_local), dtype=bool)
    sd = scalar_dists[mask]
    sp = spectral_dists[mask]
    
    r, p = stats.pearsonr(sd, sp)
    print(f"Pearson r (local ±50): {r:.4f} (p={p:.2e})")
    
    # KNN within cluster
    nn_indices = np.argsort(spectral_dists, axis=1)[:, 1:6]
    nn_scalar_dists = scalar_dists[np.arange(len(k_local))[:, None], nn_indices]
    avg_nn = np.mean(nn_scalar_dists)
    print(f"Average scalar distance to 5 nearest spectral neighbors: {avg_nn:.2f}")
    
    if r > 0.6 or avg_nn < 10:
        print("   ✅ PROMISING: Strong local structure detected!")
        return True
    print("   ❌ No exploitable local structure.")
    return False

# ==========================================================
# TEST 2: ML BIT PREDICTION (256-bit Safe)
# ==========================================================
def test_bit_prediction(k_vals, signatures):
    print("\n" + "="*60)
    print("TEST 2: ML Bit Prediction (256-bit Keys)")
    print("="*60)
    
    X = np.array(signatures)
    X = StandardScaler().fit_transform(X)
    
    cv = StratifiedShuffleSplit(n_splits=3, test_size=0.2, random_state=42)
    results = {}
    
    for bits in [1, 2, 4, 8]:
        mask = (1 << bits) - 1
        # Top bits (most significant)
        y_top = np.array([int((k >> (256 - bits)) & mask) for k in k_vals], dtype=np.int64)
        # Bottom bits (least significant)
        y_low = np.array([int(k & mask) for k in k_vals], dtype=np.int64)
        
        clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        
        try:
            acc_top = np.mean(cross_val_score(clf, X, y_top, cv=cv, scoring='accuracy'))
        except Exception:
            acc_top = 0.0
            
        try:
            acc_low = np.mean(cross_val_score(clf, X, y_low, cv=cv, scoring='accuracy'))
        except Exception:
            acc_low = 0.0
            
        baseline = 1.0 / (1 << bits)
        results[bits] = (acc_top, acc_low, baseline)
        print(f"   {bits} bits | Top acc: {acc_top:.3f} | Low acc: {acc_low:.3f} | Random: {baseline:.3f}")
        
    max_acc = max([r[0] for r in results.values()] + [r[1] for r in results.values()])
    if max_acc > 0.6:
        print("   ✅ SIGNIFICANT: ML extracts bit information from spectrum!")
        return True
    print("    ML performs at random baseline.")
    return False

# ==========================================================
# TEST 3: COMPONENT-WISE CORRELATION
# ==========================================================
def test_component_correlation(k_vals, signatures):
    print("\n" + "="*60)
    print("TEST 3: Component-wise Correlation (High/Low bits)")
    print("="*60)
    
    S = np.array(signatures)
    shifts = [8, 16, 32, 64]
    best_r = 0
    
    for s in shifts:
        mask = (1 << s) - 1
        # Extract components as float64 for correlation
        low_comp = np.array([float(k & mask) for k in k_vals], dtype=np.float64)
        high_comp = np.array([float((k >> s) & mask) for k in k_vals], dtype=np.float64)
        
        r_low, _ = stats.pearsonr(low_comp, S[:, 0])
        r_high, _ = stats.pearsonr(high_comp, S[:, 0])
        
        print(f"   Shift {s:2d} bits | Low r={r_low:.3f} | High r={r_high:.3f}")
        best_r = max(best_r, abs(r_low), abs(r_high))
        
    if best_r > 0.4:
        print("   ✅ PROMISING: Spectral features correlate with key components!")
        return True
    print("   ❌ No component-wise correlation found.")
    return False

# ==========================================================
# MAIN
# ==========================================================
def main():
    print("🔬 ADVANCED SPECTRAL TESTS (256-BIT KEYS)")
    print(f"Global samples: {NUM_GLOBAL}, Local cluster: {NUM_LOCAL}, Window: {WINDOW_SIZE}")
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    oracle = SpectralOracle(WINDOW_SIZE, NUM_FREQS)
    
    # 1. Global random 256-bit keys
    print(" Generating global signatures (full 256-bit range)...")
    k_global = [random.getrandbits(256) for _ in range(NUM_GLOBAL)]
    sig_global = np.array([oracle.compute_signature(k * G, G) for k in k_global])
    
    # 2. Local clustered keys (around a random center, ±50)
    print("⏳ Generating local cluster signatures (±50 steps)...")
    k_center = random.getrandbits(256)
    k_local = [k_center + random.randint(-50, 50) for _ in range(NUM_LOCAL)]
    sig_local = np.array([oracle.compute_signature(k * G, G) for k in k_local])
    
    t0 = time.time()
    r1 = test_local_cluster(k_local, sig_local)
    r2 = test_bit_prediction(k_global, sig_global)
    r3 = test_component_correlation(k_global, sig_global)
    
    print("\n" + "="*60)
    print("📊 FINAL VERDICT FOR KANGAROO ACCELERATION")
    print("="*60)
    if r1 or r2 or r3:
        print("🚀 AT LEAST ONE TEST SHOWED PROMISE.")
        print("   → Worth implementing hybrid Kangaroo + spectral filter.")
    else:
        print("❌ ALL ADVANCED TESTS FAILED ON 256-BIT KEYS.")
        print("   → Spectral features contain NO exploitable information for ECDLP search.")
        print("   → Hypothesis refuted. Close this research direction.")
    print("="*60)
    print(f"⏱️  Total time: {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()