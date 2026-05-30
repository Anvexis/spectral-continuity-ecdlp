#!/usr/bin/env python3
"""
Test 1: Raw x-coordinate time-series learning (no FFT)
"""
import numpy as np
from ecdsa import SECP256k1, SigningKey
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
import random

def generate_sequences(k_start, length, G):
    """Generate raw x-coordinate sequence"""
    xs = []
    curr = k_start * G
    for _ in range(length):
        xs.append(int(curr.x()))
        curr = curr + G
    return np.array(xs, dtype=np.float64)

def test_raw_sequence_prediction():
    print("="*60)
    print("TEST 1: Raw Time-Series Prediction (No FFT)")
    print("="*60)
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    
    # Generate dataset: windows of x-coords -> target = k mod 256
    WINDOW = 32
    NUM_SAMPLES = 500
    X, y = [], []
    
    for _ in range(NUM_SAMPLES):
        k = random.getrandbits(256)
        seq = generate_sequences(k, WINDOW, G)
        X.append(seq)
        y.append(k % 256)  # Predict lowest 8 bits
    
    X = np.array(X)
    y = np.array(y)
    X = StandardScaler().fit_transform(X)
    
    # Linear probe (Ridge regression)
    clf = Ridge(alpha=1.0)
    scores = cross_val_score(clf, X, y, cv=5, scoring='r2')
    r2_mean = np.mean(scores)
    
    # Classification accuracy baseline
    from sklearn.ensemble import RandomForestClassifier
    clf_clf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
    acc = np.mean(cross_val_score(clf_clf, X, y, cv=5, scoring='accuracy'))
    
    print(f"R² (regression on k mod 256): {r2_mean:.4f} (0 = random, 1 = perfect)")
    print(f"Accuracy (classification): {acc:.3f} (baseline = 1/256 ≈ 0.004)")
    
    if r2_mean > 0.1 or acc > 0.05:
        print("✅ PROMISING: Raw sequence contains predictable structure!")
        return True
    print("❌ Raw x-coordinates are cryptographically scrambled. No learning signal.")
    return False

if __name__ == "__main__":
    test_raw_sequence_prediction()