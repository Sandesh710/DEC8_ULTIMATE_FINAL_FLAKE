#!/usr/bin/env python3
"""
Run FLake Model for 365 days and compare with Fortran test file.
"""

import numpy as np
import sys

# Import all the FLake code from extracted notebook
# We'll execute it to get all the functions and classes
exec(open('extracted_notebook_code.py').read(), globals())

print("\n" + "="*80)
print("RUNNING FLAKE MODEL FOR 365 DAYS")
print("="*80)

# ============================================================================
# LOAD INPUT DATA
# ============================================================================

print("\nLoading input data from Potsdam80-96.dat...")

# Read input meteorological data (tab-separated)
# Format: timestep, Iw, T_air, wind, humidity, cloudiness
input_data = []
with open('Potsdam80-96.dat', 'r') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 6:
            input_data.append([float(x) for x in parts])

input_data = np.array(input_data)
print(f"Loaded {len(input_data)} timesteps of input data")

# ============================================================================
# SIMULATION PARAMETERS (from Heiligensee80-96.nml)
# ============================================================================

# Time parameters
del_time_lk = 86400.0  # Time step [s] = 1 day
time_step_number = 365  # Run for 365 days (1 year)
save_interval_n = 1    # Save every timestep

# Initial conditions
T_wML_init = 4.0  # Initial mixed layer temperature [°C]
T_bot_init = 4.0  # Initial bottom temperature [°C]
h_ML_init = 3.0   # Initial mixed layer depth [m]

# Lake parameters
depth_w_lk = 5.9      # Lake depth [m]
fetch_lk = 2.0e3      # Typical wind fetch [m]
sediments_on = True   # Use sediment layer
depth_bs_lk = 5.0     # Sediment layer depth [m]
T_bs_lk = 4.0         # Sediment temperature [°C]
latitude_lk = 51.0    # Latitude [degrees]

# Measurement heights
z_wind_m = 10.0   # Wind measurement height [m]
z_Taqa_m = 2.0    # Temperature/humidity measurement height [m]
z_Tw_m = 0.0      # Water temperature measurement depth [m]

# Water transparency (Mueggelsee - opaque water)
nband_optic = 1
frac_optic_arr = np.array([1.0] + [0.0]*9, dtype=np.float64)
extincoef_optic_arr = np.array([1.2] + [0.0]*9, dtype=np.float64)

# Create optic parameters for water
optic_par_water = OpticparMedium(
    nband_optic=np.int32(nband_optic),
    frac_optic=frac_optic_arr,
    extincoef_optic=extincoef_optic_arr
)

# Create optic parameters for ice (white ice)
extincoef_ice_arr = np.array([17.1] + [0.0]*9, dtype=np.float64)
optic_par_ice = OpticparMedium(
    nband_optic=np.int32(nband_optic),
    frac_optic=frac_optic_arr.copy(),
    extincoef_optic=extincoef_ice_arr
)

# Create optic parameters for snow (melting snow)
extincoef_snow_arr = np.array([15.0] + [0.0]*9, dtype=np.float64)
optic_par_snow = OpticparMedium(
    nband_optic=np.int32(nband_optic),
    frac_optic=frac_optic_arr.copy(),
    extincoef_optic=extincoef_snow_arr
)

# Albedo values
albedo_water = 0.07
albedo_ice = 0.60  # White ice
albedo_snow = 0.60  # Dry snow

# Coriolis parameter
omega_earth = 7.2921e-5  # Earth rotation rate [rad/s]
par_Coriolis = 2.0 * omega_earth * np.sin(latitude_lk * np.pi / 180.0)

print(f"\nSimulation parameters:")
print(f"  Lake depth: {depth_w_lk} m")
print(f"  Time step: {del_time_lk} s (1 day)")
print(f"  Number of steps: {time_step_number}")
print(f"  Coriolis parameter: {par_Coriolis:.6e} s^-1")

# ============================================================================
# INITIALIZE FLAKE STATE VARIABLES
# ============================================================================

# Convert initial temperatures to Kelvin
T_wML_0 = T_wML_init + tpl_T_r
T_bot_0 = T_bot_init + tpl_T_r
h_ML_0 = h_ML_init

# Initialize all state variables (previous timestep - "_p_flk")
T_snow_p_flk = tpl_T_f
T_ice_p_flk = tpl_T_f
T_wML_p_flk = T_wML_0
T_mnw_p_flk = T_wML_0
T_bot_p_flk = T_bot_0
T_B1_p_flk = T_bs_lk + tpl_T_r

h_snow_p_flk = 0.0
h_ice_p_flk = 0.0
h_ML_p_flk = h_ML_0
H_B1_p_flk = depth_bs_lk
C_T_p_flk = C_T_min

