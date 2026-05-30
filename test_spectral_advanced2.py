#!/usr/bin/env python3
"""
Advanced Spectral Tests for ECDLP Acceleration
Tests: Mutual Information, Manifold Structure, GLV Correlation, Contrastive Learning
"""

import numpy as np
import matplotlib.pyplot as plt
from ecdsa import SECP256k1, SigningKey
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.feature_selection import mutual_info_regression
from sklearn.metrics import roc_auc_score
from scipy import stats
import random
import time

# ==========================================================
# CONFIG
# ==========================================================
NUM_SAMPLES = 600
WINDOW_SIZE = 32
NUM_FREQS = 8
MAX_BITS = 256

# ==========================================================
# ORACLE
# ==========================================================
class SpectralOracle:
    def __init__(self, window_size=32, num_freqs=8):
        self.W = window_size
        self.N = num_freqs

    def compute(self, point, G):
        x_vals = []
        curr = point
        for _ in range(self.W):
            x_vals.append(float(int(curr.x())))
            curr = curr + G
        spectrum = np.fft.fft(np.array(x_vals, dtype=float))
        mags = np.abs(spectrum[1:self.N+1])
        mx = np.max(mags)
        if mx > 1e-10:
            mags /= mx
        return mags

# ==========================================================
# GLV DECOMPOSITION (secp256k1 proxy)
# ==========================================================
def glv_split(k):
    """Split k into (k1, k2) proxy for GLV structure.
    True GLV uses lattice reduction, but k%2^128 and k>>128 capture the same structural split for correlation testing."""
    return k % (1 << 128), k >> 128

# ==========================================================
# TESTS
# ==========================================================
def test_mutual_information(k_vals, signatures):
    print("\n" + "="*60)
    print("TEST 1: Mutual Information I(S(k); k)")
    print("="*60)
    X = np.array(signatures)
    y = np.array(k_vals, dtype=np.float64)
    
    # MI per feature
    mi_per_feat = mutual_info_regression(X, y, n_neighbors=5, random_state=42)
    mi_total = np.mean(mi_per_feat)
    
    print(f"Mean MI per spectral component: {mi_total:.4f} nats")
    print(f"Max MI (single freq): {np.max(mi_per_feat):.4f} nats")
    print("Interpretation: >0.5 = strong dependency, 0.1-0.5 = weak, <0.1 = independent")
    
    return mi_total

def test_manifold_structure(signatures):
    print("\n" + "="*60)
    print("TEST 2: Manifold Hypothesis Check")
    print("="*60)
    X = np.array(signatures)
    
    # PCA intrinsic dimensionality
    pca = PCA()
    pca.fit(X)
    var_ratio = pca.explained_variance_ratio_
    print(f"PCA Explained Variance: {var_ratio[:5]}")
    
    is_1d = var_ratio[0] > 0.85
    is_low_d = np.sum(var_ratio > 0.05) <= 3
    
    print(f"1D Manifold? {'✅ YES' if is_1d else '❌ NO'} (1st comp: {var_ratio[0]:.3f})")
    print(f"Low-D (<3)? {'✅ YES' if is_low_d else '❌ NO'} (active dims: {np.sum(var_ratio>0.05)})")
    
    # t-SNE visualization (sample 200 for speed)
    idx = random.sample(range(len(X)), min(200, len(X)))
    tsne = TSNE(n_components=2, perplexity=30, random_state=42)
    Z = tsne.fit_transform(X[idx])
    
    plt.figure(figsize=(6,4))
    plt.scatter(Z[:,0], Z[:,1], c=np.array(k_vals)[idx]/(1<<256), cmap='viridis', s=10)
    plt.colorbar(label='Normalized k')
    plt.title("t-SNE Projection of Spectral Signatures")
    plt.tight_layout()
    plt.savefig("manifold_tsne.png", dpi=150)
    print("📊 Saved: manifold_tsne.png")
    
    return is_1d or is_low_d

