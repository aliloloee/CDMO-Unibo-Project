import os
import json
import subprocess
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Any
from setup.config import glob

class CPSolver:
    def __init__(self,data, timeout: int = 300):
        
        self.timeout = timeout
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(self.base_dir, "cp", "Models")
        self.output_dir = os.path.join(self.base_dir, "output", "cp")
        self.input_dir = os.path.join(self.base_dir, "input")
        self.data = os.path.join(self.input_dir, f"inst{int(data):02d}.dat")
        self.window = glob.obtain('app')

    def print_output(self, message: str):
        """Print output to the GUI window"""
        if self.window:
            self.window.print_output(message)
        else:
            print(message)

    def read_dat_file(self, file_path: str) -> Tuple[int, int, List[int], List[int], List[List[int]]]:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Remove empty lines and strip whitespace
        lines = [line.strip() for line in lines if line.strip()]
        
        m = int(lines[0])  # Number of couriers
        n = int(lines[1])  # Number of items
        l = [int(x) for x in lines[2].split()]  # Couriers capacities
        s = [int(x) for x in lines[3].split()]  # Items sizes
        
        # Distance matrix
        D = []
        for line in lines[4:]:
            row = [int(x) for x in line.split()]
            D.append(row)
        
        return m, n, l, s, D

    def create_dzn_file(self, m: int, n: int, l: List[int], s: List[int], D: List[List[int]]) -> str:
        dzn_file = f"""m = {m};
        n = {n};
        l = {l};
        s = {s};
        D = [|"""
        
        # Format the distance matrix with | separators between rows
        matrix_rows = []
        for row in D:
            matrix_rows.append(" " + ", ".join(map(str, row)))
        
        dzn_file += " |".join(matrix_rows)
        dzn_file += " |];"
        
        return dzn_file

    def parse_mzn_output(self, output_string: str, timeout: int) -> Dict[str, Any]:
        obj_value = None
        solution = []
        max_path_length = None
        path_lengths = []
        courier_distances = []

        # Extract objective value
        match = re.search(r"Optimized maximum distance:\s*(\d+)", output_string)
        if match:
            obj_value = int(match.group(1))
            self.print_output(f"Optimized maximum distance: {obj_value}")

        # Extract max path length
        match = re.search(r"max path length:\s*(\d+)", output_string)
        if match:
            max_path_length = int(match.group(1))
            self.print_output(f"\nmax path length: {max_path_length}")

        # Extract path lengths
        match = re.search(r"path length of each couriers:\s*\[(.*?)\]", output_string)
        if match:
            path_lengths = [int(x.strip()) for x in match.group(1).split(',')]
            self.print_output(f"\npath length of each couriers: {path_lengths}")

        # Extract courier paths and distances
        self.print_output("\ncourier pathes and total distances:")
        path_pattern = re.compile(r"courier (\d+):\s*path:\s*([\d\s]+)\s*total distance:\s*(\d+)")
        for match in path_pattern.finditer(output_string):
            courier_num = int(match.group(1))
            path = list(map(int, match.group(2).strip().split()))
            distance = int(match.group(3))
            solution.append(path)
            courier_distances.append(distance)
            self.print_output(f"courier {courier_num}:")
            self.print_output(f"    path: {' '.join(map(str, path))}")
            self.print_output(f"    total distance: {distance}")

        # Extract elapsed time
        time_match = re.search(r"% time elapsed: ([\d.]+) s", output_string)
        elapsed_time = float(time_match.group(1)) if time_match else timeout
        self.print_output(f"\n% time elapsed: {elapsed_time:.2f} s")

        return {
            "time": min(timeout, int(elapsed_time)),
            "optimal": elapsed_time < timeout,
            "obj": obj_value,
            "sol": solution if solution else None,
            "max_path_length": max_path_length,
            "path_lengths": path_lengths,
            "courier_distances": courier_distances
        }

    def run_minizinc_model(self, model_path: str, dzn_path: str, solver: str) -> Dict[str, Any]:
        try:
            process = subprocess.Popen(
                [
                    "minizinc",
                    "-m", model_path,
                    "-d", dzn_path,
                    "--solver", solver,
                    "--output-time",
                    "--solver-time-limit", str(self.timeout * 1000),
                    "-s"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False
            )

            output_lines = []
            for line in iter(process.stdout.readline, ''):
                # Only print lines that contain solution information
                if any(key in line.lower() for key in ['optimized', 'path:', 'time elapsed']):
                    self.print_output(line.strip())
                output_lines.append(line)
            
            process.stdout.close()
            process.wait(timeout=self.timeout + 1)

            output_string = "".join(output_lines)
            return self.parse_mzn_output(output_string, self.timeout)

        except subprocess.TimeoutExpired:
            self.print_output(f"MiniZinc process timed out for model {model_path}.")
            return {
                "time": self.timeout,
                "optimal": False,
                "obj": None,
                "sol": None
            }

    def solve(self) -> Dict[str, Any]:
        """
        Solve the given instance using the CP solver.
        
        Returns:
            Dictionary containing the solution results
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Read and convert the instance
            m, n, l, s, D = self.read_dat_file(self.data)
            dzn_content = self.create_dzn_file(m, n, l, s, D)
            
            # Generate output filenames
            instance_name = Path(self.data).stem
            dzn_file = os.path.join(self.output_dir, f"{instance_name}.dzn")
            json_file = os.path.join(self.output_dir, f"{instance_name}.json")
            
            # Save the .dzn file
            with open(dzn_file, 'w') as f:
                f.write(dzn_content)
            
            
            # Define the models to run
            models = {
                "gecode": "MCP_Base_Version.mzn",
                "gecode_symmetry": "MCP_LB_SB.mzn",
                "gecode_symmetry_heuristic": "MCP_LB_SB_Heuristic_Gecode.mzn",
                "chuffed": "MCP_Base_Version.mzn",
                "chuffed_symmetry": "MCP_LB_SB.mzn",
                "chuffed_symmetry_heuristic": "MCP_LB_SB_Heuristic_Chuffed.mzn"
            }
            
            # Run all models and collect results
            results = {}
            for model_name, model_file in models.items():
                model_path = os.path.join(self.models_dir, model_file)
                if not os.path.exists(model_path):
                    self.print_output(f"Error: Model file not found: {model_path}")
                    continue
                results[model_name] = self.run_minizinc_model(model_path, dzn_file, model_name.split('_')[0])
            
            # Save results to JSON
            with open(json_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.print_output("\nFinal Results Summary:")
            for model_name, result in results.items():
                self.print_output(f"\n{model_name}:")
                self.print_output(f"  Time: {result['time']} seconds")
                self.print_output(f"  Optimal: {result['optimal']}")
                self.print_output(f"  Objective: {result['obj']}")
                if result['sol']:
                    self.print_output("  Solution paths:")
                    for i, path in enumerate(result['sol']):
                        self.print_output(f"    Courier {i+1}: {path}")
            
            return results
            
        except Exception as e:
            self.print_output(f"Error solving instance {self.data}: {str(e)}")
            return {
                "time": self.timeout,
                "optimal": False,
                "obj": None,
                "sol": None
            }
