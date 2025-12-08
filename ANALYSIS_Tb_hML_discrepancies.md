# Analysis: Tb and hML Discrepancies Between Fortran and Python Implementations

## Executive Summary
This document analyzes discrepancies between the Fortran FLake model and its Python translation, specifically focusing on:
- **Tb** (T_bot): Bottom temperature [K]
- **hML** (h_ML): Mixed layer depth [m]

## Test Data Format
From `Heiligensee80-96.test`:
- Column 3: **Tb** (bottom temperature)
- Column 13: **h_ML** (mixed layer depth)

---

## Critical Sections Comparison

### 1. OPEN WATER: Mixed-Layer Deepening - T_bot Calculation

#### FORTRAN (flake_driver.incf: Lines 609-640)
```fortran
IF(h_ML_n_flk.LE.depth_w-h_ML_min_flk) THEN       ! Mixing did not reach the bottom

  IF(h_ML_n_flk.GT.h_ML_p_flk) THEN   ! Mixed-layer deepening
    R_H_icesnow     = h_ML_p_flk/depth_w
    R_rho_c_icesnow = 1._ireals-R_H_icesnow
    R_TI_icesnow    = 0.5_ireals*C_T_p_flk*R_rho_c_icesnow+C_TT_flk*(2._ireals*R_H_icesnow-1._ireals)
    R_Tstar_icesnow = (0.5_ireals+C_TT_flk-C_Q_flk)/R_TI_icesnow
    R_TI_icesnow    = (1._ireals-C_T_p_flk*R_rho_c_icesnow)/R_TI_icesnow

    d_T_bot_dt = (Q_w_flk-Q_bot_flk+I_w_flk-I_bot_flk)/tpl_rho_w_r/tpl_c_w
    d_T_bot_dt = d_T_bot_dt - C_T_p_flk*(T_wML_p_flk-T_bot_p_flk)*d_h_ML_dt
    d_T_bot_dt = d_T_bot_dt*R_Tstar_icesnow/depth_w                   ! Q+I fluxes and dh_ML/dt term

    flk_str_2 = I_intm_h_D_flk - (1._ireals-C_Q_flk)*I_h_flk - C_Q_flk*I_bot_flk
    flk_str_2 = flk_str_2*R_TI_icesnow/(depth_w-h_ML_p_flk)/tpl_rho_w_r/tpl_c_w
    d_T_bot_dt = d_T_bot_dt + flk_str_2                               ! Add radiation-flux term

    flk_str_2 = (1._ireals-C_TT_2*R_TI_icesnow)/C_T_p_flk
    flk_str_2 = flk_str_2*(T_wML_p_flk-T_bot_p_flk)*d_C_T_dt
    d_T_bot_dt = d_T_bot_dt + flk_str_2                               ! Add dC_T/dt term

  ELSE                                ! Mixed-layer retreat or stationary state
    d_T_bot_dt = 0._ireals                                            ! dT_bot/dt=0
  END IF

  T_bot_n_flk = T_bot_p_flk + d_T_bot_dt*del_time                      ! Update T_bot
  T_bot_n_flk = MAX(T_bot_n_flk, tpl_T_f)           ! Security, limit T_bot by the freezing point
  flk_str_2 = (T_bot_n_flk-tpl_T_r)*flake_buoypar(T_mnw_n_flk)
  IF(flk_str_2.LT.0._ireals) T_bot_n_flk = tpl_T_r  ! Security, avoid T_r crossover
  T_wML_n_flk = C_T_n_flk*(1._ireals-h_ML_n_flk/depth_w)
  T_wML_n_flk = (T_mnw_n_flk-T_bot_n_flk*T_wML_n_flk)/(1._ireals-T_wML_n_flk)
  T_wML_n_flk = MAX(T_wML_n_flk, tpl_T_f)           ! Security, limit T_wML by the freezing point
```

