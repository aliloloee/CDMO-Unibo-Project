from z3.z3 import Bool, If, Or, Not, And, Implies, Xor
import math

from sat import settings

from sat.utils import to_binary, greater_eq


############################################################################

def at_least_one_bw(bool_vars):
    """
    :param bool_vars:  array of z3 variables
    :return: Or between all the z3 variables in bool_vars
    """
    return Or(bool_vars)

def at_most_one_bw(bool_vars, name):
    """
    Checks that a vector contains at most a value == True
    :param bool_vars: array of Z3 variables
    :param name: name associated to bool_vars
    :return: And of constraints
    """
    constraints = []
    n = len(bool_vars)
    m = math.ceil(math.log2(n))
    r = [Bool(f"r_{name}_{i}") for i in range(m)]
    binaries = [to_binary(i, m) for i in range(n)]
    for i in range(n):
        for j in range(m):
            phi = Not(r[j])
            if binaries[i][j]:
                phi = r[j]
            constraints.append(Or(Not(bool_vars[i]), phi))
    return And(constraints)

def exactly_one_bw(bool_vars, name):
    """
    checks that in a vector there exactly a value == True
    :param bool_vars: array of Z3 variables
    :param name: name associated to bool_vars
    :return: And of constraints
    """
    return And(at_least_one_bw(bool_vars), at_most_one_bw(bool_vars, name))


def binary_sum(a, b, res, name):
    """
    This function ensures that the binary sum of a and b equals res using Z3 constraints

    :param a: first binary vector of z3 variables
    :param b: second binary vector of z3 variables
    :param res: vector of z3 variables containing the result of the sum,
    :param name: name associated to the sum
    :return: constraints which are true if the results is equal to res
    """
    carries = [Bool(f"C{name}_{i}") for i in range(len(a) + 1)]

    c1 = And([(((a[i] == b[i]) == res[i]) == carries[i + 1]) for i in range(len(res))])

    c2 = And(Not(carries[0]), Not(carries[-1]))

    c3 = And(
        [
            carries[i] == Or(And(a[i], b[i]), And(a[i], carries[i + 1]), And(b[i], carries[i + 1]))
            for i in range(len(res))
        ]
    )
    return And(c1, c2, c3)


def binary_increment(a, bit, res, name):
    """
    :param a: input vector of z3 variables
    :param bit: bit to be added to the input vector
    :param res: result of the computation
    :param name: name associated with the operator and the input values
    :return: constraints which are true if res contains the binary increment
    """
    carries = [Bool(f"C{name}_{i}") for i in range(len(a))]
    c1 = carries[0] == bit

    c2 = And([carries[i + 1] == And(a[len(a) - 1 - i], carries[i]) for i in range(len(a) - 1)])

    c3 = And([res[len(a) - 1 - i] == Xor(a[len(a) - 1 - i], carries[i]) for i in range(len(a))])

    return And(c1, c2, c3)

############################################################################


