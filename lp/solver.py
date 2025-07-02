import time as pytime
from pulp import *
from lp.helper import format_output

def LPSolver(m, n, capacities, sizes, distance_matrix, coupled_pairs=None, timeout=300, solver_name="cbc", use_symmetry_breaking=False):
    model = LpProblem("MCP_MIP", LpMinimize)

    num_nodes = n + 1
    depot = n

    # Decision Variables
    x = LpVariable.dicts("x", (range(num_nodes), range(num_nodes), range(m)), cat="Binary")
    u = LpVariable.dicts("u", (range(n), range(m)), lowBound=0, upBound=n, cat="Integer")
    courier_weights = [LpVariable(f"weight_{k}", lowBound=0, upBound=capacities[k], cat="Integer") for k in range(m)]
    courier_distance = [LpVariable(f"dist_{k}", lowBound=0, cat="Continuous") for k in range(m)]
    D_max = LpVariable("D_max", lowBound=0, cat="Continuous")

    ordering = [LpVariable(f"order_{j}", 1, n, cat="Integer") for j in range(n)]
    ord_matrix = [[LpVariable(f"ord_{i}_{j}", cat="Binary") for j in range(n)] for i in range(n)]

    model += D_max  # Objective

    # Constraint 1: Capacity
    for k in range(m):
        model += courier_weights[k] == lpSum(x[i][j][k] * sizes[j] for i in range(num_nodes) for j in range(n))
        model += courier_weights[k] <= capacities[k]

    # Constraint 2: Each item visited exactly once
    for j in range(n):
        model += lpSum(x[i][j][k] for i in range(num_nodes) for k in range(m) if i != j) == 1

    # Constraint 3: Flow conservation
    for k in range(m):
        for j in range(n):
            model += lpSum(x[i][j][k] for i in range(num_nodes) if i != j) == lpSum(x[j][i][k] for i in range(num_nodes) if i != j)

    # Constraint 4: Depot entry/exit
    for k in range(m):
        model += lpSum(x[depot][j][k] for j in range(n)) == 1
        model += lpSum(x[j][depot][k] for j in range(n)) == 1

    # Constraint 5: MTZ Subtour elimination
    for k in range(m):
        for i in range(n):
            for j in range(n):
                if i != j:
                    model += u[i][k] - u[j][k] + (n + 1) * x[i][j][k] <= n

    # Constraint 6: Distance accumulation
    for k in range(m):
        model += courier_distance[k] == lpSum(
            distance_matrix[i][j] * x[i][j][k] for i in range(num_nodes) for j in range(num_nodes) if i != j
        )
        model += D_max >= courier_distance[k]
        
    # Constraint 7: Coupled items on same courier
    if coupled_pairs:
        for i, j in coupled_pairs:
            for k in range(m):
                model += lpSum(x[a][i][k] for a in range(num_nodes) if a != i) == \
                         lpSum(x[a][j][k] for a in range(num_nodes) if a != j)

    # Constraint 8: Coupled items ordering
    if coupled_pairs:
        for i, j in coupled_pairs:
            model += ordering[i] >= ordering[j] + 1

    # Constraint 9: Ordering uniqueness
    for i in range(n):
        model += lpSum(ord_matrix[i][j] for j in range(n)) == 1
    for j in range(n):
        model += lpSum(ord_matrix[i][j] for i in range(n)) == 1
    for i in range(n):
        model += ordering[i] == lpSum(ord_matrix[i][j] * (j + 1) for j in range(n))

    # Constraint 10: Optional symmetry breaking
    if use_symmetry_breaking:
        for k in range(m - 1):
            model += courier_distance[k] <= courier_distance[k + 1]

    # Solve
    solver = PULP_CBC_CMD(msg=0, timeLimit=timeout) if solver_name == "cbc" else GLPK_CMD(msg=0, timeLimit=timeout)
    start = pytime.time()
    model.solve(solver)
    end = pytime.time()

    raw_seconds = end - start

    if raw_seconds > timeout:
        seconds = 300
        optimal = False
    else:
        seconds = int(raw_seconds)
        optimal = model.status == LpStatusOptimal

    # Extract paths
    paths = [[] for _ in range(m)]
    for k in range(m):
        # Reconstruct tour starting from depot
        current = depot
        visited = set()
        while True:
            next_node = None
            for j in range(num_nodes):
                if j != current and value(x[current][j][k]) == 1:
                    next_node = j
                    break
            if next_node is None or next_node == depot:
                break
            if next_node < n:
                paths[k].append(next_node + 1)
            visited.add(next_node)
            current = next_node

    #if no solution is found, return empty paths
    if all(len(p) == 0 for p in paths):
        seconds = timeout
        optimal = False
        obj_val = 0
        sol = []
        return format_output(seconds, optimal, obj_val, sol)
    
    else:    
        # Compute actual max distance
        def compute_path_distance(path):
            full_path = [depot] + [p - 1 for p in path] + [depot]
            dist = 0
            for i in range(len(full_path) - 1):
                dist += distance_matrix[full_path[i]][full_path[i + 1]]
            return dist

        obj_val = max(compute_path_distance(p) for p in paths) if any(paths) else 0
        sol  = paths
        
        return format_output(seconds, optimal, obj_val, sol)
