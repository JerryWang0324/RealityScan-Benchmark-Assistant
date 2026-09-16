# RealityScan Benchmark Assistant

A reproducible benchmarking and experiment-management tool for RealityScan photogrammetric
alignment workflows.

> **Project status:** Phase 5 / v0.5.0. The application connects experiment design, isolated
> RealityScan execution, structured scientific analysis, Pareto comparison, offline HTML reporting,
> and privacy-conscious reproducibility packages. It intentionally makes no “best overall” claim.

## Motivation

RealityScan exposes several alignment parameters. Repeatedly changing parameters, running alignment,
recording results, and comparing outcomes by hand is slow and makes experiment records inconsistent.
This application turns that sequence into a traceable workflow while keeping interpretation limited
to claims supported by the collected data.

## Features

- Single Alignment Test and Multi-Experiment Benchmark
- Manual, Full Factorial, and One Factor At A Time experiment design
- CSV and structured JSON export
- Parameter-versus-metric and Pareto charts
- Registration-rate/runtime Pareto analysis
- Sweep sensitivity, marginal-gain, and descriptive diminishing-return observations
- Offline HTML report
- Sanitized reproducibility ZIP package

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
          Structured Analysis
                    ↓
         Pareto Analysis + Report
                    ↓
          CSV + Charts + HTML + ZIP
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

## Parameter Sweep

Choose **Generate Parameter Sweep** to create a reproducible design without manually adding every
row. The dialog uses the same centralized RealityScan parameter schema as `ExperimentConfig` and the
CLI command builder. UI labels remain Traditional Chinese while official CLI values remain unchanged
internally.

- **Full Factorial** creates the Cartesian product of every selected value and is useful for observing
  parameter combinations.
- **One Factor At A Time (OFAT)** starts with an explicit baseline, then changes one parameter at a
  time while all others stay fixed. This makes individual descriptive effects easier to interpret.

```text
Feature quality: High
Features: 20,000 / 40,000 / 80,000
Overlap: Medium / High
Reprojection: 1.0 / 2.0

1 × 3 × 2 × 2 = 12 experiments
```

The count and relative workload update immediately. More than 20 experiments displays a warning;
more than 50 requires confirmation. These soft limits do not prohibit large sweeps. Preview the full
table before adding it. Generated rows remain editable, disableable, duplicable, reorderable, and
deletable through the regular experiment table.

Exact duplicates are detected by the four alignment parameter values. The default is to skip them;
the user may add them anyway or cancel. Every accepted sweep is saved under `sweeps/<sweep_id>.json`
in the selected output root and copied into the benchmark run. Definitions contain no dataset path,
so the same design can be reused for another dataset through the model API.

```text
ParameterSweepConfig
        ↓
ExperimentGenerator
        ↓
List[ExperimentConfig]
        ↓
BenchmarkProject
        ↓
BenchmarkRunner → SingleExperimentRunner → RealityScanController
```

`ExperimentGenerator` is a pure Cartesian/OFAT generator and never invokes RealityScan. Each
experiment has a stable `exp_<random>` ID for folders and result mapping, a readable name such as
`High | 20k | Medium | 1.0px`, and a deterministic machine name such as
`QHigh_F20000_OMedium_R1.0`. Metadata records its sweep ID, mode, generation time, baseline, varied
parameters, and `MANUAL`, `SWEEP`, or `BASELINE` role.

```json
{
  "sweep_id": "sweep_a31f2c9d10",
  "mode": "full_factorial",
  "parameters": {
    "feature_detection_quality": ["High"],
    "max_features_per_image": [20000, 40000, 80000],
    "image_overlap": ["Medium", "High"],
    "max_feature_reprojection_error": [1.0, 2.0]
  },
  "baseline": null,
  "experiment_ids": ["exp_..."],
  "varied_parameters": [
    "max_features_per_image",
    "image_overlap",
    "max_feature_reprojection_error"
  ]
}
```

## Running a Benchmark

1. Select the shared image folder and RealityScan executable.
2. Review, create, duplicate, edit, enable, and order the experiments.
3. Optionally enable **Stop queue when an experiment fails** or **Benchmark dry run**.
4. Preview all CLI commands if desired.
5. Select **Run Benchmark**.
6. Follow experiment number, experiment name, state, overall experiment-level progress, elapsed
   time, and estimated remaining time. After the first experiment finishes, the estimate uses the
   observed wall time of completed experiments and updates each second. It remains unavailable
   before a completed sample, during dry runs, and when the current experiment has already exceeded
   the observed average. The GUI remains responsive because the complete queue runs on a `QThread`
   worker.
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

The `Pareto 分析：各指標第一名` result filter groups repeated runs by parameter configuration and
uses each group's mean from successful runs. It selects one first-place group for each of the seven
table metrics: registered images, registration rate, component count, largest component camera
count, sparse points, reprojection error, and runtime. A star marks every metric that a displayed
group wins. Groups with no first-place metric are hidden, so at most seven groups appear. Ties are
resolved by registration rate, runtime, component count, and then experiment ID. Fewer components,
lower reprojection error, and shorter runtime rank first; the other four metrics rank higher values
first. Missing metric values are omitted from that metric's group mean.

The structured analysis can identify:

- higher registration rate;
- shorter runtime;
- lower reported reprojection error; and
- higher sparse point count.

It deliberately does not calculate or claim a “best overall” configuration.