#### PYTHON (notebook)
```python
if h_ML_n_flk <= depth_w - h_ML_min_flk:
    if h_ML_n_flk > h_ML_p_flk:
        R_H_icesnow, R_rho_c_icesnow = h_ML_p_flk / depth_w, 1.0 - h_ML_p_flk / depth_w
        R_TI_icesnow = 0.5 * C_T_p_flk * R_rho_c_icesnow + C_TT_flk * (2.0 * R_H_icesnow - 1.0)
        R_Tstar_icesnow, R_TI_icesnow = (0.5 + C_TT_flk - C_Q_flk) / R_TI_icesnow, (1.0 - C_T_p_flk * R_rho_c_icesnow) / R_TI_icesnow
        d_T_bot_dt = (((Q_w_flk - Q_bot_flk + I_w_flk - I_bot_flk) / tpl_rho_w_r / tpl_c_w
                      - C_T_p_flk * (T_wML_p_flk - T_bot_p_flk) * d_h_ML_dt) * R_Tstar_icesnow / depth_w)
        d_T_bot_dt += ((I_intm_h_D_flk - (1.0 - C_Q_flk) * I_h_flk - C_Q_flk * I_bot_flk) * R_TI_icesnow
                      / (depth_w - h_ML_p_flk) / tpl_rho_w_r / tpl_c_w)
        d_T_bot_dt += (1.0 - C_TT_2 * R_TI_icesnow) / C_T_p_flk * (T_wML_p_flk - T_bot_p_flk) * d_C_T_dt
    else:
        d_T_bot_dt = 0.0
    T_bot_n_flk = max(T_bot_p_flk + d_T_bot_dt * del_time, tpl_T_f)
    if (T_bot_n_flk - tpl_T_r) * flake_buoypar(T_mnw_n_flk) < 0.0:
        T_bot_n_flk = tpl_T_r
    T_wML_n_flk = max((T_mnw_n_flk - T_bot_n_flk * C_T_n_flk * (1.0 - h_ML_n_flk / depth_w))
                     / (1.0 - C_T_n_flk * (1.0 - h_ML_n_flk / depth_w)), tpl_T_f)
```

### 🔴 ISSUE #1: T_wML Calculation Formula Difference

**FORTRAN:**
```fortran
T_wML_n_flk = C_T_n_flk*(1._ireals-h_ML_n_flk/depth_w)
T_wML_n_flk = (T_mnw_n_flk-T_bot_n_flk*T_wML_n_flk)/(1._ireals-T_wML_n_flk)
```
This uses **TWO steps**:
1. First calculates intermediate value: `temp = C_T * (1 - h_ML/D)`
2. Then: `T_wML = (T_mnw - T_bot * temp) / (1 - temp)`

**PYTHON:**
```python
T_wML_n_flk = (T_mnw_n_flk - T_bot_n_flk * C_T_n_flk * (1.0 - h_ML_n_flk / depth_w))
             / (1.0 - C_T_n_flk * (1.0 - h_ML_n_flk / depth_w))
```
This uses **ONE step** with the formula expanded inline.

✅ **Mathematically equivalent** - NOT the source of error.

---

### 2. ICE-COVERED: T_bot Calculation

