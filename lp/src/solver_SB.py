import time as pytime
from pulp import *
from helper import format_output

def solve_instance(m, n, capacities, sizes, distance_matrix, timeout=300, solver_name="cbc"):
    model = LpProblem("MCP_MIP_SymmetryBreaking", LpMinimize)

    num_nodes = n + 1  # items + depot
    depot = n

    # Variables
    x = LpVariable.dicts("x", (range(num_nodes), range(num_nodes), range(m)), cat="Binary")  # Routing
    u = LpVariable.dicts("u", (range(n), range(m)), lowBound=0, upBound=n, cat="Integer")     # Subtour elimination
    courier_weights = [
        LpVariable(name=f"weight_{k}", lowBound=0, upBound=capacities[k], cat="Integer")
        for k in range(m)
    ]
    courier_distance = [
        LpVariable(name=f"dist_{k}", lowBound=0, cat="Continuous") for k in range(m)
    ]
    D_max = LpVariable("D_max", lowBound=0, cat="Continuous")

    # Coupling structure
    coupled = [[0]*n for _ in range(n)]

    ordering = [LpVariable(f"order_{j}", 1, n, cat="Integer") for j in range(n)]
    ord_matrix = [[LpVariable(f"ord_{i}_{j}", cat="Binary") for j in range(n)] for i in range(n)]

    model += D_max

    # Constraint 1: Capacity constraint per courier
    for k in range(m):
        model += courier_weights[k] == lpSum(x[i][j][k] * sizes[j] for i in range(num_nodes) for j in range(n))
        model += courier_weights[k] <= capacities[k]

    # Constraint 2: Each item is visited exactly once
    for j in range(n):
        model += lpSum(x[i][j][k] for i in range(num_nodes) for k in range(m) if i != j) == 1

    # Constraint 3: Flow conservation per courier
    for k in range(m):
        for j in range(n):
            model += lpSum(x[i][j][k] for i in range(num_nodes) if i != j) == lpSum(x[j][i][k] for i in range(num_nodes) if i != j)

    # Constraint 4: Each courier departs from and returns to depot exactly once
    for k in range(m):
        model += lpSum(x[depot][j][k] for j in range(n)) == 1
        model += lpSum(x[j][depot][k] for j in range(n)) == 1

    # Constraint 5: Subtour elimination (MTZ)
    for k in range(m):
        for i in range(n):
            for j in range(n):
                if i != j:
                    model += u[i][k] - u[j][k] + (n + 1) * x[i][j][k] <= n

    # Constraint 6: Distance accumulation and D_max bound
    for k in range(m):
        model += courier_distance[k] == lpSum(
            distance_matrix[i][j] * x[i][j][k] for i in range(num_nodes) for j in range(num_nodes) if i != j
        )
        model += D_max >= courier_distance[k]

    # Constraint 7: Coupling - same courier
    for i in range(n):
        for j in range(n):
            if coupled[i][j]:
                for k in range(m):
                    model += lpSum(x[a][i][k] for a in range(num_nodes) if a != i) == lpSum(x[a][j][k] for a in range(num_nodes) if a != j)

    # Constraint 8: Coupling - ordering dominance
    for i in range(n):
        for j in range(n):
            if coupled[i][j]:
                model += ordering[i] >= ordering[j] + 1

    # Constraint 9: Ordering uniqueness via permutation matrix
    for i in range(n):
        model += lpSum(ord_matrix[i][j] for j in range(n)) == 1
    for j in range(n):
        model += lpSum(ord_matrix[i][j] for i in range(n)) == 1
    for i in range(n):
        model += ordering[i] == lpSum(ord_matrix[i][j] * (j + 1) for j in range(n))

    # Constraint 10: Symmetry breaking — enforce lexicographic courier ordering (heuristic)
    for k in range(m - 1):
        model += courier_distance[k] <= courier_distance[k + 1]

    # Solve
    solver = (
        PULP_CBC_CMD(msg=0, timeLimit=timeout) if solver_name == "cbc"
        else GLPK_CMD(msg=0, timeLimit=timeout)
    )
    start = pytime.time()
    model.solve(solver)
    end = pytime.time()

    seconds = end - start
    optimal = model.status == 1
    obj_val = D_max.varValue if D_max.varValue is not None else 0

    sol = [[] for _ in range(m)]
    for k in range(m):
        for j in range(n):
            if any(value(x[i][j][k]) == 1 for i in range(num_nodes) if i != j):
                sol[k].append(j + 1)

    return format_output(seconds, optimal, obj_val, sol)