# Architecture

The application uses four primary boundaries:

1. `gui` renders state and gathers user input.
2. `models` defines typed, serializable domain data.
3. `realityscan` owns official CLI keys, command construction, process execution, and report parsing.
4. `services` will orchestrate benchmark runs without depending on Qt.

The GUI must never call `subprocess` directly. `RealityScanControllerProtocol` is the mockable seam
used by future benchmark orchestration and unit tests.