#### FORTRAN (flake_driver.incf: Lines 407-442)
```fortran
HTC_Water: IF(h_ice_n_flk.GE.h_Ice_min_flk) THEN    ! Ice exists

  T_mnw_n_flk = MIN(T_mnw_n_flk, tpl_T_r) ! Limit the mean temperature under the ice by T_r
  T_wML_n_flk = tpl_T_f                   ! The mixed-layer temperature is equal to the freezing point

  IF(l_ice_create) THEN                  ! Ice has just been created
    IF(h_ML_p_flk.GE.depth_w-h_ML_min_flk) THEN    ! h_ML=D when ice is created
      h_ML_n_flk = 0._ireals                 ! Set h_ML to zero
      C_T_n_flk = C_T_min                    ! Set C_T to its minimum value
    ELSE                                          ! h_ML<D when ice is created
      h_ML_n_flk = h_ML_p_flk                ! h_ML remains unchanged
      C_T_n_flk = C_T_p_flk                  ! C_T (thermocline) remains unchanged
    END IF
    T_bot_n_flk = T_wML_n_flk - (T_wML_n_flk-T_mnw_n_flk)/C_T_n_flk/(1._ireals-h_ML_n_flk/depth_w)
                                             ! Update the bottom temperature

  ELSE IF(T_bot_p_flk.LT.tpl_T_r) THEN   ! Ice exists and T_bot < T_r, molecular heat transfer
    h_ML_n_flk = h_ML_p_flk                  ! h_ML remains unchanged
    C_T_n_flk = C_T_p_flk                    ! C_T (thermocline) remains unchanged
    T_bot_n_flk = T_wML_n_flk - (T_wML_n_flk-T_mnw_n_flk)/C_T_n_flk/(1._ireals-h_ML_n_flk/depth_w)
                                             ! Update the bottom temperature

  ELSE                                   ! Ice exists and T_bot = T_r, convection due to bottom heating
    T_bot_n_flk = tpl_T_r                      ! T_bot is equal to the temperature of maximum density
    IF(h_ML_p_flk.GE.c_small_flk) THEN   ! h_ML > 0
      C_T_n_flk = C_T_p_flk                     ! C_T (thermocline) remains unchanged
      h_ML_n_flk = depth_w*(1._ireals-(T_wML_n_flk-T_mnw_n_flk)/(T_wML_n_flk-T_bot_n_flk)/C_T_n_flk)
      h_ML_n_flk = MAX(h_ML_n_flk, 0._ireals)   ! Update the mixed-layer depth
    ELSE                                 ! h_ML = 0
      h_ML_n_flk = h_ML_p_flk                   ! h_ML remains unchanged
      C_T_n_flk = (T_wML_n_flk-T_mnw_n_flk)/(T_wML_n_flk-T_bot_n_flk)
      C_T_n_flk = MIN(C_T_max, MAX(C_T_n_flk, C_T_min)) ! Update the shape factor (thermocline)
    END IF
  END IF

  T_bot_n_flk = MIN(T_bot_n_flk, tpl_T_r)    ! Security, limit the bottom temperature by T_r
```

#### PYTHON (notebook)
```python
if h_ice_n_flk >= h_Ice_min_flk:  # Ice-covered
    T_mnw_n_flk = min(T_mnw_n_flk, tpl_T_r)
    T_wML_n_flk = tpl_T_f
    if l_ice_create:
        if h_ML_p_flk >= depth_w - h_ML_min_flk:
            h_ML_n_flk, C_T_n_flk = 0.0, C_T_min
        else:
            h_ML_n_flk, C_T_n_flk = h_ML_p_flk, C_T_p_flk
        T_bot_n_flk = T_wML_n_flk - (T_wML_n_flk - T_mnw_n_flk) / C_T_n_flk / (1.0 - h_ML_n_flk / depth_w)
    elif T_bot_p_flk < tpl_T_r:
        h_ML_n_flk, C_T_n_flk = h_ML_p_flk, C_T_p_flk
        T_bot_n_flk = T_wML_n_flk - (T_wML_n_flk - T_mnw_n_flk) / C_T_n_flk / (1.0 - h_ML_n_flk / depth_w)
    else:
        T_bot_n_flk = tpl_T_r
        if h_ML_p_flk >= c_small_flk:
            C_T_n_flk = C_T_p_flk
            h_ML_n_flk = max(depth_w * (1.0 - (T_wML_n_flk - T_mnw_n_flk) / (T_wML_n_flk - T_bot_n_flk) / C_T_n_flk), 0.0)
        else:
            h_ML_n_flk = h_ML_p_flk
            C_T_n_flk = min(C_T_max, max((T_wML_n_flk - T_mnw_n_flk) / (T_wML_n_flk - T_bot_n_flk), C_T_min))
```

