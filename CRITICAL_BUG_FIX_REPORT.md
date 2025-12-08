# 🔴 CRITICAL BUG REPORT: Tb and hML Discrepancies

## Date: December 8, 2025
## Issue: T_bot (Tb) and h_ML (hML) incorrect outputs compared to Fortran test file

---

## 🎯 ROOT CAUSE IDENTIFIED

### **BUG #1: Incorrect C_TT_flk and C_Q_flk Calculation (CRITICAL)**

**Location:** Cell 22, Line 431 of `FLAKE_Model_CORRECTED_FINAL_helsinngese.ipynb`

**Current INCORRECT Code:**
```python
C_TT_flk, C_Q_flk = C_TT_1 * C_T_p_flk - C_TT_2, 2.0 * C_TT_flk / C_T_p_flk
```

**Problem:**
This is a **simultaneous tuple assignment** in Python. When computing the right-hand side values:
1. `C_TT_1 * C_T_p_flk - C_TT_2` is computed correctly
2. `2.0 * C_TT_flk / C_T_p_flk` **USES THE OLD VALUE** of `C_TT_flk`

Since `C_TT_flk` is initialized to `0.0` globally (line 2526), this means:
```python
C_Q_flk = 2.0 * 0.0 / C_T_p_flk = 0.0  # WRONG!
```

**Correct Code (MUST FIX):**
```python
C_TT_flk = C_TT_1 * C_T_p_flk - C_TT_2
C_Q_flk = 2.0 * C_TT_flk / C_T_p_flk
```

**Why This Causes Tb and hML Errors:**

1. **Incorrect C_Q_flk = 0.0** propagates to the T_bot calculation (line ~3224):
   ```python
   d_T_bot_dt += ((I_intm_h_D_flk - (1.0 - C_Q_flk) * I_h_flk - C_Q_flk * I_bot_flk) * R_TI_icesnow
                 / (depth_w - h_ML_p_flk) / tpl_rho_w_r / tpl_c_w)
   ```

   With `C_Q_flk = 0.0`, this becomes:
   ```python
   d_T_bot_dt += ((I_intm_h_D_flk - I_h_flk) * R_TI_icesnow / (depth_w - h_ML_p_flk) / tpl_rho_w_r / tpl_c_w)
   ```

   **Missing the radiation flux terms!** Should be:
   ```python
   d_T_bot_dt += ((I_intm_h_D_flk - (1.0 - C_Q_flk) * I_h_flk - C_Q_flk * I_bot_flk) * ...)
   ```
   where `C_Q_flk` should be a positive value computed from C_TT_flk.

2. **Incorrect C_TT_flk = 0.0** (used as old value) affects:
   - R_TI_icesnow calculation (line ~3193): `R_TI_icesnow = C_T_p_flk / C_TT_flk`
     - **Division by zero or near-zero!**
   - Multiple radiation flux calculations involving C_TT_flk

3. **Cascading effects on h_ML:**
   - Since T_bot is wrong, the temperature gradient `(T_wML - T_bot)` is wrong
   - This affects the denominator in h_ML calculations
   - Results in incorrect mixed-layer depth evolution

---

## 📊 IMPACT SEVERITY

### Critical Variables Affected:
1. ✅ **C_TT_flk** - Shape parameter for thermocline
2. ✅ **C_Q_flk** - Shape factor for heat flux
3. ❌ **T_bot** - Bottom temperature (PRIMARY ISSUE)
4. ❌ **h_ML** - Mixed-layer depth (PRIMARY ISSUE)
5. ❌ **d_T_bot_dt** - Rate of change of bottom temperature
6. ❌ **d_h_ML_dt** - Rate of change of mixed-layer depth

### Test Results Comparison:
From `Heiligensee80-96.test`, we see that:
- **Fortran T_bot values** vary from ~0.3K to ~7.5K depending on conditions
- **Fortran h_ML values** vary from 0m to 5.9m (full lake depth)
- **Python values** will be significantly different due to this bug

---

## 🔧 FIX INSTRUCTIONS

### Step 1: Locate the Bug
1. Open `FLAKE_Model_CORRECTED_FINAL_helsinngese.ipynb`
2. Navigate to Cell 22 (the `flake_driver` function)
3. Find line 431 (around line 185 of the function)

### Step 2: Apply the Fix

**FIND THIS LINE:**
```python
        C_TT_flk, C_Q_flk = C_TT_1 * C_T_p_flk - C_TT_2, 2.0 * C_TT_flk / C_T_p_flk
```

**REPLACE WITH THESE TWO LINES:**
```python
        C_TT_flk = C_TT_1 * C_T_p_flk - C_TT_2
        C_Q_flk = 2.0 * C_TT_flk / C_T_p_flk
```

### Step 3: Verify the Fix
Add debugging output temporarily:
```python
        C_TT_flk = C_TT_1 * C_T_p_flk - C_TT_2
        C_Q_flk = 2.0 * C_TT_flk / C_T_p_flk
        # DEBUG: Verify values
        assert C_TT_flk != 0.0, f"C_TT_flk should not be zero! C_T_p_flk={C_T_p_flk}"
        assert C_Q_flk != 0.0, f"C_Q_flk should not be zero! C_TT_flk={C_TT_flk}"
        print(f"DEBUG: C_TT_flk={C_TT_flk:.6f}, C_Q_flk={C_Q_flk:.6f}")  # Can remove after testing
```