Successful runs with registration rate and runtime are compared using three Pareto metrics:
higher registration rate, shorter runtime, and fewer reported components. A dominates B only when
A is no worse on all three metrics and strictly better on at least one. A one-component run and a
faster two-component run can therefore both remain on the frontier. A missing component count is
treated as unknown and cannot dominate a reported count solely through that metric. Exact metric
ties remain together on the frontier. Single-result, missing-registration/runtime, and all-failed
benchmarks do not fabricate a Pareto comparison.

For a sweep in which exactly one parameter varies, reports also include line charts for every metric
with at least two valid values: parameter versus registration rate, runtime, reported mean
reprojection error, and sparse point count. Multi-parameter sweeps remain grouped through Source and
Sweep ID in `results.csv` instead of forcing a misleading 3D visualization. OFAT summary JSON records
registration-rate difference in percentage points, runtime difference and ratio, reported
reprojection-error difference, and sparse-point difference relative to its baseline.

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

### Phase 5 analysis example

| Experiment | Registration | Runtime | Reported reprojection |
| --- | ---: | ---: | ---: |
| A | 92% | 120 s | 0.72 px |
| B | 97% | 190 s | 0.65 px |
| C | 98% | 360 s | 0.58 px |
| D | 94% | 250 s | 0.69 px |

Metric leaders are C for registration and reported reprojection error, and A for runtime. The
registration/runtime frontier is A, B, and C; D is dominated by B. These are separate descriptive
comparisons, with no overall winner inferred.

## Benchmark Output Structure

```text
benchmark_runs/
└── building_test_20260828_153000/
    ├── benchmark.json
    ├── benchmark.log
    ├── sweeps/
    │   └── sweep_a31f2c9d10.json
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
        ├── analysis.json
        ├── report.html
        ├── building_test_reproducibility.zip
        └── charts/
            ├── registration_rate.png
            ├── runtime.png
            ├── mean_reprojection_error.png
            ├── sparse_point_count.png
            ├── pareto_registration_runtime.png
            └── sweep_a31f2c9d10_max_features_per_image_registration_rate.png
```

`report.html` embeds its CSS and refers only to local chart PNGs, so it opens offline by double
clicking. The ZIP contains sanitized `benchmark.json`, summary JSON, CSV, analysis, HTML, charts,
sweep definitions, experiment configs, and environment metadata. It excludes source images,
RealityScan executables, caches, and full project output. Absolute public paths are reduced to labels
such as `<dataset>/Building01`.

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
| `experiment_id` | Stable identity independent of the display name |
| `experiment_name` | Experiment display name |
| `source` | `MANUAL`, `SWEEP`, or `BASELINE` |
| `sweep_id` | Sweep grouping identity, or `N/A` for manual rows |
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

## Interpreting Results and Scientific Limitations

- Correlation does not imply geometric accuracy; these metrics support descriptive comparison only.
- A higher registration rate does not necessarily mean a more accurate reconstruction.
- Lower reported reprojection error does not imply lower absolute 3D error.
- More sparse points do not necessarily mean a more accurate or useful model.
- Sweep observations apply only to the tested dataset, RealityScan version, hardware, and workflow.
- RealityScan internal metrics are not substitutes for independent ground truth. True accuracy
  evaluation requires control points, scale constraints, surveyed reference geometry, or other
  independent measurements.
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
They cover sweep serialization and validation, 12-case Cartesian generation, OFAT isolation,
duplicate detection, deterministic naming and unique IDs, baseline-relative metrics,
single-variable charts, Traditional Chinese live counts, model serialization, queue order,
failure isolation, stop-on-failure,
cooperative cancellation, disabled rows, CSV encoding/missing values, conditional chart creation,
comparison helpers, report parsing, command construction, and Traditional Chinese GUI text.
Phase 5 tests additionally cover Pareto domination and ties, missing metrics, sweep deltas and safe
division, diminishing-return wording, all-failed HTML output, integrity warnings, path sanitization,
ZIP allow-list contents, and a mock report-level integration flow.

## Documentation

- [Architecture](docs/architecture.md)
- [Metrics](docs/metrics.md)
- [Experimental design](docs/experimental_design.md)
- [Reproducibility](docs/reproducibility.md)
- [Scientific limitations](docs/scientific_limitations.md)

## Screenshots

The [`docs/images/`](docs/images/) directory is reserved for screenshots captured from verified GUI
runs. No fabricated screenshots are included.

The opt-in real tests under `integration_tests/` are skipped unless explicitly enabled:

- `RSBA_RUN_REALITYSCAN_INTEGRATION=1` verifies report-only export from an existing project.
- `RSBA_RUN_REALITYSCAN_BENCHMARK_INTEGRATION=1` plus
  `RSBA_INTEGRATION_IMAGE_FOLDER` runs two complete alignment experiments and checks CSV/charts.
- `RSBA_RUN_REALITYSCAN_SWEEP_INTEGRATION=1` runs a 20k/40k/80k feature sweep and verifies its
  result CSV and parameter-effect chart.

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
- Loading a saved sweep through the GUI is not yet exposed. Save/load is available through
  `SweepDefinition`, and every GUI-created definition is saved automatically.
- Multi-parameter Full Factorial results use grouped CSV data and standard per-experiment charts;
  the application intentionally avoids hard-to-read 3D surfaces.
- No overall winner or automatic “best settings” recommendation is produced because metrics may
  conflict.
