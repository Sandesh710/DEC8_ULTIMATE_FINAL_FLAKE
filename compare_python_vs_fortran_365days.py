#!/usr/bin/env python3
"""
Compare Python FLake output vs Fortran test file for first 365 days.
"""

import numpy as np

print("="*80)
print("COMPARING PYTHON vs FORTRAN FLAKE OUTPUTS (365 DAYS)")
print("="*80)

# ============================================================================
# LOAD FORTRAN TEST DATA
# ============================================================================

print("\nLoading Fortran test data from Heiligensee80-96.test...")

fortran_data = []
with open('Heiligensee80-96.test', 'r') as f:
    lines = f.readlines()
    # Skip first 2 lines (header + column names)
    for line in lines[2:367]:  # Lines 3 to 367 (timesteps 0-364)
        parts = line.strip().split()
        if len(parts) >= 23:
            fortran_data.append([float(x) for x in parts])

fortran_data = np.array(fortran_data)
print(f"Loaded {len(fortran_data)} timesteps from Fortran")

# ============================================================================
# LOAD PYTHON OUTPUT DATA
# ============================================================================

print("Loading Python output from Heiligensee80-96.rslt...")

python_data = []
with open('Heiligensee80-96.rslt', 'r') as f:
    lines = f.readlines()
    # Skip first 2 lines (header + column names)
    for line in lines[2:367]:  # Lines 3 to 367 (timesteps 0-364)
        parts = line.strip().split()
        if len(parts) >= 23:
            python_data.append([float(x) for x in parts])

python_data = np.array(python_data)
print(f"Loaded {len(python_data)} timesteps from Python")

# ============================================================================
# COLUMN MAPPING
# ============================================================================

columns = {
    'No': 0,
    'time': 1,
    'Ts': 2,
    'Tm': 3,
    'Tb': 4,
    'ufr_a': 5,
    'ufr_w': 6,
    'Wconv': 7,
    'Qw': 8,
    'Q_se': 9,
    'Q_la': 10,
    'I_w': 11,
    'Q_lwa': 12,
    'Q_lww': 13,
    'h_ML': 14,
    'C_T': 15,
    'H_B1': 16,
    'T_B1': 17,
    'Qbot': 18,
    'H_ice': 19,
    'H_snow': 20,
    'T_ice': 21,
    'T_snow': 22
}

# ============================================================================
# COMPUTE DIFFERENCES
# ============================================================================

print("\n" + "="*80)
print("COMPUTING DIFFERENCES (Python - Fortran)")
print("="*80)

differences = python_data - fortran_data

# Focus on key variables
key_vars = ['Ts', 'Tm', 'Tb', 'h_ML', 'C_T', 'Qw', 'Q_se', 'Q_la', 'I_w']

print("\nStatistics for first 365 days:")
print("-"*80)
print(f"{'Variable':<10} {'Mean Diff':<12} {'Max Diff':<12} {'StdDev':<12} {'RMSE':<12}")
print("-"*80)

results_summary = []

for var in key_vars:
    col = columns[var]
    diffs = differences[:, col]

    mean_diff = np.mean(diffs)
    max_diff = np.max(np.abs(diffs))
    std_diff = np.std(diffs)
    rmse = np.sqrt(np.mean(diffs**2))

    results_summary.append({
        'var': var,
        'mean': mean_diff,
        'max': max_diff,
        'std': std_diff,
        'rmse': rmse
    })

    print(f"{var:<10} {mean_diff:11.6f}  {max_diff:11.6f}  {std_diff:11.6f}  {rmse:11.6f}")

# ============================================================================
# DETAILED COMPARISON FOR KEY TIMESTEPS
# ============================================================================

print("\n" + "="*80)
print("DETAILED COMPARISON AT KEY TIMESTEPS")
print("="*80)

key_steps = [0, 1, 5, 10, 30, 90, 180, 364]

for step in key_steps:
    if step >= len(fortran_data):
        continue

    print(f"\nTimestep {step} (Day {fortran_data[step, 1]:.1f}):")
    print("-"*80)
    print(f"{'Variable':<10} {'Fortran':<15} {'Python':<15} {'Diff':<15} {'% Diff':<10}")
    print("-"*80)

    for var in ['Ts', 'Tb', 'h_ML', 'Qw']:
        col = columns[var]
        f_val = fortran_data[step, col]
        p_val = python_data[step, col]
        diff = p_val - f_val

        if abs(f_val) > 0.01:
            pct_diff = (diff / f_val) * 100
        else:
            pct_diff = 0.0

        print(f"{var:<10} {f_val:14.6f}  {p_val:14.6f}  {diff:14.6f}  {pct_diff:9.3f}%")