# Initialize next timestep variables ("_n_flk")
T_snow_n_flk = T_snow_p_flk
T_ice_n_flk = T_ice_p_flk
T_wML_n_flk = T_wML_p_flk
T_mnw_n_flk = T_mnw_p_flk
T_bot_n_flk = T_bot_p_flk
T_B1_n_flk = T_B1_p_flk

h_snow_n_flk = h_snow_p_flk
h_ice_n_flk = h_ice_p_flk
h_ML_n_flk = h_ML_p_flk
H_B1_n_flk = H_B1_p_flk
C_T_n_flk = C_T_p_flk

# Initialize other global variables
C_I_flk = 0.0
C_TT_flk = 0.0
C_Q_flk = 0.0
C_S_flk = 0.0

Phi_I_pr0_flk = 0.0
Phi_I_pr1_flk = 0.0
Phi_T_pr0_flk = 0.0

Q_snow_flk = 0.0
Q_ice_flk = 0.0
Q_w_flk = 0.0
Q_bot_flk = 0.0
Q_star_flk = 0.0
Q_sensible_flk = 0.0
Q_latent_flk = 0.0
Q_lwa_flk = 0.0
Q_lww_flk = 0.0

I_atm_flk = 0.0
I_snow_flk = 0.0
I_ice_flk = 0.0
I_w_flk = 0.0
I_h_flk = 0.0
I_bot_flk = 0.0
I_intm_0_h_flk = 0.0
I_intm_h_D_flk = 0.0

u_star_w_flk = 0.0
u_star_a_flk = 0.0
w_star_sfc_flk = 0.0
dMsnowdt_flk = 0.0

print("\nInitialized FLake state variables")
print(f"  T_wML = {T_wML_p_flk - tpl_T_r:.2f} °C")
print(f"  T_bot = {T_bot_p_flk - tpl_T_r:.2f} °C")
print(f"  h_ML = {h_ML_p_flk:.2f} m")

# ============================================================================
# STORAGE FOR RESULTS
# ============================================================================

results = {
    'No': [],
    'time': [],
    'Ts': [],
    'Tm': [],
    'Tb': [],
    'ufr_a': [],
    'ufr_w': [],
    'Wconv': [],
    'Qw': [],
    'Q_se': [],
    'Q_la': [],
    'I_w': [],
    'Q_lwa': [],
    'Q_lww': [],
    'h_ML': [],
    'C_T': [],
    'H_B1': [],
    'T_B1': [],
    'Qbot': [],
    'H_ice': [],
    'H_snow': [],
    'T_ice': [],
    'T_snow': []
}

# ============================================================================
# MAIN TIME LOOP
# ============================================================================

print("\n" + "="*80)
print("STARTING TIME INTEGRATION")
print("="*80)