def set_constraints(input_data, solver, symmetry=None):

    if solver is None:
        raise ValueError("Solver is not initialized")

    couriers      = input_data[0]
    items         = input_data[1]
    couriers_size = input_data[2]
    item_size     = input_data[3]
    distances     = input_data[4]
    loads_bits    = input_data[5]
    distances_bits = input_data[6]
    sub_tour      = input_data[7]

    # 1. matrix of assignment
    # couriers * (items + 1) - last column is the depot
    asg = [[Bool(f'asg{i}_{j}') for j in range(items + 1)] for i in range(couriers)]

    # 2. matrix of orderings for global visit sequence (n+2)*(n+2)
    # why 'n+2' ? 1 is for "starting at depot", 1 is for "returning to depot"
    orderings = [[Bool(f'orderings{i}_{j}') for j in range(items + 2)] for i in range(items + 2)]

    # 3. matrix of couples, containing travel transitions (n+1)*(n+1)
    couples = [[Bool(f'couples{i}_{j}') for j in range(items + 1)] for i in range(items + 1)]

    # 4. matrix of courier loads m*(n+1)*load_bits
    # courier_loads[i][j] --> The binary cumalative load of the i-th courier after processing j items
    courier_loads = [[[Bool(f'loads{i}_{j}_{k}') for j in range(loads_bits)] for k in range(items + 1)]
                        for i in range(couriers)]

    # 5. matrix of courier distances
    # according to couples matrix which was (n+1)*(n+1), we have (n+1)^2+1 possible transitions
    # couriers_distances[k][x] --> The binary cumalative distance of the k-th courier after traveling the x-th possible transition
    couriers_distances = [
        [[Bool(f"dist_{k}_{i}_{j}") for j in range(distances_bits)] for i in range((items + 1) ** 2 + 1)]
        for k in range(couriers)]

    # 6. Sum structures
    bits_sum = math.ceil(math.log2(items))
    sum_asg = [[Bool(f'sum_asg{i}_{j}') for i in range(bits_sum)] for j in range(couriers + 1)]
    sum_first_row = [[Bool(f'sum_start{i}_{j}') for i in range(bits_sum)] for j in range(items + 1)]
    sum_first_col = [[Bool(f'sum_end{i}_{j}') for i in range(bits_sum)] for j in range(items + 1)]



    ## Constraints on asg matrix
    # 1) Each item must be assigned to a courier
    # Each of the columns in asg matrix, except the last one which is related to depot, must have exactly one True value 
    for i in range(items):
        solver.add(exactly_one_bw([asg[k][i] for k in range(couriers)], name=f'items_{i}'))

    # 2) If a courier carry at least an item, then it must move from depot
    for k in range(couriers):
        solver.add(
            If(
                Or(asg[k][:-1]), asg[k][-1], asg[k][-1] == False
            )
        )
    
    # 3) If we are in a sub_tour scenario (all couriers can carry all items), then all couriers must be used
    solver.add(
            Implies(
                sub_tour,
                And([asg[k][-1] for k in range(couriers)])
            )
        )


    ## Constraints on orderings matrix
    # 1) Each column in orderings matrix must have exactly one True value
    for i in range(items + 2):
        solver.add(exactly_one_bw([orderings[j][i] for j in range(items + 2)], f'order_col_{i}'))

    # 2) Each row in orderings matrix must have exactly one True value
    for i in range(items + 2):
        solver.add(exactly_one_bw(orderings[i], f'orderings_{i}'))

    # 3) Each tour starts at origin depot and ends at return depot
    solver.add(
            And(orderings[0][-2], orderings[-1][-1])
        )


    ## Constraints on couples matrix
    ## The 1st and 2nd consraints below assure each item appears exactly once in a route
    # 1) Each item must have exactly one outgoing transition to another node
    for i in range(items):
        solver.add(exactly_one_bw(couples[i], f'couples_row_{i}'))

    # 2) Each item must have exactly one incoming transition from another node
    for i in range(items):
        solver.add(exactly_one_bw([couples[j][i] for j in range(items + 1)], f'couples_col{i}'))

    # 3) No self loop, disallowing a node to travel to itself
    solver.add(
            Not(Or(
                [couples[i][i] for i in range(items + 1)]
            ))
        )
    
    # 4) Consistency with courier assignment
    # If we have a transition from i to j, then we must have a courier assigned to both i and j
    for i in range(items + 1):
        for j in range(items + 1):
            if i != j:
                solver.add(
                    Implies(
                        couples[i][j],
                        Or([And(asg[k][i], asg[k][j]) for k in range(couriers)])
                    )
                )

    # 5) Consistency with orderings
    for i in range(items + 1):
        for j in range(items + 1):
            # If we go from i to the return depot, then node i must appear before the return depot in the tour
            # Also we ensure that the return depot is the last node in the tour
            if j == items:
                solver.add(
                    Implies(
                        couples[i][j],
                        greater_eq(
                            [orderings[k][i] for k in range(items + 1)],
                            [orderings[k][-1] for k in range(items + 1)],
                            f'set-couples{i}_{j}'

                        )
                    )
                )

            # If you travel from i to j, then i must be visited before j in the global tour ordering
            # Disconected cyclic tour elimination  (1-->2-->1)
            elif i != j:
                solver.add(
                    Implies(
                        couples[i][j],
                        greater_eq(
                            [orderings[k][i] for k in range(items + 1)],
                            [orderings[k][j] for k in range(items + 1)],
                            f'set-couples{i}_{j}'

                        )
                    )
                )

    # 6) Consistency with departure from and return to depot for each courier
    for k in range(couriers):
        solver.add(
            # A courier must depart from depot only once, no multi-route 
            at_most_one_bw(
                        [And(couples[-1][i], asg[k][i]) for i in range(items)],
                        f'nds_{k}'  
            )
        )
        solver.add(
            # A courier must return once, no duplicate depot visits
            at_most_one_bw(
                        [And(couples[i][-1], asg[k][i]) for i in range(items)],
                        f'nde_{k}'  
            )
        )

    ## Constraints on courier loads
    # 1) Initialization of courier loads to zero
    # 2) Accumulation of loads if courier is assigned to an item
    t = 1
    for k in range(couriers):
        solver.add(Not(Or(courier_loads[k][0])))  # All values are false in index 0
        for i in range(items):
            solver.add(If(
                Not(Or(asg[k][i])),
                And([courier_loads[k][i][j] == courier_loads[k][i + 1][j] for j in range(loads_bits)]),
                binary_sum(courier_loads[k][i], item_size[i], courier_loads[k][i + 1], f'sum{t}')
            ))
            t += 1

    # 3) Packing capacity constraints
    for k in range(couriers):
        solver.add(
            greater_eq(
                couriers_size[k], courier_loads[k][-1], f'bin_packing{k}'
            )
        )

    # 4) Symmetry breaking
    # By enforcing a "load_0 ≥ load_1 ≥ load_2 ...", the solutions which are the same but SAT sees them as different, are eliminated.
    if symmetry == settings.WITH_SYMMETRY:
        for k in range(couriers - 1):
            solver.add(
                greater_eq(
                        courier_loads[k][-1], courier_loads[k+1][-1], f'sym_br_{k}'
                )
            )


    ## Constraints on courier distances
    # 1) Initialization of courier distances to zero
    # 2) Accumulation of distances if courier travels
    t = 1
    for k in range(couriers):
        solver.add(Not(Or(couriers_distances[k][0])))
        x = 0
        for i in range(items + 1):
            for j in range(items + 1):
                solver.add(
                    If(
                        Or(And(couples[i][j], asg[k][j], asg[k][i])),
                        binary_sum(
                            couriers_distances[k][x],
                            distances[i][j],
                            couriers_distances[k][x + 1],
                            f'C{t}'
                        ),
                        And(
                            [couriers_distances[k][x][l] == couriers_distances[k][x + 1][l]
                                for l in range(distances_bits)]
                        )
                    )
                )
                x += 1
                t += 1

    

    ## Constraints on sum structures
    # 1) Initialization of sum structures to zero
    solver.add(Not(Or(sum_asg[0])))
    solver.add(Not(Or(sum_first_row[0])))
    solver.add(Not(Or(sum_first_col[0])))

    # 2) Accumulation
    for k in range(couriers):
        solver.add(binary_increment(sum_asg[k], asg[k][-1], sum_asg[k + 1], f'courier_sum{k}'))

    for i in range(items):
        solver.add(
            binary_increment(sum_first_row[i], couples[-1][i], sum_first_row[i + 1], f'coup_row_sum{i}'))
        
    for i in range(items):
        solver.add(
            binary_increment(sum_first_col[i], couples[i][-1], sum_first_col[i + 1], f'coup_col_sum{i}'))
        
    # 3) Matching among sum structures
    for i in range(bits_sum):
        solver.add(And(sum_first_col[-1][i] == sum_asg[-1][i], sum_first_row[-1][i] == sum_asg[-1][i]))

    
    return  solver, ( 
                        asg,
                        couples,
                        [courier_loads[k][-1] for k in range(couriers)],
                        [couriers_distances[k][-1] for k in range(couriers)]
                    )