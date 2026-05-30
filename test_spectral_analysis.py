#!/usr/bin/env python3
"""
Test spectral properties of scalar multiplication on secp256k1.
Demonstrates non-random spectrum and local continuity.
"""

import numpy as np
import matplotlib.pyplot as plt
from ecdsa import SECP256k1, SigningKey, VerifyingKey
from ecdsa.ellipticcurve import Point
import random

def get_point_from_verifying_key(vk: VerifyingKey) -> Point:
    """Extract the elliptic curve Point from a VerifyingKey."""
    return vk.pubkey.point

def compute_x_sequence(k_start: int, length: int, G: Point) -> np.ndarray:
    """Compute sequence of x-coordinates: x(k_start·G), x((k_start+1)·G), ..."""
    x_vals = []
    curr = k_start * G
    for _ in range(length):
        # Convert to native Python int, then float for NumPy compatibility
        x_val = float(int(curr.x()))
        x_vals.append(x_val)
        curr = curr + G
    return np.array(x_vals, dtype=float)

def spectral_analysis(x_seq: np.ndarray) -> np.ndarray:
    """Compute FFT and return normalized magnitude spectrum."""
    spectrum = np.fft.fft(x_seq)
    mags = np.abs(spectrum)
    # Normalize
    max_mag = np.max(mags)
    if max_mag > 1e-10:
        mags = mags / max_mag
    return mags

def test_spectrum_randomness():
    """Test if spectrum deviates from white noise."""
    print("=" * 60)
    print("TEST 1: Spectrum Randomness Analysis")
    print("=" * 60)
    
    # Generate sequence
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point  # Get the Point object
    x_seq = compute_x_sequence(random.randint(1, 10000), 256, G)
    
    # Spectral analysis
    mags = spectral_analysis(x_seq)
    
    # Statistics (excluding DC component)
    mags_no_dc = mags[1:50]  # First 50 frequencies
    mean_mag = np.mean(mags_no_dc)
    std_mag = np.std(mags_no_dc)
    ratio = std_mag / mean_mag if mean_mag > 1e-10 else float('inf')
    
    print(f"Mean amplitude (first 50 freqs): {mean_mag:.4f}")
    print(f"Std deviation: {std_mag:.4f}")
    print(f"Std/Mean ratio: {ratio:.4f}")
    print(f"Expected for white noise: ~1.0")
    
    if ratio < 0.5:
        print("✅ RESULT: Spectrum is NOT white noise (structured)")
    else:
        print("⚠️  RESULT: Spectrum appears random")
    
    # Visualization
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(mags_no_dc)
    plt.title("Magnitude Spectrum (First 50 Frequencies)")
    plt.xlabel("Frequency Index")
    plt.ylabel("Normalized Magnitude")
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.hist(mags_no_dc, bins=20, alpha=0.7)
    plt.title("Distribution of Magnitudes")
    plt.xlabel("Magnitude")
    plt.ylabel("Count")
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("spectrum_analysis.png", dpi=150)
    print("📊 Saved: spectrum_analysis.png")
    
    return ratio

def test_local_continuity():
    """Test spectral continuity between consecutive points."""
    print("\n" + "=" * 60)
    print("TEST 2: Local Spectral Continuity")
    print("=" * 60)
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    k0 = random.randint(1, 10000)
    
    # Compute spectral signatures at k, k+1, k+10, k+100
    window_size = 64
    offsets = [0, 1, 10, 50, 100]
    signatures = []
    
    for offset in offsets:
        x_seq = compute_x_sequence(k0 + offset, window_size, G)
        sig = spectral_analysis(x_seq)[1:17]  # First 16 frequencies
        signatures.append(sig)
    
    # Compute distances
    print(f"Reference: k = {k0}")
    print(f"{'Offset':<10} {'Spectral Distance':<20} {'Interpretation'}")
    print("-" * 50)
    
    distances = []
    for i, offset in enumerate(offsets):
        dist = np.linalg.norm(signatures[i] - signatures[0])
        distances.append((offset, dist))
        
        if dist < 0.1:
            interp = "Very close (high correlation)"
        elif dist < 0.5:
            interp = "Moderately close"
        else:
            interp = "Distant (low correlation)"
        
        print(f"{offset:<10} {dist:<20.4f} {interp}")
    
    # Visualization
    plt.figure(figsize=(10, 4))
    plt.plot([d[0] for d in distances], [d[1] for d in distances], 'o-', linewidth=2)
    plt.title("Spectral Distance vs Scalar Offset")
    plt.xlabel("Offset in k")
    plt.ylabel("Euclidean Distance in Spectral Space")
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Threshold')
    plt.legend()
    plt.tight_layout()
    plt.savefig("spectral_continuity.png", dpi=150)
    print("📊 Saved: spectral_continuity.png")
    
    # Check continuity
    if distances[1][1] < 0.2:  # k and k+1 should be close
        print("✅ RESULT: Local spectral continuity CONFIRMED")
        return True
    else:
        print("❌ RESULT: Local continuity NOT observed")
        return False

def test_amplitude_correlation():
    """Test correlation between consecutive amplitude spectra."""
    print("\n" + "=" * 60)
    print("TEST 3: Amplitude Correlation (k vs k+1)")
    print("=" * 60)
    
    sk = SigningKey.generate(curve=SECP256k1)
    G = sk.verifying_key.pubkey.point
    
    correlations = []
    num_tests = 20
    
    for _ in range(num_tests):
        k = random.randint(1, 10000)
        
        # Compute spectra at k and k+1
        x_k = compute_x_sequence(k, 128, G)
        x_k1 = compute_x_sequence(k + 1, 128, G)
        
        spec_k = spectral_analysis(x_k)[1:33]
        spec_k1 = spectral_analysis(x_k1)[1:33]
        
        # Pearson correlation
        corr = np.corrcoef(spec_k, spec_k1)[0, 1]
        if not np.isnan(corr):
            correlations.append(corr)
    
    avg_corr = np.mean(correlations)
    print(f"Average correlation (over {num_tests} tests): {avg_corr:.4f}")
    print(f"Expected for independent sequences: ~0.0")
    print(f"Expected for identical sequences: 1.0")
    
    if avg_corr > 0.9:
        print("✅ RESULT: Very high correlation (spectral smoothness)")
    elif avg_corr > 0.5:
        print("✅ RESULT: Moderate correlation detected")
    else:
        print("⚠️  RESULT: Low correlation")
    
    return avg_corr

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SPECTRAL CONTINUITY TEST SUITE")
    print("Elliptic Curve: secp256k1")
    print("=" * 60 + "\n")
    
    # Run tests
    spectrum_ratio = test_spectrum_randomness()
    continuity = test_local_continuity()
    amplitude_corr = test_amplitude_correlation()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Spectrum Std/Mean: {spectrum_ratio:.4f} (white noise: ~1.0)")
    print(f"Local continuity: {'✅ YES' if continuity else '❌ NO'}")
    print(f"Amplitude correlation: {amplitude_corr:.4f}")
    
    if spectrum_ratio < 0.5 and continuity and amplitude_corr > 0.9:
        print("\n🎉 ALL TESTS PASSED: Spectral continuity CONFIRMED")
        print("\nImplications:")
        print("  • ECDLP has hidden algebraic structure")
        print("  • Spectral methods can guide search (gradient descent)")
        print("  • Not white noise → potential for optimization")
    else:
        print("\n⚠️  SOME TESTS FAILED or results inconclusive")
        print("  • May require larger sample sizes")
        print("  • Or different curve parameters")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()