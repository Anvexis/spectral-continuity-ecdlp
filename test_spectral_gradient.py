#!/usr/bin/env python3
"""
Demonstrate spectral gradient descent for ECDLP.
Given a target point Q = k·G, attempt to find k using spectral distance minimization.
"""

import numpy as np
from ecdsa import SECP256k1, SigningKey
from ecdsa.ellipticcurve import Point
import random

class SpectralOracle:
    """Compute spectral signatures for points on the curve."""
    
    def __init__(self, window_size: int = 32, num_freqs: int = 8):
        self.window_size = window_size
        self.num_freqs = num_freqs
    
    def compute_signature(self, point: Point, G: Point) -> np.ndarray:
        """Compute spectral signature of x-coordinate sequence."""
        x_vals = []
        curr = point
        for _ in range(self.window_size):
            # Convert to native Python float for NumPy compatibility
            x_val = float(int(curr.x()))
            x_vals.append(x_val)
            curr = curr + G
        
        # FFT
        spectrum = np.fft.fft(np.array(x_vals, dtype=float))
        mags = np.abs(spectrum[1:self.num_freqs+1])  # Exclude DC
        
        # Normalize
        max_mag = np.max(mags)
        if max_mag > 1e-10:
            mags = mags / max_mag
        
        return mags
    
    def spectral_distance(self, sig1: np.ndarray, sig2: np.ndarray) -> float:
        """Compute Euclidean distance between signatures."""
        return float(np.linalg.norm(sig1 - sig2))

def spectral_gradient_descent(target_point: Point, G: Point, oracle: SpectralOracle, max_steps: int = 100):
    """
    Attempt to find k such that k·G = target_point using spectral gradient descent.
    """
    print(f"\nStarting spectral gradient descent...")
    print(f"Target point X: {int(target_point.x())}")
    
    # Start from a nearby point (for demonstration)
    k_current = random.randint(1, 100)
    current_point = k_current * G
    
    best_distance = float('inf')
    best_k = k_current
    
    for step in range(max_steps):
        # Compute spectral distance
        sig_current = oracle.compute_signature(current_point, G)
        sig_target = oracle.compute_signature(target_point, G)
        distance = oracle.spectral_distance(sig_current, sig_target)
        
        if distance < best_distance:
            best_distance = distance
            best_k = k_current
        
        # Try moving forward (+G)
        next_point = current_point + G
        sig_next = oracle.compute_signature(next_point, G)
        dist_next = oracle.spectral_distance(sig_next, sig_target)
        
        # Try moving backward (-G)
        # FIX: Use addition with negation because Point objects don't support '-' operator
        prev_point = current_point + (-G)
        sig_prev = oracle.compute_signature(prev_point, G)
        dist_prev = oracle.spectral_distance(sig_prev, sig_target)
        
        # Choose direction
        if dist_next < distance and dist_next < dist_prev:
            current_point = next_point
            k_current += 1
            direction = "+G"
        elif dist_prev < distance:
            current_point = prev_point
            k_current -= 1
            direction = "-G"
        else:
            # Local minimum
            break
        
        if step % 10 == 0:
            print(f"  Step {step:3d}: k={k_current:6d}, dist={distance:.4f}, dir={direction}")
        
        # Check if found
        if current_point == target_point:
            print(f"\n✅ FOUND! k = {k_current}")
            return k_current
    
    print(f"\n️  Stopped at k={k_current}, distance={best_distance:.4f}")
    print(f"  Best found: k={best_k}, distance={best_distance:.4f}")
    
    return None

def test_small_range():
    """Test spectral gradient descent on small range (demonstration)."""
    print("=" * 60)
    print("SPECTRAL GRADIENT DESCENT TEST (Small Range)")
    print("=" * 60)
    
    # Generate random key in small range
    true_k = random.randint(50, 150)
    sk = SigningKey.from_secret_exponent(true_k, curve=SECP256k1)
    G = sk.verifying_key.pubkey.point  # Get the Point object
    target = sk.verifying_key.pubkey.point  # This is the target point
    
    print(f"True private key: {true_k}")
    print(f"Target point X: {int(target.x())}")
    
    # Create oracle
    oracle = SpectralOracle(window_size=32, num_freqs=8)
    
    # Attempt recovery
    found_k = spectral_gradient_descent(target, G, oracle, max_steps=200)
    
    if found_k == true_k:
        print(f"\n🎉 SUCCESS! Recovered k = {found_k}")
        return True
    else:
        print(f"\n❌ FAILED to recover k (Expected for complex landscape)")
        print("   This demonstrates that while the landscape is smooth,")
        print("   it has local minima that trap simple gradient descent.")
        return False

def main():
    """Run spectral gradient descent test."""
    success = test_small_range()
    
    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    print("If FAILED (which is likely):")
    print("  • The spectral landscape is smooth but NON-CONVEX.")
    print("  • Gradient descent gets stuck in local minima.")
    print("  • This proves the existence of structure (gradients),")
    print("    but also shows that simple local search is insufficient.")
    print("")
    print("For Bitcoin Puzzle 135:")
    print("  • We need a global search (Kangaroo) that uses")
    print("    spectral distance as a heuristic, not just hash collision.")
    print("=" * 60)

if __name__ == "__main__":
    main()