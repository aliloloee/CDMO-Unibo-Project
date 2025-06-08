from sat import settings

from z3.z3 import Solver, sat, unsat, Bool, Z3Exception

from sat.utils import (
    set_upper_bound, to_binary, set_lower_bound, greater_eq, max_of_bin_int,
    convert_from_binary_to_int, sorting_correspondence, saving_file
    )
from sat.binarization import binarizer

from sat.constraints import set_constraints

from setup.config import glob

import time as t


class SATSolver:
    def __init__(self, data, output_dir, timeout):
        self.data = data
        self.output_dir = output_dir
        self.timeout = timeout
        self.solver = None
        self.symmetry = None
        self.window = glob.obtain('app')

    def set_solver(self):
        self.solver = Solver()
        self.solver.set('timeout', self.timeout * 1000)

    def initiate_searching(self, instance, search_opt):
        if search_opt == settings.LINEAR_SEARCH:
            return self.linear_search(instance)

        elif search_opt == settings.BINARY_SEARCH:
            return self.binary_search(instance)

        raise ValueError(f"Unknown search option: {search_opt}")

    def solve(self):

        path_to_save = self.output_dir + "/sat/"
        for key, instance in self.data.items():
            self.window.print_output(f"###### Instance: {key} ######")
            solutions_dict  = {}
            output_filename = key.split('.')[0][-2:] + '.json'

            for search_opt in settings.SEARCH_OPTIONS:
                for symm_opt in settings.SYMMETRY_OPTIONS:
                    self.window.print_output(f"### Search: {search_opt}, Symmetry: {symm_opt} ###")
                    solution_key_dict = f"z3_{symm_opt}_{search_opt}"
                    self.symmetry = symm_opt
                    self.set_solver()

                    try:
                        solution = self.initiate_searching(instance, search_opt)
                        print(solution)
                        solutions_dict[solution_key_dict] = solution
                    
                    except TimeoutError as e:
                        print("TimeoutError:", e)
                        solutions_dict[solution_key_dict] = {
                                    'time': self.timeout,
                                    'optimal': False,
                                    'obj': "n/a",
                                    'sol': []
                                }

                    except Z3Exception as e:
                        print("Z3 Exception:", e)
                        solutions_dict[solution_key_dict] = {
                                    'time': self.timeout,
                                    'optimal': False,
                                    'obj': "n/a",
                                    'sol': []
                                }
                    
                    except Exception as e:
                        print("Exception:", e)
                        solutions_dict[solution_key_dict] = {'satisfiable':False}

            saving_file(solutions_dict, path_to_save, output_filename)

            
            self.window.print_output(f"###### Instance: {key} ended ######")

    def get_solution(self, model, results):
        asg, couples, couriers_load, couriers_distance = results
        couriers = len(asg)
        items = len(asg[0]) - 1
        # calculating bits
        load_couriers_bit = len(couriers_load[0])
        distances_bit = len(couriers_distance[0])

        asg_evaluated = [[model.evaluate(asg[k][i]) for i in range(items + 1)] for k in range(couriers)]

        couples_evaluated = [[model.evaluate(couples[k][i]) for i in range(items + 1)]
                            for k in range(items + 1)]

        courier_loads_evaluated = [
            [model.evaluate(couriers_load[k][j]) for j in range(load_couriers_bit)]
            for k in range(couriers)]

        couriers_distances_evaluated = [
            [model.evaluate(couriers_distance[k][j])for j in range(distances_bit)]
            for k in range(couriers)]

        return asg_evaluated, couples_evaluated, courier_loads_evaluated, couriers_distances_evaluated
    
    def format_output(self, result, opt, seconds):
        """
        :param solution: solution of the model
        :param optimal: indicates if the solution is optimal or not
        :param seconds: time taken by the model to solve the instance
        :return: a dictionary {time: optimal: obj: sol:}
        """
        asg, couples, _, distances = result
        couriers = len(asg)
        items = len(asg[0]) - 1
        seconds = int(seconds).__floor__()
        optimal = opt
        obj = int(max([convert_from_binary_to_int(distances[i]) for i in range(couriers)]))
        all_dist = []
        var = 0
        for k in range(couriers):
            courier_path = []
            if asg[k][items]:   # if courier is used (assigned to depot)
                for i in range(items + 1):
                    if couples[items][i] and asg[k][i]:  # there's a transition: depot → item i and courier k is responsible
                        var = i  # first item i courier k visits
                        break

                # tracing the tour
                found = True
                while found:
                    for j in range(items + 1):
                        if couples[var][j] and asg[k][j]:

                            # stops when reaching depot
                            if j == items:
                                courier_path.append(var+1)
                                found = False
                            else:
                                courier_path.append(var+1)
                                var = j
            all_dist.append(courier_path)

        return  {
            'time': seconds,
            'optimal': optimal,
            'obj': obj,
            'sol': all_dist
        }
    
    def print_solution(self, solution, seconds, optimal=True):
        """
        Prints the computed solution in a structured format using self.window.print_output.

        :param solution: tuple of model outputs (asg, couples, _, distances)
        :param seconds: float runtime in seconds
        """
        asg_evaluated, couples_evaluated, _, couriers_distances_evaluated = solution
        couriers = len(asg_evaluated)
        items = len(asg_evaluated[0]) - 1

        for k in range(couriers):
            self.window.print_output(f"Courier {k}")
            if asg_evaluated[k][items]:
                for i in range(items + 1):
                    if couples_evaluated[items][i] and asg_evaluated[k][i]:
                        self.window.print_output(f"  start: ORIGIN → end: Item {i}")
                        var = i
                        break  # Stop after first start point is found

                found = True
                while found:
                    for j in range(items + 1):
                        if couples_evaluated[var][j] and asg_evaluated[k][j]:
                            if j == items:
                                self.window.print_output(f"  start: Item {var} → end: ORIGIN")
                                found = False
                            else:
                                self.window.print_output(f"  start: Item {var} → end: Item {j}")
                                var = j
            else:
                self.window.print_output("  DO NOT START")

        self.window.print_output("Distances:")
        distances = [convert_from_binary_to_int(couriers_distances_evaluated[i]) for i in range(couriers)]
        self.window.print_output("  " + str(distances))
        if seconds < 1:
            self.window.print_output(f"Time: {seconds:.2f} seconds")
        else:
            self.window.print_output(f"Time: {int(seconds).__floor__()} seconds")
        self.window.print_output(f"Optimal: {'Yes' if optimal else 'No'}")

    def linear_search(self, instance):
        self.window.print_output("Starting optimization exploiting linear search")

        input_data, correspondence_dict = binarizer.binarize(instance)
        couriers = input_data[0]
        distance_bits = input_data[6]

        upper_bound = set_upper_bound(instance[4], input_data[-1], couriers)
        self.solver, results = set_constraints(input_data, self.solver, self.symmetry)
        self.window.print_output('Model built, starting optimization process search')

        model = None
        output_dict = None
        optimal = False
        satisfiable = True
        iter = 0
        start_time = t.time()

        while satisfiable:
            # The bounds
            conv_upper_bound = to_binary(upper_bound, distance_bits)
            lower_bound = to_binary(set_lower_bound(instance[4], input_data[-1])[0], distance_bits)

            # Find the maximum courier distance
            max_val = [[Bool(f"max_{j}_{i}_{iter}") for i in range(distance_bits)] 
                                                    for j in range(couriers)]
            self.solver.add(
                max_of_bin_int(
                        [results[-1][k] for k in range(couriers)], 
                        max_val, 
                        f'max_obj{iter}'
                    )
            )

            # Makee sure the maximum value is bounded
            self.solver.add(greater_eq(conv_upper_bound, max_val[-1], f"up_bound{iter}"))
            self.solver.add(greater_eq(max_val[-1], lower_bound, f"low_bound{iter}"))

            # Check the satisfiability
            status = self.solver.check()

            try_timeout = t.time() - start_time

            if status == unsat:
                if iter == 0:
                    self.window.print_output('Unsat')
                    raise ValueError("The instance is unsatisfiable")
                satisfiable = False

            elif status == sat:
                iter += 1
                model = self.solver.model()

                # update the upper bound
                max_val_binary = [model.evaluate(max_val[-1][j]) for j in range(distance_bits)]  # extract the value of z3 variable
                upper_bound = convert_from_binary_to_int(max_val_binary)
                upper_bound = upper_bound - 1

                # Save the best solution in case of timeout (optimal=False)
                evaluation = self.get_solution(model, results)  # evaluate model on each component of result
                final_evaluation = [sorting_correspondence(res, correspondence_dict)
                                    for res in evaluation]
                output_dict = self.format_output(final_evaluation, optimal, try_timeout)

            if (self.timeout - try_timeout) < 0:
                if iter == 0:
                    raise TimeoutError("Solver timed out before finding any solution.")
                # output = False
                self.print_solution(final_evaluation, round(try_timeout, 3), optimal=False)
                return output_dict
            
        if model:
            # This case happens only when the model has become unsatisfiable, but we still had time (optimal=True)
            optimal = True
            evaluation = self.get_solution(model, results)
            final_evaluation = [sorting_correspondence(res, correspondence_dict)
                                for res in evaluation]

            self.print_solution(final_evaluation, round(try_timeout, 3))
            output_dict = self.format_output(final_evaluation, optimal, try_timeout)
            return output_dict
        else:
            raise ValueError("No satisfiable model was found during the search.")

    def binary_search(self, instance):
        self.window.print_output("Starting optimization exploiting binary search")

        input_data, correspondence_dict = binarizer.binarize(instance)
        couriers = input_data[0]
        distance_bits = input_data[6]

        lower_bound = set_lower_bound(instance[4], input_data[-1])[0]
        upper_bound = set_upper_bound(instance[4], input_data[-1], couriers)

        self.solver, results = set_constraints(input_data, self.solver, self.symmetry)
        self.window.print_output('Model built, starting optimization process search')

        model = None
        output_dict = None
        optimal = False
        iter = 0
        start_time = t.time()

        while lower_bound <= upper_bound:
            mid = (lower_bound + upper_bound) // 2
            conv_upper_bound = to_binary(mid, distance_bits)
            conv_lower_bound = to_binary(lower_bound, distance_bits)

            # Find the maximum courier distance
            max_val = [[Bool(f"max_{j}_{i}_{iter}") for j in range(distance_bits)] for i in range(couriers)]
            self.solver.add(
                max_of_bin_int(
                    [results[-1][k] for k in range(couriers)],
                    max_val,
                    f'max_obj{iter}'
                )
            )

            self.solver.push()
            self.solver.add(greater_eq(conv_upper_bound, max_val[-1], f"up_bound{iter}"))
            self.solver.add(greater_eq(max_val[-1], conv_lower_bound, f"low_bound{iter}"))

            status = self.solver.check()
            try_timeout = t.time() - start_time

            if status == unsat:
                if iter == 0:
                    self.window.print_output('Unsat')
                    raise ValueError("The instance is unsatisfiable")
                lower_bound = mid + 1

            elif status == sat:
                iter += 1
                model = self.solver.model()

                # Save the best solution in case of timeout
                evaluation = self.get_solution(model, results)
                final_evaluation = [sorting_correspondence(res, correspondence_dict)
                                    for res in evaluation]
                output_dict = self.format_output(final_evaluation, optimal, try_timeout)
                upper_bound = mid - 1

            self.solver.pop()

            if (self.timeout - try_timeout) < 0:
                if iter == 0:
                    raise TimeoutError("Solver timed out before finding any solution.")
                self.print_solution(final_evaluation, round(try_timeout, 3), optimal=False)
                return output_dict

        if model:
            optimal = True
            evaluation = self.get_solution(model, results)
            final_evaluation = [sorting_correspondence(res, correspondence_dict)
                                for res in evaluation]
            self.print_solution(final_evaluation, round(try_timeout, 3))
            output_dict = self.format_output(final_evaluation, optimal, try_timeout)
            return output_dict
        else:
            raise ValueError("No satisfiable model was found during the search.")

