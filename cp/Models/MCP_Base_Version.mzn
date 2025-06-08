include "globals.mzn";


% *********** Input Data and Decision Variable Definitions ************

int: m;                            % Number of couriers
int: n;                            % Number of items
int: depot = n+1;                        


set of int: Items = 1..n;          
set of int: Couriers = 1..m;
set of int: Points = 1..n+1;       

array[Couriers] of int: l;             % Load capacity of each courier
array[Items] of int: s;                % Size of each item

array[Points, Points] of int: D;                   % Distance matrix
array[Couriers] of var 0..sum(s): load;            % Compute the load for each courier

int: max_path = n + 2;                   % The longest path that one courier can have
set of int: Positions = 1..max_path;            
array[Couriers, Positions] of var 0..n+1: path;
array[Couriers] of var 2..max_path: path_length;
array[Couriers] of var int: dist;
array[Couriers] of var 0..sum(s): courier_load;
var int: max_dist;


% **************** Constraints ******************

% 1. Start and end path with depot and not exceed the maximum path length
constraint forall(c in Couriers)(
    path[c,1] = depot /\ path[c, path_length[c]] = depot /\ path_length[c] <= max_path
);

% 2. Set unused positions to 0
constraint forall(c in Couriers, p in path_length[c]+1..max_path)(
    path[c,p] = 0
);

% 3. Ensure that each item assigned to exactly once
constraint forall(i in Items)(
    count([path[c,p] | c in Couriers, p in 2..max_path-1], i) = 1
); 

% 4. Load calculation for each courier and check their limits
constraint forall(c in Couriers)(
    courier_load[c] = sum(p in 2..path_length[c]-1)(
        if path[c,p] > 0 then s[path[c,p]] else 0 endif
    )
);

constraint forall(c in Couriers)(courier_load[c] <= l[c]); 

% 5. Calculate total distance for each courier and optimize it
constraint forall(c in Couriers)(
    dist[c] = sum(p in 1..max_path-1)(
        if p < path_length[c] then D[path[c,p], path[c,p+1]] else 0 endif
    )      
);

constraint max_dist = max(c in Couriers)(dist[c]);

  
solve :: int_search([path[c,p] | c in Couriers, p in Positions], first_fail, indomain_min) 
minimize max_dist;

%**************** Output ******************

output [
    "Optimized maximum distance: ", show(fix(max_dist)), "\n",
    "\nmax path length: ", show(max_path), "\n",
    "\npath length of each couriers: ", show(fix(path_length)), "\n",
    "\ncourier pathes and total distances:\n",
    concat([
        let { int: rl = fix(path_length[c]) } in
        concat([
            "courier ", show(c), 
            ":\n    path: ",
            concat([
                show(fix(path[c,p])) ++ " "
                | p in 2..rl-1
            ]),
            "\n    total distance: ", show(fix(dist[c])), "\n"
        ])
        | c in Couriers
    ])
];






