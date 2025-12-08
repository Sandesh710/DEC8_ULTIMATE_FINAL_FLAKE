#!/usr/bin/env python3
"""
Fix the critical C_TT_flk and C_Q_flk bug in the FLake notebook.

This script fixes the tuple assignment issue in Cell 22, line 431.
"""

import json
import sys

def fix_notebook(input_file, output_file):
    """
    Fix the C_TT_flk, C_Q_flk tuple assignment bug.

    The bug is in Cell 22, where simultaneous tuple assignment uses the old value of C_TT_flk.
    """
    print(f"Reading notebook: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    print(f"Total cells: {len(notebook['cells'])}")

    # Target cell 22 (0-indexed)
    cell_idx = 22
    cell = notebook['cells'][cell_idx]

    if cell['cell_type'] != 'code':
        print(f"ERROR: Cell {cell_idx} is not a code cell!")
        return False

    # Get the source as a list of lines
    source_lines = cell['source']

    print(f"Cell {cell_idx} has {len(source_lines)} lines")

    # Find the buggy line
    buggy_line = "        C_TT_flk, C_Q_flk = C_TT_1 * C_T_p_flk - C_TT_2, 2.0 * C_TT_flk / C_T_p_flk\n"

    # Fixed lines (as a list)
    fixed_lines = [
        "        C_TT_flk = C_TT_1 * C_T_p_flk - C_TT_2\n",
        "        C_Q_flk = 2.0 * C_TT_flk / C_T_p_flk\n"
    ]

    # Find and replace
    found = False
    for i, line in enumerate(source_lines):
        if line == buggy_line:
            print(f"Found buggy line at index {i}")
            print(f"  OLD: {line.strip()}")

            # Replace with two lines
            source_lines[i] = fixed_lines[0]
            source_lines.insert(i+1, fixed_lines[1])

            print(f"  NEW LINE 1: {fixed_lines[0].strip()}")
            print(f"  NEW LINE 2: {fixed_lines[1].strip()}")

            found = True
            break

    if not found:
        print("ERROR: Could not find the buggy line!")
        print("Searching for similar lines...")
        for i, line in enumerate(source_lines):
            if 'C_TT_flk, C_Q_flk' in line or 'C_TT_flk' in line and 'C_Q_flk' in line:
                print(f"  Line {i}: {line.strip()}")
        return False

    # Update the cell
    notebook['cells'][cell_idx]['source'] = source_lines

    # Write the fixed notebook
    print(f"\nWriting fixed notebook to: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=1, ensure_ascii=False)

    print("✅ Fix applied successfully!")
    print(f"\nNext steps:")
    print("1. Open {output_file} in Jupyter")
    print("2. Run all cells")
    print("3. Compare Tb and hML outputs with Fortran test file")

    return True

if __name__ == '__main__':
    input_notebook = 'FLAKE_Model_CORRECTED_FINAL_helsinngese.ipynb'
    output_notebook = 'FLAKE_Model_CORRECTED_FINAL_helsinngese_FIXED.ipynb'

    success = fix_notebook(input_notebook, output_notebook)

    sys.exit(0 if success else 1)
