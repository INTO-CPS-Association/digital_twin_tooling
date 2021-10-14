# A tool for managing digital twin simulations

This project aims to provide a structured approach to working with digital twins and support the analysis that one might want to carry out in this context.

The project provides a pipeline like approach for structuring digital twin simulations. It structures a simulation as a number of participating tasks:
* data providers: Providing data to the simulation by connecting to external sources and translating the data into a simulation compatible format.
* simulators: Providing the ability to simulate models (such as FMI models using maestro)

The tool is provided as a module and can be used like:

```bash
python -m "digital_twin_tooling" project -project <path to project file>.yml \
                                 -show -run 1 -fmus <path to folder contaning the fmus>
```

Show status of launchers in job folder
```bash
python -m "digital_twin_tooling" launcher  -work jobs/e1b27ef9-2699-474d-bba5-c23fdcf31821/ -s
```