# ============================================================================
# CHECK FOR CRITICAL DISCREPANCIES
# ============================================================================

print("\n" + "="*80)
print("CHECKING FOR CRITICAL DISCREPANCIES")
print("="*80)

# Define tolerance thresholds
tolerances = {
    'Ts': 0.1,   # ±0.1°C
    'Tb': 0.1,   # ±0.1°C
    'Tm': 0.1,   # ±0.1°C
    'h_ML': 0.1, # ±0.1 m
    'C_T': 0.01, # ±0.01
    'Qw': 5.0,   # ±5 W/m²
}

critical_issues = []

for var, tol in tolerances.items():
    col = columns[var]
    diffs = differences[:, col]
    max_diff = np.max(np.abs(diffs))

    if max_diff > tol:
        exceeds = np.sum(np.abs(diffs) > tol)
        pct_exceeds = (exceeds / len(diffs)) * 100
        critical_issues.append({
            'var': var,
            'max_diff': max_diff,
            'tolerance': tol,
            'exceeds': exceeds,
            'pct': pct_exceeds
        })

if critical_issues:
    print("\n⚠️  CRITICAL DISCREPANCIES FOUND:")
    print("-"*80)
    for issue in critical_issues:
        print(f"  {issue['var']}:")
        print(f"    Max difference: {issue['max_diff']:.6f}")
        print(f"    Tolerance: ±{issue['tolerance']}")
        print(f"    Timesteps exceeding tolerance: {issue['exceeds']} ({issue['pct']:.1f}%)")
else:
    print("\n✅ NO CRITICAL DISCREPANCIES")
    print("   All variables within tolerance!")

# ============================================================================
# TIME SERIES COMPARISON
# ============================================================================

print("\n" + "="*80)
print("TIME SERIES ANALYSIS")
print("="*80)

# Check if trends match
print("\nTrend correlation (first 365 days):")
print("-"*80)

for var in ['Ts', 'Tb', 'h_ML']:
    col = columns[var]
    f_series = fortran_data[:, col]
    p_series = python_data[:, col]

    # Compute correlation
    correlation = np.corrcoef(f_series, p_series)[0, 1]

    # Compute trend direction match
    f_trend = f_series[-1] - f_series[0]
    p_trend = p_series[-1] - p_series[0]
    trend_match = "✅ Match" if (f_trend * p_trend) > 0 else "❌ Opposite"

    print(f"  {var:<10}: Correlation = {correlation:.6f}  |  Trend: {trend_match}")

# ============================================================================
# SAVE DETAILED COMPARISON TO FILE
# ============================================================================

print("\n" + "="*80)
print("SAVING DETAILED COMPARISON")
print("="*80)

with open('comparison_python_vs_fortran_365days.txt', 'w') as f:
    f.write("PYTHON vs FORTRAN COMPARISON (First 365 days)\n")
    f.write("="*80 + "\n\n")

    f.write("Timestep-by-timestep comparison for key variables:\n")
    f.write("-"*120 + "\n")
    f.write(f"{'Step':<6} {'Time':<8} ")
    for var in ['Ts', 'Tb', 'h_ML']:
        f.write(f"{'F_'+var:<10} {'P_'+var:<10} {'Diff_'+var:<10} ")
    f.write("\n")
    f.write("-"*120 + "\n")

    for i in range(len(fortran_data)):
        f.write(f"{int(fortran_data[i,0]):<6} {fortran_data[i,1]:<8.2f} ")
        for var in ['Ts', 'Tb', 'h_ML']:
            col = columns[var]
            f_val = fortran_data[i, col]
            p_val = python_data[i, col]
            diff = p_val - f_val
            f.write(f"{f_val:<10.5f} {p_val:<10.5f} {diff:<10.5f} ")
        f.write("\n")

print("✅ Saved detailed comparison to: comparison_python_vs_fortran_365days.txt")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

if not critical_issues:
    print("\n🎉 SUCCESS! Python implementation matches Fortran within tolerances!")
    print("\nKey findings:")
    for res in results_summary[:3]:  # Show top 3 variables
        print(f"  • {res['var']}: RMSE = {res['rmse']:.6f}, Max diff = {res['max']:.6f}")
else:
    print("\n⚠️  DISCREPANCIES DETECTED!")
    print(f"\n{len(critical_issues)} variable(s) exceed tolerance thresholds.")
    print("\nThis indicates potential issues with:")
    print("  1. Input data differences")
    print("  2. Physics implementation differences")
    print("  3. Numerical precision differences")
    print("\nReview the detailed comparison file for timestep-by-timestep analysis.")

print("\n" + "="*80)
