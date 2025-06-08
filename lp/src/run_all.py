import os
import json
from helper import load_all_instances
from solver import solve_instance

def run_all(input_dir, output_dir, solver_name="cbc", first=1, last=21, use_symmetry_breaking=False):
    os.makedirs(output_dir, exist_ok=True)
    data = load_all_instances(input_dir, first, last)

    for filename, (m, n, caps, sizes, D) in data.items():
        print(f"Solving {filename}")
        result = solve_instance(
        m, n, caps, sizes, D,
        timeout=300,
        solver_name=solver_name,
        use_symmetry_breaking=use_symmetry_breaking
        )

        label = f"{solver_name}_symbreak" if use_symmetry_breaking else solver_name
        result_dict = {label: result}


        instance_id = "".join(filter(str.isdigit, filename))
        out_path = os.path.join(output_dir, f"{instance_id}.json")
        with open(out_path, "w") as f:
            json.dump(result_dict, f, indent=2)
        print(f"Saved to {out_path}")

if __name__ == "__main__":
    run_all("input", "lp/res/mip_cbc_test", first=7, last=8, solver_name="cbc")