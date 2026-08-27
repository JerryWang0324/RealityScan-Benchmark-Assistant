# Architecture

The application uses four primary boundaries:

1. `gui` renders state and gathers user input.
2. `models` defines typed, serializable domain data.
3. `realityscan` owns official CLI keys, command construction, process execution, and report parsing.
4. `services` orchestrates one experiment without depending on Qt; a future benchmark runner can
   call that same service repeatedly.

The GUI must never call `subprocess` directly. `RealityScanControllerProtocol` is the mockable seam
used by `SingleExperimentRunner`, future benchmark orchestration, and unit tests.

The phase-two execution boundary is:

```text
GUI -> QThread worker -> SingleExperimentRunner
                         |-> dataset validation
                         |-> command builder
                         |-> RealityScanController -> subprocess argv list
                         `-> ReportParser -> ExperimentResult
```

Every non-dry process attempt leaves config, command, stdout, stderr, runtime, and result artifacts.
The GUI never imports or calls `subprocess`.