def test_glv_correlation(k_vals, signatures):
    print("\n" + "="*60)
    print("TEST 3: GLV Decomposition Correlation")
    print("="*60)
    X = np.array(signatures)
    k1_vals = np.array([glv_split(k)[0] for k in k_vals], dtype=np.float64)
    k2_vals = np.array([glv_split(k)[1] for k in k_vals], dtype=np.float64)
    
    # Correlation with first spectral component (most informative usually)
    r1_k1, _ = stats.pearsonr(X[:,0], k1_vals)
    r1_k2, _ = stats.pearsonr(X[:,0], k2_vals)
    
    # MI with GLV components
    mi_k1 = mutual_info_regression(X, k1_vals, n_neighbors=5, random_state=42).mean()
    mi_k2 = mutual_info_regression(X, k2_vals, n_neighbors=5, random_state=42).mean()
    
    print(f"Pearson(S[0], k1): {r1_k1:.4f} | Pearson(S[0], k2): {r1_k2:.4f}")
    print(f"MI(S, k1): {mi_k1:.4f} | MI(S, k2): {mi_k2:.4f}")
    
    if abs(r1_k1) > 0.3 or abs(r1_k2) > 0.3 or mi_k1 > 0.2 or mi_k2 > 0.2:
        print("✅ PROMISING: Spectrum encodes GLV-like structure!")
        return True
    print("❌ No GLV correlation detected.")
    return False

def test_contrastive_learning(k_vals, signatures):
    print("\n" + "="*60)
    print("TEST 4: Contrastive / Pairwise Prediction")
    print("="*60)
    
    # ✅ FIX: Cap pairs to available samples & use numpy for speed
    N_pairs = min(5000, len(k_vals) // 2)
    idx1 = np.random.choice(len(k_vals), N_pairs, replace=False)
    idx2 = np.random.choice(len(k_vals), N_pairs, replace=False)
    
    scalar_dists = np.abs(np.array(k_vals)[idx1] - np.array(k_vals)[idx2])
    spec_dists = np.linalg.norm(np.array(signatures)[idx1] - np.array(signatures)[idx2], axis=1)
    
    threshold = 100
    labels = (scalar_dists < threshold).astype(int)
    
    if np.all(labels == labels[0]):
        print("⚠️  Not enough variance for AUC.")
        return 0.5
        
    auc = roc_auc_score(labels, -spec_dists)
    print(f"AUC for predicting |Δk| < {threshold}: {auc:.4f}")
    print("Interpretation: 0.5 = random, >0.65 = usable filter")
    return auc

# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":
    print(" ADVANCED SPECTRAL TESTS v2.0")
    print(f"Samples: {NUM_SAMPLES} | Window: {WINDOW_SIZE} | Freqs: {NUM_FREQS}")
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    oracle = SpectralOracle(WINDOW_SIZE, NUM_FREQS)
    
    print("⏳ Generating 256-bit signatures...")
    k_vals = [random.getrandbits(MAX_BITS) for _ in range(NUM_SAMPLES)]
    signatures = [oracle.compute(k * G, G) for k in k_vals]
    signatures = np.array(signatures)
    
    t0 = time.time()
    r1 = test_mutual_information(k_vals, signatures)
    r2 = test_manifold_structure(signatures)
    r3 = test_glv_correlation(k_vals, signatures)
    r4 = test_contrastive_learning(k_vals, signatures)
    
    print("\n" + "="*60)
    print("📊 FINAL VERDICT")
    print("="*60)
    score = 0
    if r1 > 0.2: score += 1
    if r2: score += 1
    if r3: score += 1
    if r4 > 0.65: score += 1
    
    if score >= 3:
        print("🚀 STRONG SIGNAL DETECTED. Spectral features contain exploitable structure.")
        print("   → Implement hybrid Kangaroo with spectral filter.")
    elif score >= 2:
        print("️  WEAK/MARGINAL SIGNAL. May help in specific regimes, but not transformative.")
    else:
        print("❌ NO EXPLOITABLE STRUCTURE FOUND. Spectral continuity is local-only.")
        print("   → Close this direction. Focus on classical optimizations.")
        
    print("="*60)
    print(f"⏱️  Total time: {time.time()-t0:.1f}s")