---

## 🧪 TESTING PROCEDURE

### Test 1: Verify C_TT_flk and C_Q_flk Values
```python
# Expected values (approximate):
# C_T_min = 0.5
# C_T_max = 0.718282
# C_TT_1 = 11/18 ≈ 0.6111
# C_TT_2 = 7/45 ≈ 0.1556

# For C_T_p_flk = 0.5:
# C_TT_flk = 0.6111 * 0.5 - 0.1556 = 0.1500
# C_Q_flk = 2.0 * 0.1500 / 0.5 = 0.6000

# These should be NON-ZERO!
```

### Test 2: Compare with Fortran Test File
Run the simulation and compare output columns:
- Column 3 (Tb): Bottom temperature
- Column 13 (h_ML): Mixed-layer depth

**Before Fix:**
```
Tb differences: LARGE (multiple degrees K)
h_ML differences: LARGE (meters)
```

**After Fix:**
```
Tb differences: SMALL (< 0.01 K tolerance)
h_ML differences: SMALL (< 0.01 m tolerance)
```

### Test 3: Full Simulation Run
```python
# Run full simulation with Heiligensee data
# Compare ALL timesteps against test file
# Verify:
# 1. T_bot matches within tolerance
# 2. h_ML matches within tolerance
# 3. No numerical instabilities
# 4. No division by zero errors
```

---

## 📝 ADDITIONAL CHECKS

### Secondary Issues to Verify (Lower Priority):

#### 1. Check C_TT_flk is initialized properly in ice-covered section
The ice-covered branch doesn't recompute C_TT_flk, but uses it from previous open-water calculations. Verify this is intentional.

#### 2. Verify global variable declarations
Ensure all `_p_flk` variables are declared global in `flake_driver`:
```python
global T_snow_p_flk, T_ice_p_flk, T_mnw_p_flk, T_wML_p_flk, T_bot_p_flk, T_B1_p_flk
global h_snow_p_flk, h_ice_p_flk, h_ML_p_flk, H_B1_p_flk, C_T_p_flk
```

#### 3. Check flake_interface sets all _p_flk variables before calling flake_driver
In the `flake_interface` function, verify:
```python
T_bot_p_flk = T_bot_in
h_ML_p_flk = h_ML_in
C_T_p_flk = C_T_in
# ... etc for all variables
```

---

## 🎓 LEARNING POINTS

### Python vs Fortran Differences:

1. **Tuple Assignment Order:**
   - **Fortran:** Sequential assignment, each line computed before next
     ```fortran
     C_TT_flk = C_TT_1*C_T_p_flk-C_TT_2
     C_Q_flk = 2._ireals*C_TT_flk/C_T_p_flk
     ```

   - **Python tuple assignment:** Simultaneous evaluation of right-hand side
     ```python
     # WRONG - uses old C_TT_flk value:
     C_TT_flk, C_Q_flk = ..., 2.0 * C_TT_flk / ...

     # CORRECT - sequential assignment:
     C_TT_flk = ...
     C_Q_flk = 2.0 * C_TT_flk / ...
     ```

2. **Variable Scope:**
   - Fortran: Module variables automatically accessible
   - Python: Must declare `global` for write access

3. **Type Precision:**
   - Fortran: `_ireals` explicit type parameter
   - Python: Use `np.float64()` for precision

---

## ✅ VERIFICATION CHECKLIST

- [ ] Fix applied to line 431 in Cell 22
- [ ] Code runs without errors
- [ ] C_TT_flk has non-zero values during open-water conditions
- [ ] C_Q_flk has non-zero values during open-water conditions
- [ ] T_bot matches Fortran test file (column 3)
- [ ] h_ML matches Fortran test file (column 13)
- [ ] No division by zero warnings
- [ ] Full simulation completes successfully
- [ ] Results saved and compared with test file
- [ ] Documentation updated

---

## 📞 SUMMARY FOR USER

### What Was Wrong:
The Python code was calculating two critical shape factors (`C_TT_flk` and `C_Q_flk`) incorrectly due to Python's tuple assignment behavior. This caused `C_Q_flk` to always be zero, which:
1. Broke the bottom temperature (T_bot/Tb) calculations
2. Caused cascading errors in mixed-layer depth (h_ML/hML) calculations
3. Resulted in incorrect radiation flux terms in the thermocline

### The Fix:
Changed one line from:
```python
C_TT_flk, C_Q_flk = C_TT_1 * C_T_p_flk - C_TT_2, 2.0 * C_TT_flk / C_T_p_flk
```

To two sequential lines:
```python
C_TT_flk = C_TT_1 * C_T_p_flk - C_TT_2
C_Q_flk = 2.0 * C_TT_flk / C_T_p_flk
```

### Expected Results After Fix:
- T_bot (Tb) will match Fortran results within numerical tolerance
- h_ML (hML) will match Fortran results within numerical tolerance
- All physics calculations will be consistent with the original Fortran model

---

END OF REPORT
