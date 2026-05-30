#!/usr/bin/env python3
"""
CRITICAL TEST: Does spectral distance correlate with scalar distance |k1 - k2|?
"""

import numpy as np
import matplotlib.pyplot as plt
from ecdsa import SECP256k1, SigningKey
import random
import time

try:
    from scipy import stats
except ImportError:
    print("ERROR: scipy is not installed.")
    print("Please run: pip install scipy")
    exit(1)

# Configuration
NUM_SAMPLES = 500      # Reduced for speed
WINDOW_SIZE = 32
NUM_FREQS = 8
MAX_K = 10000

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
            mags = mags / max_mag
        return mags
    
    def spectral_distance(self, sig1, sig2):
        return np.linalg.norm(sig1 - sig2)

def main():
    print("=" * 60)
    print("CRITICAL TEST: Spectral vs Scalar Distance")
    print("=" * 60)
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    oracle = SpectralOracle(WINDOW_SIZE, NUM_FREQS)
    
    # 1. Generate random keys and compute signatures
    print(f"Generating {NUM_SAMPLES} signatures...")
    k_values = [random.randint(1, MAX_K) for _ in range(NUM_SAMPLES)]
    signatures = []
    
    start_time = time.time()
    for i, k in enumerate(k_values):
        point = k * G
        sig = oracle.compute_signature(point, G)
        signatures.append(sig)
        
        if (i + 1) % 100 == 0:
            rate = (i + 1) / (time.time() - start_time)
            print(f"  Progress: {i+1}/{NUM_SAMPLES} ({rate:.0f} sig/s)")
    
    # 2. Compute pairwise distances
    print("Computing pairwise distances...")
    scalar_dists = []
    spectral_dists = []
    
    num_pairs = 5000  # Number of random pairs to compare
    for _ in range(num_pairs):
        i, j = random.sample(range(NUM_SAMPLES), 2)
        scalar_dist = abs(k_values[i] - k_values[j])
        spectral_dist = oracle.spectral_distance(signatures[i], signatures[j])
        
        scalar_dists.append(scalar_dist)
        spectral_dists.append(spectral_dist)
    
    scalar_dists = np.array(scalar_dists)
    spectral_dists = np.array(spectral_dists)
    
    # 3. Calculate Correlation
    pearson_r, p_value = stats.pearsonr(scalar_dists, spectral_dists)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Pearson correlation (r): {pearson_r:.4f}")
    print(f"P-value: {p_value:.2e}")
    
    # 4. Interpretation
    if abs(pearson_r) < 0.1:
        print("RESULT: NO CORRELATION")
        print("Kangaroo acceleration: ~0% (Spectral method won't help)")
    elif abs(pearson_r) < 0.3:
        print("RESULT: WEAK CORRELATION")
        print("Potential speedup: 1.1x - 1.5x (Marginal)")
    elif abs(pearson_r) < 0.5:
        print("RESULT: MODERATE CORRELATION")
        print("Potential speedup: 2x - 5x (Interesting!)")
    else:
        print("RESULT: STRONG CORRELATION")
        print("Potential speedup: >10x (Major discovery!)")
    
    print("=" * 60)

if __name__ == "__main__":
    main()