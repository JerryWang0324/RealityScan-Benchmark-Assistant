# RealityScan Benchmark Assistant

A Windows/PySide6 desktop application for reproducible, multi-experiment RealityScan alignment
benchmarks.

> **Project status:** Phase 3. The application runs an ordered queue of alignment experiments on one
> shared dataset, isolates individual failures, aggregates metrics, and writes CSV, JSON, and PNG
> reports. Parameter sweeps, automatic optimization, dense reconstruction, mesh/texture benchmarks,
> AI recommendations, cloud services, and databases remain intentionally out of scope.

## Installation

Requirements: Windows 11, Python 3.12+, and a licensed/signed-in RealityScan installation for real
runs. RealityScan is not bundled.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the Traditional Chinese GUI with `run.bat` or:

```powershell
python -m rs_benchmark.main
```

Application logs are written to `logs/app.log`.

## Benchmark Workflow

```text
One Dataset + One RealityScan Executable
                    ↓
        Experiment A / B / C
                    ↓
        Ordered RealityScan CLI Runs
                    ↓
           Collect Result Metrics
                    ↓
          Descriptive Comparison
                    ↓
        CSV + Summary JSON + Charts
```

The shared image folder and RealityScan executable are selected once. Experiment rows contain only
alignment parameters. The queue calls the Phase 2 `SingleExperimentRunner` once per enabled row;
`BenchmarkRunner` does not duplicate command construction, subprocess control, report parsing, or
single-experiment artifact handling.

## Creating Experiments

The initial table contains three editable starting presets:

| Preset | Feature quality | Max features/image | Overlap | Max reprojection error |
| --- | --- | ---: | --- | ---: |
| Default | High | 40,000 | Medium | 2.0 px |
| High Features | High | 80,000 | Medium | 2.0 px |
| Strict Geometry | High | 40,000 | High | 1.0 px |

Presets are hypotheses and convenient starting values, not claims about quality. Use **Add**, **Edit**,
**Duplicate**, **Delete**, **Move Up**, and **Move Down** to build the queue. Duplicate creates an
independent copy so one parameter can be varied. Disabled rows are saved but not executed. Identical
enabled parameter sets produce a warning and remain runnable.

## Running a Benchmark

1. Select the shared image folder and RealityScan executable.
2. Review, create, duplicate, edit, enable, and order the experiments.
3. Optionally enable **Stop queue when an experiment fails** or **Benchmark dry run**.
4. Preview all CLI commands if desired.
5. Select **Run Benchmark**.
6. Follow experiment number, experiment name, state, overall experiment-level progress, and elapsed
   time. The GUI remains responsive because the complete queue runs on a `QThread` worker.
7. Select **Cancel Benchmark** to stop after the current RealityScan process returns. Completed
   results and artifacts are retained; remaining experiments are marked `CANCELLED`.

RealityScan does not expose reliable alignment percentage through this workflow, so the application
reports honest experiment-level progress rather than inventing a fine-grained percentage.

By default, a failed experiment is recorded and the next experiment runs. If stop-on-failure is
enabled, remaining rows are marked `SKIPPED`. Final project status is `COMPLETED`, `PARTIAL_SUCCESS`,
`FAILED`, or `CANCELLED` as appropriate.

## Benchmark Dry Run

Dry run validates the shared dataset and executable, creates the benchmark root and every enabled
experiment folder, writes each `config.json`, `command.txt`, report template, and `result.json`, but
does not launch RealityScan. Results use `DRY_RUN`, and summary CSV/JSON are still generated. This is
useful for checking quoting, paths, queue order, and parameter mappings before a long run.

## Results

The GUI result table shows experiment status, registered images, registration rate, component count,
largest component camera count, sparse point count, mean reprojection error, and runtime. Missing
values are displayed as `N/A`. Actions open the output folder, copy the CSV to another location, or
open the first generated chart.

The descriptive comparison can identify:

- higher registration rate;
- shorter runtime;
- lower reported reprojection error; and
- higher sparse point count.

It deliberately does not calculate or claim a “best overall” configuration.

### Mock result

```text
Default
Registration Rate: 94.1%
Runtime: 182 s

High Features
Registration Rate: 98.0%
Runtime: 311 s

Strict
Registration Rate: 95.3%
Runtime: 228 s
```

The corresponding complete mock CSV is in [`sample/mock_results.csv`](sample/mock_results.csv).

## Benchmark Output Structure

```text
benchmark_runs/
└── building_test_20260828_153000/
    ├── benchmark.json
    ├── benchmark.log
    ├── experiments/
    │   ├── 001_default/
    │   │   ├── config.json
    │   │   ├── command.txt
    │   │   ├── alignment_report_template.html
    │   │   ├── cache_policy.json
    │   │   ├── report_export.json
    │   │   ├── result.json
    │   │   ├── runtime.json
    │   │   ├── stdout.log
    │   │   ├── stderr.log
    │   │   └── realityscan_output/
    │   ├── 002_high_features/
    │   └── 003_strict/
    └── summary/
        ├── results.csv
        ├── benchmark_summary.json
        └── charts/
            ├── registration_rate.png
            ├── runtime.png
            ├── mean_reprojection_error.png
            └── sparse_point_count.png
```

Reprojection-error charts require at least two valid values. Sparse-point and other charts are not
created when all values are unavailable. RealityScan creates its project/report/component outputs;
the application does not fabricate successful RealityScan artifacts.

