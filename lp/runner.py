import os
import json
from helper import load_all_instances
from solver import MIPSolver

def run_all(input_dir, output_dir, solver_name="cbc", first=1, last=21,  use_symmetry_breaking=False, timeout=300):
    os.makedirs(output_dir, exist_ok=True)
    data = load_all_instances(input_dir, first, last)

    for filename, (m, n, caps, sizes, D) in data.items():
        print(f"Solving {filename}")
        result = MIPSolver(
        m, n, caps, sizes, D,
        timeout=timeout,
        solver_name=solver_name,
        use_symmetry_breaking=use_symmetry_breaking
        )

        label = solver_name.lower() + "_symmetry_breaking" if use_symmetry_breaking else solver_name.lower() + "_no_symmetry_breaking"
        
        instance_id = "".join(filter(str.isdigit, filename)).zfill(2)
        out_path = os.path.join(output_dir, f"{instance_id}.json")

        if os.path.exists(out_path):
            with open(out_path, "r") as f:
                result_dict = json.load(f)
        else:
            result_dict = {}

        result_dict[label] = result

        with open(out_path, "w") as f:
            json.dump(result_dict, f, indent=2)
        print(f"Saved to {out_path}")

if __name__ == "__main__":
    run_all("../input", "../output/lp", first=1, last=10, solver_name="cbc", use_symmetry_breaking=False, timeout=300)
    run_all("../input", "../output/lp", first=1, last=10, solver_name="cbc", use_symmetry_breaking=True, timeout=300)
    run_all("../input", "../output/lp", first=1, last=10, solver_name="glpk", use_symmetry_breaking=False, timeout=300)
    run_all("../input", "../output/lp", first=1, last=10, solver_name="glpk", use_symmetry_breaking=True, timeout=300)