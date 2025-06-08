import os

def parse_dat_file(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    m = int(lines[0])
    n = int(lines[1])
    capacities = list(map(int, lines[2].split()))
    sizes = list(map(int, lines[3].split()))
    distance_matrix = [list(map(int, line.split())) for line in lines[4:4 + n + 1]]
    return m, n, capacities, sizes, distance_matrix

def load_all_instances(input_dir, first=1, last=21):
    data = {}
    for idx in range(first, last + 1):
        filename = f"inst{idx:02d}.dat"
        path = os.path.join(input_dir, filename)
        if os.path.exists(path):
            data[filename] = parse_dat_file(path)
    return data

def format_output(seconds, optimal, obj, solution):
    return {
        "time": int(seconds),      # Round down the computation time to an integer
        "optimal": optimal,        # Whether the solution is proven to be optimal
        "obj": int(obj),           # Objective value (e.g., D_max), rounded to int
        "sol": solution            # Solution: list of items assigned to each courier
    }