RealityScan 2.2 report export can fail when its report template or destination contains non-ASCII
characters. The runner automatically sends only `exportReport` through a temporary ASCII staging
directory, then copies the completed report back to the requested Chinese/Unicode experiment
folder. Project, component, benchmark, and final report paths retain their original names.

Each non-dry experiment also receives a new, empty process-local `TEMP/TMP` directory. RealityScan
therefore cannot reuse feature cache created by an earlier queue item. The directory is removed after
that RealityScan process exits, without clearing the user's global cache or caches belonging to other
projects. `cache_policy.json` records the applied strategy and cleanup state. This makes runtime
comparisons cold-cache measurements; normal operating-system disk cache effects can still exist.

`benchmark.json` is updated during the run and can be deserialized through
`BenchmarkProject.load(path)`. It records project status, timestamps, experiment configs, partial or
complete results, shared paths, notes, options, and available metadata. Metadata includes OS, Python
version, app version, dataset image count, start time, and a deterministic dataset fingerprint based
on sorted relative filenames, sizes, and modification times. Unavailable RealityScan version data
remains `null`.

## CSV Schema

`summary/results.csv` is UTF-8 with BOM for Excel compatibility. Missing values are the literal
`N/A`; Python `None` is never serialized as an object representation.

| Field | Meaning |
| --- | --- |
| `experiment_name` | Experiment display name |
| `status` | `SUCCESS`, `FAILED`, `TIMEOUT`, `DRY_RUN`, `SKIPPED`, or `CANCELLED` |
| `feature_detection_quality` | RealityScan value (`High` or `Normal`) |
| `max_features_per_image` | Maximum detected features per input image |
| `image_overlap` | RealityScan value (`Low`, `Medium`, or `High`) |
| `max_feature_reprojection_error` | Configured maximum feature reprojection error |
| `total_images` | Supported files found during dataset preflight |
| `registered_images` | Sum of registered cameras reported across components |
| `registration_rate` | `registered_images / total_images * 100` |
| `component_count` | Reported component count |
| `largest_component_camera_count` | Camera count of the largest component |
| `sparse_point_count` | Registered point count of the largest component |
| `mean_reprojection_error` | Reported mean error of the largest component |
| `runtime_seconds` | Wall-clock RealityScan process duration |
| `runtime_per_registered_image` | Runtime divided by registered images |

## Metrics

The custom RealityScan report template supplies registered camera, component, largest-component,
sparse-point, and mean reprojection-error fields. Registration rate and runtime per registered image
are derived only when their denominators are greater than zero. A missing report variable, failed
process, skipped row, or dry run can leave metrics as `N/A`.

## Scientific Limitations

- These metrics are indirect quality indicators and support descriptive comparison only.
- More sparse points do not necessarily mean a more accurate or useful model.
- Lower reported reprojection error alone does not guarantee better geometric accuracy.
- Registration rate does not measure absolute position or scale accuracy.
- True accuracy evaluation requires ground truth, control points, scale constraints, or independent
  survey measurements.
- Sparse-point and reprojection-error values describe the largest component rather than aggregating
  unrelated components.

## RealityScan CLI Integration

Official command keys remain centralized in `realityscan/commands.py`. The Phase 2 runner uses an
argv list with `shell=False`, preserving paths with spaces. It creates a new scene, imports the shared
folder, applies the row parameters, aligns, saves a project, exports components, and exports the
custom report. RealityScan version is read from Windows executable metadata because no documented
version CLI command is assumed.

Official references: [all CLI commands](https://rshelp.capturingreality.com/en-US/appbasics/allcommands.htm),
[keys and values](https://rshelp.capturingreality.com/en-US/tutorials/setkeyvaluetable.htm),
[alignment examples](https://rshelp.capturingreality.com/en-US/tutorials/commandline_1.htm), and
[report variables](https://rshelp.capturingreality.com/en-US/appbasics/reports_fav_components.htm).

## Tests

```powershell
pytest
ruff check .
```

Unit tests use fake controllers and fake single-experiment runners; they never require RealityScan.
They cover model serialization, queue order, three successes, failure isolation, stop-on-failure,
cooperative cancellation, disabled rows, CSV encoding/missing values, conditional chart creation,
comparison helpers, report parsing, command construction, and Traditional Chinese GUI text.

The opt-in real tests under `integration_tests/` are skipped unless explicitly enabled:

- `RSBA_RUN_REALITYSCAN_INTEGRATION=1` verifies report-only export from an existing project.
- `RSBA_RUN_REALITYSCAN_BENCHMARK_INTEGRATION=1` plus
  `RSBA_INTEGRATION_IMAGE_FOLDER` runs two complete alignment experiments and checks CSV/charts.

Both require `RSBA_INTEGRATION_EXECUTABLE` and a dedicated
`RSBA_INTEGRATION_OUTPUT_DIRECTORY`. Ordinary `pytest` never launches RealityScan.

## Known Limitations

- Image discovery is non-recursive and uses one shared folder.
- Cancel is cooperative between experiments. The current `subprocess.run` call cannot be interrupted
  through this UI; cancellation takes effect after it exits or times out.
- A RealityScan login or licensing dialog may still require interaction in headless mode.
- Report variables were previously verified against RealityScan 2.2; other versions should run the
  opt-in integration test before long benchmarks.
- Reopening a project is supported by the model/API; the current GUI does not yet include an Open
  Project command.
- Parameter Cartesian products and automatic parameter recommendations are not implemented.
