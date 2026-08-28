# Architecture

The application uses four primary boundaries:

1. `gui` renders state and gathers user input.
2. `models` defines typed, serializable domain data.
3. `realityscan` owns official CLI keys, command construction, process execution, and report parsing.
4. `services` orchestrates both a single experiment and the benchmark queue without depending on Qt.
5. `reports` aggregates results into CSV, summary JSON, descriptive comparisons, and PNG charts.

The GUI must never call `subprocess` directly. `RealityScanControllerProtocol` is the mockable seam
used by `SingleExperimentRunner`, future benchmark orchestration, and unit tests.

The phase-three execution boundary is:

```text
GUI -> QThread BenchmarkWorker -> BenchmarkRunner
                                  |-> validate shared dataset/executable
                                  |-> for each enabled ExperimentConfig
                                  |      `-> SingleExperimentRunner (unchanged Phase 2 pipeline)
                                  |             |-> command builder
                                  |             |-> RealityScanController -> subprocess argv list
                                  |             `-> ReportParser -> ExperimentResult
                                  `-> CSV + summary JSON + charts
```

Every non-dry process attempt leaves config, command, stdout, stderr, runtime, and result artifacts.
The GUI never imports or calls `subprocess`.

`BenchmarkRunner` does not construct RealityScan commands, invoke subprocesses, or parse reports.
Its responsibilities are queue order, progress, cooperative cancellation between experiments,
failure isolation, project status, result aggregation, and report generation.
