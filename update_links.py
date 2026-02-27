import re
import os
import shutil

base_dir = "/Users/***/Documents/GitHub/research"
temp_dir = os.path.join(base_dir, "temp")
code_dir = os.path.join(base_dir, "code/analysis/ftd_research")

# Move items
items_to_move = [
    "origin_cascade_analysis",
    "energy_pattern_analysis",
    "resonance_deep_dive",
    "test_verify_v3.py",
    "test_verify_predictions.py",
    "test_verify_v2.py"
]

for item in items_to_move:
    src = os.path.join(temp_dir, item)
    dst = os.path.join(code_dir, item)
    if os.path.exists(src):
        # Remove target if exists
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)
        print(f"Moved {item} to code_dir")
    else:
        print(f"Item not found: {src}")

# Fix markdown links
files_to_fix = [
    "posts/03_the_failure_waterfall/03_the_cavity.md",
    "posts/03_the_failure_waterfall/02_the_resonance.md",
    "papers/06_resonance_and_cavity.md"
]

for fl in files_to_fix:
    fl_path = os.path.join(base_dir, fl)
    if os.path.exists(fl_path):
        with open(fl_path, 'r') as f:
            content = f.read()
        
        # Replace temp -> code/analysis/ftd_research
        # Both in URLs and relative paths
        content = content.replace("temp/origin_cascade_analysis", "code/analysis/ftd_research/origin_cascade_analysis")
        content = content.replace("temp/energy_pattern_analysis", "code/analysis/ftd_research/energy_pattern_analysis")
        content = content.replace("temp/resonance_deep_dive", "code/analysis/ftd_research/resonance_deep_dive")
        content = content.replace("temp/test_verify_v3.py", "code/analysis/ftd_research/test_verify_v3.py")
        content = content.replace("temp/test_verify_predictions.py", "code/analysis/ftd_research/test_verify_predictions.py")
        content = content.replace("temp/test_verify_v2.py", "code/analysis/ftd_research/test_verify_v2.py")
        
        with open(fl_path, 'w') as f:
            f.write(content)
        print(f"Updated links in {fl}")