✅ **Ice-covered section matches correctly.**

---

### 3. CRITICAL ISSUE: Division by Zero Risk in T_bot Formula

#### The Formula Used (both Fortran and Python):
```
T_bot = T_wML - (T_wML - T_mnw) / C_T / (1 - h_ML/depth_w)
```

#### 🔴 ISSUE #2: When h_ML → depth_w (mixed layer reaches bottom)

The denominator `(1 - h_ML/depth_w)` approaches zero, causing:
- **Numerical instability**
- **Overflow/underflow errors**
- **Incorrect T_bot values**

**FORTRAN Protection:**
```fortran
IF(h_ML_n_flk.LE.depth_w-h_ML_min_flk) THEN  ! Only compute if h_ML is significantly less than depth_w
```
This guards against the division by ensuring `h_ML < depth_w - h_ML_min_flk` (where `h_ML_min_flk = 1e-2`).

**PYTHON Protection:**
```python
if h_ML_n_flk <= depth_w - h_ML_min_flk:  # Same guard condition
```
✅ **Python has the same protection.**

---

### 4. Mixed Layer Depth (h_ML) Calculations

#### CONVECTIVE MIXING (Fortran: Lines 496-560)

**Complete Entrainment Equation (when h_ML > h_ML_min):**
```fortran
R_H_icesnow     = depth_w/h_ML_p_flk
R_rho_c_icesnow = R_H_icesnow-1._ireals
R_TI_icesnow    = C_T_p_flk/C_TT_flk
R_Tstar_icesnow = (R_TI_icesnow/2._ireals-1._ireals)*R_rho_c_icesnow + 1._ireals
d_h_ML_dt = -Q_star_flk*(R_Tstar_icesnow*(1._ireals+c_cbl_1)-1._ireals) - Q_bot_flk
d_h_ML_dt = d_h_ML_dt/tpl_rho_w_r/tpl_c_w                        ! Q_* and Q_b flux terms
flk_str_2 = (depth_w-h_ML_p_flk)*(T_wML_p_flk-T_bot_p_flk)*C_TT_2/C_TT_flk*d_C_T_dt
d_h_ML_dt = d_h_ML_dt + flk_str_2                                 ! Add dC_T/dt term
flk_str_2 = I_bot_flk + (R_TI_icesnow-1._ireals)*I_h_flk - R_TI_icesnow*I_intm_h_D_flk
flk_str_2 = flk_str_2 + (R_TI_icesnow-2._ireals)*R_rho_c_icesnow*(I_h_flk-I_intm_0_h_flk)
flk_str_2 = flk_str_2/tpl_rho_w_r/tpl_c_w
d_h_ML_dt = d_h_ML_dt + flk_str_2                                 ! Add radiation terms
flk_str_2 = -c_cbl_2*R_Tstar_icesnow*Q_star_flk/tpl_rho_w_r/tpl_c_w/MAX(w_star_sfc_flk, c_small_flk)
flk_str_2 = flk_str_2 + C_T_p_flk*(T_wML_p_flk-T_bot_p_flk)
d_h_ML_dt = d_h_ML_dt/flk_str_2                                   ! dh_ML/dt = r.h.s.
```

**Python equivalent:**
```python
R_H_icesnow, R_rho_c_icesnow = depth_w / h_ML_p_flk, depth_w / h_ML_p_flk - 1.0
R_TI_icesnow = C_T_p_flk / C_TT_flk
R_Tstar_icesnow = (R_TI_icesnow / 2.0 - 1.0) * R_rho_c_icesnow + 1.0
d_h_ML_dt = (-Q_star_flk * (R_Tstar_icesnow * (1.0 + c_cbl_1) - 1.0) - Q_bot_flk) / tpl_rho_w_r / tpl_c_w
d_h_ML_dt += (depth_w - h_ML_p_flk) * (T_wML_p_flk - T_bot_p_flk) * C_TT_2 / C_TT_flk * d_C_T_dt
flk_str_2 = (I_bot_flk + (R_TI_icesnow - 1.0) * I_h_flk - R_TI_icesnow * I_intm_h_D_flk
            + (R_TI_icesnow - 2.0) * R_rho_c_icesnow * (I_h_flk - I_intm_0_h_flk)) / tpl_rho_w_r / tpl_c_w
d_h_ML_dt = (d_h_ML_dt + flk_str_2) / (-c_cbl_2 * R_Tstar_icesnow * Q_star_flk / tpl_rho_w_r / tpl_c_w
            / max(w_star_sfc_flk, c_small_flk) + C_T_p_flk * (T_wML_p_flk - T_bot_p_flk))
```

