# Multiple Couriers Planning Problem

This repository contains the project developed for the Combinatorial Decision Making and Optimization exam at Alma Mater Studiorum, Università di Bologna. The focus of the project is the Multiple Couriers Planning Problem (MCPP), modeled and solved using three different optimization approaches. The work has been carried out collaboratively by:

<li> Hamidreza Bahmanyar
<li> Ali Loloee
<li> Fatemeh Izadinejad

## Implemented Approaches

<li> Constraint Programming — using the MiniZinc modeling language via the Python MiniZinc API
<li> Satisfiability (SAT) — using Z3, a theorem prover from Microsoft Research, through its Python library
<li> Mixed-Integer Linear Programming (MILP) — using PuLP, a Python-based modeling language for linear optimization, solved via the GLPK solver

## How to set up a Tkinter GUI App in Docker on Windows (with VcXsrv)

### 1. Install Prerequisites

#### Docker Desktop

Download and install from: https://www.docker.com/products/docker-desktop  
Ensure it's running in **Linux containers** mode (default).

#### VcXsrv (X Server for Windows)

Download from: https://sourceforge.net/projects/vcxsrv/

After installing:

- Run **XLaunch**
- Select:
  - Multiple windows
  - Start no client
  - Enable **Disable access control**
- Finish and leave VcXsrv running

### 2. Build the Docker Image

In a terminal in the project folder:

```bash
docker build -t tkinter-docker-app .
```

### 3. Run the Container with GUI Support

Set the DISPLAY variable (in Command Prompt):

```bash
set DISPLAY=host.docker.internal:0.0
```

Then run the container:

```bash
docker run -e DISPLAY=%DISPLAY% tkinter-docker-app
```

If everything is correct, a Tkinter window should appear on your Windows desktop, rendered via VcXsrv.

## How to use the Tkinter desktop application

The project includes a user-friendly Tkinter-based desktop interface that allows users to solve the MCP problem using different optimization methods.

#### Features

- Choose among three available methods for solving the MCP problem:

  - SAT
  - CP
  - LP

- When selecting the LP solver(visualization of ressult), you can:

  - Choose the backend solver (cbc or glpk)
  - Enable or disable symmetry breaking
  - **To run multiple instances and get the output json file, run via cd lp && python runner.py**

- Input Folder Customization:
  You can select the directory containing input instances.

- Output Directory:
  You may configure where solution outputs should be saved.

- Timeout Setting:
  The default solver timeout is set to 300 seconds, but this can be customized through the interface.

- Detailed Output Display:
  In addition to saving the results, the application provides a clear and detailed explanation of the computed solutions directly in the GUI panel.
