# Architecture

The application uses four primary boundaries:

1. `gui` renders state and gathers user input.
2. `models` defines typed, serializable domain data.
3. `realityscan` owns official CLI keys, command construction, process execution, and report parsing.
4. `services` orchestrates both a single experiment and the benchmark queue without depending on Qt.
5. `analysis` converts results into one serializable `BenchmarkAnalysisResult`; it owns leaders,
   Pareto frontiers, sweep sensitivity, observations, and scientific warnings.
6. `reports` renders already-structured analysis into CSV, JSON, PNG, offline HTML, and ZIP outputs.

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
                                  `-> Analysis Layer -> CSV + JSON + charts + HTML + ZIP
```

Every non-dry process attempt leaves config, command, stdout, stderr, runtime, and result artifacts.
The GUI never imports or calls `subprocess`.

`BenchmarkRunner` does not construct RealityScan commands, invoke subprocesses, or parse reports.
Its responsibilities are queue order, progress, cooperative cancellation between experiments,
failure isolation, project status, result aggregation, and report generation.

The Phase 5 result boundary is:

```text
RealityScan
    -> ExperimentResult
    -> BenchmarkProject results
    -> analyze_benchmark()
    -> BenchmarkAnalysisResult / analysis.json
    -> GUI filters + charts + HTML report + reproducibility ZIP
```

The HTML renderer formats the supplied structured analysis. It does not select leaders, calculate
Pareto membership, or infer sweep effects. Public artifacts pass through `PathDisplaySanitizer`;
the private run-root `benchmark.json` remains available for local resume/debug workflows.
