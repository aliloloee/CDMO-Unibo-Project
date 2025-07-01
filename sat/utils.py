import os
import json
import numpy as np

from z3.z3 import Implies, And, Or, Not, Bool, Xor


def set_upper_bound(distances, sub_tour, couriers):
    items = len(distances) - 1  # # items = n, last row is the origin
    if sub_tour:
        # A heuristic upper bound based on the most challenging deliveries
        dist_np = np.array(distances)
        dist_sorted = dist_np[np.max(dist_np, axis=0).argsort()]
        max_long_path = sum([max(dist_sorted[i]) for i in range(couriers-1, items+1)])
        return int(max_long_path)

    else:
        return sum([max(distances[i]) for i in range(items+1)])  


def read_instance(path):
    """
    The function takes in input a txt files and return a tuple of the problem's instance
    """
    # Read the instance file from the general txt type
    f = open(path, 'r')
    lines = f.readlines()
    distances = []
    for i, line in enumerate(lines):
        if i == 0:
            n_couriers = int(line)
        elif i == 1:
            n_items = int(line)
        elif i == 2:
            couriers_size = [int(e) for e in line.split(' ') if e != '\n' and e != '']
        elif i == 3:
            objects_size = [int(e) for e in line.split(' ') if e != '\n' and e != '']
        else:
            distances.append([int(e) for e in line.split(' ') if e != '\n' and e != ''])
    f.close()
    return n_couriers, n_items, couriers_size, objects_size, distances


def load_data(path, instance):
    """
    Reads all instances from a given path or a specific instance if specified.
    Returns a dictionary containing, where keys are filenames and values are tuples of the instance data.
    """
    data = {}
    files = sorted(os.listdir(path))

    # Read all instances
    if instance == 0:
        for file in files:
            data[file] = (read_instance(path + "/" + file))

    # Read file until the instance specified
    else:
        i = 0
        for file in files:
            if i == instance:
                break
            data[file] = (read_instance(path + "/" + file))
            i += 1
    return data

def load_single_data(path, instance):
    data = {}
    files = sorted(os.listdir(path))

    # Read all instances
    if instance == 0:
        for file in files:
            data[file] = read_instance(os.path.join(path, file))

    # Read only the specified instance
    else:
        if instance - 1 < len(files):
            file = files[instance - 1]
            data[file] = read_instance(os.path.join(path, file))
        else:
            raise IndexError(f"Instance index {instance} is out of range. There are only {len(files)} files.")
    
    return data


################################################## Need to be studied from  here

def to_binary(num, length=None):
    """
    If length is less than possible number of boolean number, the minimum number is returned
    ex// to_binary(10, 3) --> [True, False, True, False]

    convert a number to its binary representation
    :param num: number to be converted
    :param length: boolean varaibles to pad zeros
    :return:
    """
    num_bin = bin(num).split("b")[-1]

    if length:
        num_bin = "0" * (length - len(num_bin)) + num_bin
    return [True if bit == '1' else False for bit in num_bin]


def set_lower_bound(distances, all_travel):
    """
    :param distances: matrix of distances
    :result lb: the lower bound for the objective funciton
    :result dist_lb: the lower bound for the array of courier distances
    """
    last_row = distances[-1]
    last_column = [distances[i][-1] for i in range(len(distances[0]))]
    value1 = last_column[np.argmax(last_row)] + max(last_row)
    value2 = last_row[np.argmax(last_column)] + max(last_column)
    lb = max(value1, value2)

    if not all_travel:
        dist_lb = 0
    else:
        value1 = last_column[np.argmin(last_row)] + min(last_row)
        value2 = last_row[np.argmin(last_column)] + min(last_column)
        dist_lb = min(value1, value2) 

    return (lb, dist_lb)


def greater_eq(vec1, vec2, name):
    """
    :param vec1: first vector of z3 varaibles
    :param vec2:  second vector of z3 varaiables
    :param name: names associated with the operator and vec1, vec2
    :return: constraints which are true if vec1 is greater or equal to vec2
    """
    constraints = []
    gt = [Bool(f"gt_{name}{i}") for i in range(len(vec1))]

    constraints.append(
        And(
            [
                Implies(Not(vec1[0]), Not(vec2[0])),
                Implies(And(vec1[0], Not(vec2[0])), gt[0]),
                Implies(Not(Xor(vec1[0], vec2[0])), Not(gt[0]))]
        )
    )

    for i in range(1, len(vec1)):
        constraints.append(
            And(
                Or(gt[i - 1],
                   And(
                       [
                           Implies(Not(vec1[i]), Not(vec2[i])),
                           Implies(And(vec1[i], Not(vec2[i])), gt[i]),
                           Implies(Not(Xor(vec1[i], vec2[i])), Not(gt[i]))]
                   )
                   ),
                Implies(gt[i - 1], gt[i])
            )
        )
    return And(constraints)


def max_of_bin_int(values, max_values, name):
    """
    Example:
    values = [[True, False], [False, True], [True, True]]
    max_values is initialized as a list of three empty bit-vectors: max_values = [_, _, _].
    The function ensures that the last bit-vector in max_values is the maximum of all input bit-vectors in values. 


    :param values: list of bitvectors representing integers
    :param max_values: will be bounded to a list where the last element is the max
    :param name: name associated with the operator and the input data
    :return: constraints which are true if the last element of the list is the maximum
    """

    constraints = []
    len_bits = len(values[0])
    constraints.append(
        And([max_values[0][j] == values[0][j] for j in range(len_bits)]),
    )

    for i in range(0, len(values) - 1):
        constraints.append(
            Or(
                # CASE A: mᵢ ≥ vᵢ₊₁ ⇒ keep mᵢ as max
                And(greater_eq(max_values[i], values[i + 1], f"{name}st{i}"),
                    And([max_values[i + 1][j] == max_values[i][j] for j in range(len_bits)])),

                # CASE B: vᵢ₊₁ > mᵢ ⇒ overwrite with vᵢ₊₁
                And(greater_eq(values[i + 1], max_values[i], f"{name}opp{i}"),
                    And([max_values[i + 1][j] == values[i + 1][j] for j in range(len_bits)]))
            )
        )
    return And(constraints)


def convert_from_binary_to_int(val):
    """
    ex// convert_from_binary_to_int([True, False, True, False]) --> 10
    :param val: array of binary variabled to be converted to an integer
    :return: integer value
    """
    number = 0
    for i in range(len(val)):
        if val[i]:
            number += 2 ** (len(val) - 1 - i)
    return number


def sorting_correspondence(res, corresponding_dict):
    '''
    :param res: list of variables returned by a certain model
    :param corresponding_dict: dictionary where the keys are the couriers 
                               couriers in order and the values are the 
                               corresponding couriers before the sorting

    :result: the set of result reordered according to the original instance
    '''
    # We reorder only the result whose first dimension is M 
    if not isinstance(res, list):
        return res
    
    if len(res) != len(corresponding_dict):
        return res

    final_res = [[] for _ in range(len(res))]
    # Assigned the corrispondences with the dictionary
    for i in range(len(res)):
        courier = corresponding_dict[i]
        final_res[courier] = res[i]
    return final_res


def saving_file(json_dict, path, filename):
    if not os.path.exists(path):
        os.makedirs(path)
        
    with open(path + filename, 'w') as file:
        json.dump(json_dict, file)