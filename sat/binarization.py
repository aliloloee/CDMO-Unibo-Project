import math
import numpy as np


class BinaryModel:

    def to_binary(self, num, length=None):
        """
        Used to represent numeric constraints like load or distance purely in Boolean terms.

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


    def sorting_couriers(self, value):
        """
        sorting_couriers(value)
        Purpose: Rearranges couriers by their capacity in descending order.

        Why? Helps break symmetries (i.e., avoid multiple equivalent solutions with permuted courier indices).

        Returns: A mapping from sorted index to original index, used to interpret final solutions.
        """
        courier_size = value[2]
        size_pos = {}
        # Initialization
        for i in range(len(courier_size)):
            size_pos[courier_size[i]] = []

        for i in range(len(courier_size)):
            size_pos[courier_size[i]].append(i)

        courier_size_copy = courier_size.copy()
        courier_size_copy.sort(reverse=True)
        corresponding_dict = {}
        for i in range(len(courier_size)):
            corresponding_dict[i] = size_pos[courier_size_copy[i]][0]
            size_pos[courier_size_copy[i]].pop(0)

        return corresponding_dict


    def binarize(self, instance):
        """
        Inputs an instance (already parsed).

        Computes:
            Binary-encoded courier capacities
            Binary-encoded item sizes
            Binary-encoded distance matrix

        Also computes the bit lengths needed for load and distance constraints:
            load_couriers_bit = max(log2(total load), log2(max capacity))
            distances_bit = log2(max distance)

        Determines whether sub-tour elimination is required:
            sub_tour = True if min(courier_size) >= max(item_size) else False
        """
        corr_dict = self.sorting_couriers(instance)
        couriers, items, courier_size, item_size, distances = instance

        # sorting in descending order the couriers to apply symmetry
        courier_size = np.sort(courier_size)[::-1]

        load_couriers_bit = max(
            math.ceil(math.log2(sum(item_size))),
            math.ceil(math.log2(max(courier_size)))
        )
        distances_bit = math.ceil(
            math.log2(sum(
                [max(distances[i])
                for i in range(len(distances))]
            ))
        )

        # binary representation of courier_size
        courier_size_conv = [self.to_binary(courier_size[i], load_couriers_bit) for i in range(couriers)]

        # binary representation of item_size
        item_size_conv = [self.to_binary(item_size[i], load_couriers_bit) for i in range(items)]

        # binary representation of distances_conv
        distances_conv = [[self.to_binary(distances[i][j], distances_bit) 
                                                    for j in range(items+1)]
                                                    for i in range(items+1)]
        
        sub_tour = (True if min(courier_size) >= max(item_size) else False)
        prepared_instance = (
            couriers,
            items,
            courier_size_conv,
            item_size_conv,
            distances_conv,
            load_couriers_bit,
            distances_bit,
            sub_tour
        )

        return prepared_instance, corr_dict


binarizer = BinaryModel()

