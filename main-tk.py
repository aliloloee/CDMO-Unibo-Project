import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import argparse

from sat.utils import load_data
from sat.solver import SATSolver
from cp.solver import CPSolver
from lp.solvergui import MIPSolver
from lp.helper import parse_dat_file
import os

from setup.config import glob

class MCPApp:
    def __init__(self, root):
        root.title("Multiple Couriers Planning - GUI")
        root.geometry("900x500")

        root.grid_columnconfigure(0, weight=1, uniform="column")
        root.grid_columnconfigure(1, weight=3, uniform="column")

        left_frame = ttk.Frame(root, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew")

        right_frame = ttk.Frame(root, padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Variables
        self.approach_var = tk.StringVar(value="SAT")
        self.solver_var = tk.StringVar(value="cbc")
        self.symbreak_var = tk.BooleanVar(value=False)
        self.num_instance_var = tk.IntVar(value=0)
        self.input_dir_var = tk.StringVar(value="./input")
        self.output_dir_var = tk.StringVar(value="./output")
        self.timeout_var = tk.IntVar(value=300)

        # Solver selection
        ttk.Label(left_frame, text="Approach:").pack(anchor='w')
        self.approach_combo = ttk.Combobox(
            left_frame,
            textvariable=self.approach_var,
            values=["SAT", "CP", "LP"],
            state="readonly"
        )
        self.approach_combo.pack(fill='x')
        self.approach_combo.bind("<<ComboboxSelected>>", self.update_lp_options)

        ttk.Label(left_frame, text="Instance Number:").pack(anchor='w', pady=(10, 0))
        ttk.Entry(left_frame, textvariable=self.num_instance_var).pack(fill='x')

        ttk.Label(left_frame, text="Input Directory:").pack(anchor='w', pady=(10, 0))
        ttk.Entry(left_frame, textvariable=self.input_dir_var).pack(fill='x')

        ttk.Label(left_frame, text="Output Directory:").pack(anchor='w', pady=(10, 0))
        ttk.Entry(left_frame, textvariable=self.output_dir_var).pack(fill='x')

        ttk.Label(left_frame, text="Timeout (sec):").pack(anchor='w', pady=(10, 0))
        ttk.Entry(left_frame, textvariable=self.timeout_var).pack(fill='x')

        # LP-specific options
        self.lp_solver_label = ttk.Label(left_frame, text="LP Solver:")
        self.lp_solver_combo = ttk.Combobox(left_frame, textvariable=self.solver_var, values=["cbc", "glpk"], state="readonly")
        self.symbreak_check = ttk.Checkbutton(left_frame, text="Enable Symmetry Breaking", variable=self.symbreak_var)

        # Run button
        ttk.Button(left_frame, text="Run Solver", command=self.demo_output).pack(pady=20)

        # Output area
        ttk.Label(right_frame, text="Execution Output:").pack(anchor='w')
        self.output_text = ScrolledText(right_frame, wrap=tk.WORD, height=25)
        self.output_text.pack(fill='both', expand=True)

        self.update_lp_options()

    def update_lp_options(self, event=None):
        if self.approach_var.get().lower() == "lp":
            self.lp_solver_label.pack(anchor='w', pady=(10, 0))
            self.lp_solver_combo.pack(fill='x')
            self.lp_solver_combo.current(0)
            self.symbreak_check.pack(anchor='w', pady=(10, 0))
        else:
            self.lp_solver_label.pack_forget()
            self.lp_solver_combo.pack_forget()
            self.symbreak_check.pack_forget()

    def print_output(self, message=None):
        if message:
            self.output_text.insert(tk.END, message + "\n")
            self.output_text.see(tk.END)

    def demo_output(self):
        self.output_text.delete(1.0, tk.END)
        self.print_output("Loading the input instance...")

        approach = self.approach_var.get().lower()

        self.print_output(f"Approach selected: {approach.upper()}")

        if approach == "sat":
            data = load_data(self.input_dir_var.get(), self.num_instance_var.get())
            solver = SATSolver(
                data=data,
                output_dir=self.output_dir_var.get(),
                timeout=int(self.timeout_var.get()),
            )
            self.print_output("Running SAT solver...")
            solver.solve()

        elif approach == "cp":
            solver = CPSolver(
                data=self.num_instance_var.get(),
                timeout=int(self.timeout_var.get())
            )
            self.print_output("Running CP solver...")
            solver.solve()

        elif approach == "lp":
            solver_name = self.solver_var.get().lower()
            use_sb = self.symbreak_var.get()
            self.print_output(f"Running LP solver with {solver_name.upper()} | Symmetry Breaking: {use_sb}")

            try:
                filename = f"inst{self.num_instance_var.get():02d}.dat"
                path = os.path.join(self.input_dir_var.get(), filename)
                m, n, capacities, sizes, distance_matrix = parse_dat_file(path)
            except Exception as e:
                self.print_output(f"Error loading instance: {e}")
                return
            
            try:
                result = MIPSolver(
                m=m,
                n=n,
                capacities=capacities,
                sizes=sizes,
                distance_matrix=distance_matrix,
                timeout=int(self.timeout_var.get()),
                solver_name=solver_name,
                use_symmetry_breaking=use_sb
                )
                self.print_output(f"Objective: {result['obj']}")
                self.print_output(f"Optimal: {result['optimal']}")
                self.print_output(f"Time: {result['time']} sec")
                self.print_output(f"Solution: {result['sol']}")

            except Exception as e:
                self.print_output(f"LP Solver error: {e}")
        else:
            self.print_output("Please select a valid solver.")

        self.print_output("Done.")

if __name__ == '__main__':
    root = tk.Tk()
    app = MCPApp(root)
    glob.add('app', app)
    root.mainloop()