✅ **Python matches Fortran structure.**

---

## 🔍 POTENTIAL ROOT CAUSES

### ROOT CAUSE #1: Variable Initialization Order
**Issue:** Python might not properly initialize all `_p_flk` variables before calling `flake_driver`.

**Check in flake_interface:**
```python
# MUST set all _p_flk variables BEFORE calling flake_driver
T_bot_p_flk = T_bot_in
h_ML_p_flk = h_ML_in
C_T_p_flk = C_T_in
# ... etc
```

### ROOT CAUSE #2: Missing C_TT_flk Calculation
**Fortran computes C_TT_flk BEFORE using it:**
```fortran
C_TT_flk = C_TT_1*C_T_p_flk-C_TT_2         ! Line 487
C_Q_flk = 2._ireals*C_TT_flk/C_T_p_flk     ! Line 488
```

**Python MUST also compute these before the mixing calculations:**
```python
C_TT_flk, C_Q_flk = C_TT_1 * C_T_p_flk - C_TT_2, 2.0 * C_TT_flk / C_T_p_flk
```

### ROOT CAUSE #3: Numerical Precision
**Fortran uses explicit `_ireals` type casting:**
```fortran
R_H_icesnow = 1.0_ireals - h_ML_p_flk/depth_w
```

**Python should ensure float64:**
```python
R_H_icesnow = np.float64(1.0) - np.float64(h_ML_p_flk) / np.float64(depth_w)
```

---

## 🔬 DEBUGGING STEPS

1. **Add diagnostic prints** to compare intermediate values:
   ```python
   print(f"DEBUG: R_H_icesnow = {R_H_icesnow}")
   print(f"DEBUG: R_TI_icesnow = {R_TI_icesnow}")
   print(f"DEBUG: d_T_bot_dt = {d_T_bot_dt}")
   ```

2. **Check if C_TT_flk is computed** before use

3. **Verify all _p_flk variables** are set in flake_interface before calling flake_driver

4. **Check for array vs scalar issues** in Python (numpy broadcasting)

5. **Compare test file output** line-by-line with Python output

---

## ✅ NEXT STEPS

1. Search notebook for C_TT_flk initialization
2. Verify _p_flk variable assignments in flake_interface
3. Add detailed logging/debugging
4. Run side-by-side comparison with test file
5. Fix identified issues

---

## 📝 SUMMARY OF KEY FORMULAS

### T_bot under ice:
```
T_bot = T_wML - (T_wML - T_mnw) / [C_T * (1 - h_ML/D)]
```

### T_bot open water (deepening):
```
dT_bot/dt = [(Q_w - Q_bot + I_w - I_bot)/(ρ*c) - C_T*(T_wML - T_bot)*dh_ML/dt] * R_star / D
          + [I_mean_thermo - stuff] * R_TI / (D - h_ML) / (ρ*c)
          + [(1 - C_TT_2*R_TI)/C_T] * (T_wML - T_bot) * dC_T/dt
```

### h_ML convection:
```
dh_ML/dt = [flux_terms + radiation_terms] / denominator
where denominator = -c_cbl_2*R_star*Q_star/(ρ*c)/w_star + C_T*(T_wML - T_bot)
```

---

END OF ANALYSIS