for step in range(time_step_number + 1):  # 0 to 365

    # Get meteorological forcing for this timestep
    if step < len(input_data):
        I_w_input = input_data[step, 1]  # Incoming shortwave radiation [W/m²]
        T_air = input_data[step, 2]      # Air temperature [°C]
        wind = input_data[step, 3]       # Wind speed [m/s]
        humidity = input_data[step, 4]   # Relative humidity [-]
        cloudiness = input_data[step, 5] # Cloud cover [-]
    else:
        # Use last available values
        I_w_input = input_data[-1, 1]
        T_air = input_data[-1, 2]
        wind = input_data[-1, 3]
        humidity = input_data[-1, 4]
        cloudiness = input_data[-1, 5]

    # Convert to proper units
    T_air_K = T_air + tpl_T_r

    # Store results for this timestep (before advancing)
    results['No'].append(step)
    results['time'].append(step * del_time_lk / 86400.0)  # Convert to days

    # Surface temperature
    if h_ice_p_flk >= h_Ice_min_flk:
        if h_snow_p_flk >= h_Snow_min_flk:
            Ts = T_snow_p_flk - tpl_T_r
        else:
            Ts = T_ice_p_flk - tpl_T_r
    else:
        Ts = T_wML_p_flk - tpl_T_r

    results['Ts'].append(Ts)
    results['Tm'].append(T_mnw_p_flk - tpl_T_r)
    results['Tb'].append(T_bot_p_flk - tpl_T_r)
    results['ufr_a'].append(u_star_a_flk)
    results['ufr_w'].append(u_star_w_flk)
    results['Wconv'].append(w_star_sfc_flk)
    results['Qw'].append(Q_w_flk)
    results['Q_se'].append(Q_sensible_flk)
    results['Q_la'].append(Q_latent_flk)
    results['I_w'].append(I_w_flk)
    results['Q_lwa'].append(Q_lwa_flk)
    results['Q_lww'].append(Q_lww_flk)
    results['h_ML'].append(h_ML_p_flk)
    results['C_T'].append(C_T_p_flk)
    results['H_B1'].append(H_B1_p_flk)
    results['T_B1'].append(T_B1_p_flk - tpl_T_r)
    results['Qbot'].append(Q_bot_flk)
    results['H_ice'].append(h_ice_p_flk)
    results['H_snow'].append(h_snow_p_flk)
    results['T_ice'].append(T_ice_p_flk - tpl_T_r)
    results['T_snow'].append(T_snow_p_flk - tpl_T_r)

    if step % 50 == 0:
        print(f"Step {step:4d}: Ts={Ts:7.3f}°C, Tb={T_bot_p_flk-tpl_T_r:7.3f}°C, hML={h_ML_p_flk:6.3f}m, C_Q={C_Q_flk:6.3f}")

    # Don't advance on the last timestep (we just record it)
    if step == time_step_number:
        break

    # Call FLake driver to advance one timestep
    try:
        # First compute radiation fluxes
        flake_radflux(
            depth_w=depth_w_lk,
            albedo_water=albedo_water,
            albedo_ice=albedo_ice,
            albedo_snow=albedo_snow,
            opticpar_water=optic_par_water,
            opticpar_ice=optic_par_ice,
            opticpar_snow=optic_par_snow
        )

        # Then call the main driver
        T_sfc_n = flake_driver(
            depth_w=depth_w_lk,
            depth_bs=depth_bs_lk,
            T_bs=T_bs_lk + tpl_T_r,
            par_Coriolis=par_Coriolis,
            extincoef_water_typ=extincoef_optic_arr[0],
            del_time=del_time_lk,
            T_sfc_p=Ts + tpl_T_r
        )

        # Copy "next" values to "previous" for next iteration
        T_snow_p_flk = T_snow_n_flk
        T_ice_p_flk = T_ice_n_flk
        T_wML_p_flk = T_wML_n_flk
        T_mnw_p_flk = T_mnw_n_flk
        T_bot_p_flk = T_bot_n_flk
        T_B1_p_flk = T_B1_n_flk

        h_snow_p_flk = h_snow_n_flk
        h_ice_p_flk = h_ice_n_flk
        h_ML_p_flk = h_ML_n_flk
        H_B1_p_flk = H_B1_n_flk
        C_T_p_flk = C_T_n_flk

    except Exception as e:
        print(f"\n❌ ERROR at timestep {step}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n✅ Simulation completed successfully!")

# ============================================================================
# SAVE RESULTS TO FILE
# ============================================================================

output_file = 'python_output_365days.txt'
print(f"\nSaving results to {output_file}...")

with open(output_file, 'w') as f:
    # Header
    f.write("Results from Python FLake simulation (FIXED VERSION).\n")
    f.write(" No     time         Ts            Tm            Tb            ufr_a         ufr_w         Wconv         Qw            Q_se          Q_la          I_w           Q_lwa         Q_lww         h_ML          C_T           H_B1          T_B1         Qbot           H_ice        H_snow        T_ice         T_snow    \n")

    # Data
    for i in range(len(results['No'])):
        f.write(f"{results['No'][i]:6d} {results['time'][i]:11.5f} ")
        f.write(f"{results['Ts'][i]:13.5f} {results['Tm'][i]:13.5f} {results['Tb'][i]:13.5f} ")
        f.write(f"{results['ufr_a'][i]:13.6f} {results['ufr_w'][i]:13.6e} ")
        f.write(f"{results['Wconv'][i]:13.6e} {results['Qw'][i]:13.6f} ")
        f.write(f"{results['Q_se'][i]:13.6f} {results['Q_la'][i]:13.6f} ")
        f.write(f"{results['I_w'][i]:13.6f} {results['Q_lwa'][i]:13.6f} ")
        f.write(f"{results['Q_lww'][i]:13.6f} {results['h_ML'][i]:13.5f} ")
        f.write(f"{results['C_T'][i]:13.6f} {results['H_B1'][i]:13.5f} ")
        f.write(f"{results['T_B1'][i]:13.5f} {results['Qbot'][i]:13.6e} ")
        f.write(f"{results['H_ice'][i]:12.5f} {results['H_snow'][i]:13.5f} ")
        f.write(f"{results['T_ice'][i]:13.5f} {results['T_snow'][i]:13.5f}\n")

print(f"✅ Saved {len(results['No'])} timesteps to {output_file}")

print("\n" + "="*80)
print("RUN COMPLETE")
print("="*80)
