import time as pytime
from pulp import *
from helper import format_output

def solve_instance(m, n, capacities, sizes, distance_matrix, coupled_pairs=None, timeout=300, solver_name="cbc"):
    model = LpProblem("MCP_MIP_Standardized", LpMinimize)

    num_nodes = n + 1
    depot = n

    # Decision Variables
    x = LpVariable.dicts("x", (range(num_nodes), range(num_nodes), range(m)), cat="Binary")  # Routing
    u = LpVariable.dicts("u", (range(n), range(m)), lowBound=0, upBound=n, cat="Integer")     # Subtour elimination
    courier_weights = [
        LpVariable(f"weight_{k}", lowBound=0, upBound=capacities[k], cat="Integer") for k in range(m)
    ]
    courier_distance = [
        LpVariable(f"dist_{k}", lowBound=0, cat="Continuous") for k in range(m)
    ]
    D_max = LpVariable("D_max", lowBound=0, cat="Continuous")

    ordering = [LpVariable(f"order_{j}", 1, n, cat="Integer") for j in range(n)]
    ord_matrix = [[LpVariable(f"ord_{i}_{j}", cat="Binary") for j in range(n)] for i in range(n)]

    model += D_max  # Objective

    # Constraint 1: Capacity per courier
    for k in range(m):
        model += courier_weights[k] == lpSum(x[i][j][k] * sizes[j] for i in range(num_nodes) for j in range(n))
        model += courier_weights[k] <= capacities[k]

    # Constraint 2: Each item is visited exactly once
    for j in range(n):
        model += lpSum(x[i][j][k] for i in range(num_nodes) for k in range(m) if i != j) == 1

    # Constraint 3: Flow conservation
    for k in range(m):
        for j in range(n):
            model += lpSum(x[i][j][k] for i in range(num_nodes) if i != j) == lpSum(x[j][i][k] for i in range(num_nodes) if i != j)

    # Constraint 4: Depot departure and return
    for k in range(m):
        model += lpSum(x[depot][j][k] for j in range(n)) == 1
        model += lpSum(x[j][depot][k] for j in range(n)) == 1

    # Constraint 5: Subtour elimination (MTZ)
    for k in range(m):
        for i in range(n):
            for j in range(n):
                if i != j:
                    model += u[i][k] - u[j][k] + (n + 1) * x[i][j][k] <= n

    # Constraint 6: Distance tracking and max bound
    for k in range(m):
        model += courier_distance[k] == lpSum(
            distance_matrix[i][j] * x[i][j][k]
            for i in range(num_nodes) for j in range(num_nodes) if i != j
        )
        model += D_max >= courier_distance[k]

    # Constraint 7 & 8: Coupled deliveries
    if coupled_pairs:
        for i, j in coupled_pairs:
            for k in range(m):
                model += lpSum(x[a][i][k] for a in range(num_nodes) if a != i) == lpSum(x[a][j][k] for a in range(num_nodes) if a != j)
            model += ordering[i] >= ordering[j] + 1

    # Constraint 9: Unique ordering using permutation matrix
    for i in range(n):
        model += lpSum(ord_matrix[i][j] for j in range(n)) == 1
    for j in range(n):
        model += lpSum(ord_matrix[i][j] for i in range(n)) == 1
    for i in range(n):
        model += ordering[i] == lpSum(ord_matrix[i][j] * (j + 1) for j in range(n))

    # Solver selection
    solver = (
        PULP_CBC_CMD(msg=0, timeLimit=timeout) if solver_name == "cbc"
        else GLPK_CMD(msg=0, timeLimit=timeout)
    )

    # Solve
    start = pytime.time()
    model.solve(solver)
    end = pytime.time()

    # Extract results
    seconds = end - start
    optimal = model.status == 1
    obj_val = D_max.varValue if D_max.varValue is not None else 0

    sol = [[] for _ in range(m)]
    for k in range(m):
        for j in range(n):
            if any(value(x[i][j][k]) == 1 for i in range(num_nodes) if i != j):
                sol[k].append(j + 1)

    return format_output(seconds, optimal, obj_val, sol)
