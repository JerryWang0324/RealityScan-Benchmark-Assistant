# RealityScan Benchmark Assistant

A Windows/PySide6 desktop application for reproducible RealityScan alignment experiments.

> **Project status:** phase two. A complete, independently callable single-alignment workflow is
> implemented. Multi-experiment queues, parameter sweeps, comparisons, charts, dense
> reconstruction, mesh, texture, AI, databases, and cloud integration are intentionally out of
> scope.

## Installation

Requirements: Windows 11, Python 3.12+, and a licensed/signed-in RealityScan installation for real
runs. RealityScan is not bundled.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run the GUI

Double-click `run.bat`, or start it manually:

```powershell
python -m rs_benchmark.main
```

Application logs are written to `logs/app.log`.

## Single Alignment Test

1. Select `RealityScan.exe` (legacy `RealityCapture.exe` is also accepted).
2. Select a folder containing `.jpg`, `.jpeg`, `.png`, `.tif`, or `.tiff` images.
3. Choose feature detection quality, maximum features per image, image overlap, and maximum
   reprojection error.
4. Optionally use **Preview CLI Command** to inspect the exact Windows command line.
5. Select **Run Single Alignment Test**.
6. Review the status, registration metrics, error message, and experiment output location.

Execution happens on a Qt worker thread, so the window remains responsive. Basic dataset and
executable errors are detected before RealityScan is launched.

The same operation is available as a Qt-independent service:

```python
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner

result = SingleExperimentRunner().run_experiment(config)
```

## Dry Run

Enable **Dry Run** before selecting **Run Single Alignment Test**. The application validates the
dataset and executable, creates an isolated experiment folder, and writes `config.json`,
`command.txt`, the custom report template, and `result.json`. It does not start RealityScan. A dry
run result uses status `DRY_RUN`.

## RealityScan CLI Integration

The phase-two command uses an argv list with `shell=False`; paths containing spaces remain single
arguments. Official commands and raw keys are centralized in `realityscan/commands.py`.

Command chain:

```text
-headless
-silent <crash-report-folder>
-stdConsole
-set appQuitOnError=true
-newScene
-addFolder <image-folder>
-set sfmFeatureDetectionQuality=<High|Normal>
-set sfmMaxFeaturesPerImage=<integer>
-set sfmImagesOverlap=<Low|Medium|High>
-set sfmMaxFeatureReprojectionError=<float>
-align
-save <project.rsproj>
-setMinComponentSize 1
-exportLatestComponents <components-folder>
-exportReport <alignment_report.html> <alignment_report_template.html>
-quit
```

Official references: [all CLI commands](https://rshelp.capturingreality.com/en-US/appbasics/allcommands.htm),
[keys and values](https://rshelp.capturingreality.com/en-US/tutorials/setkeyvaluetable.htm),
[alignment examples](https://rshelp.capturingreality.com/en-US/tutorials/commandline_1.htm), and
[report variables](https://rshelp.capturingreality.com/en-US/appbasics/reports_fav_components.htm).

RealityScan does not document a CLI version command. The controller reads Windows executable file
metadata; `None` is stored when reliable metadata is unavailable.

## Metrics

The project writes a minimal custom report template based on official report variables. This avoids
depending on localized or installation-specific predefined reports.

| Result field | Definition |
| --- | --- |
| `total_images` | Preflight count of supported files in the selected folder |
| `registered_images` | Sum of registered camera counts reported for all components |
| `registration_rate` | `registered_images / total_images` |
| `component_count` | RealityScan project component count |
| `largest_component_camera_count` | Camera count of the largest component |
| `sparse_point_count` | Registered point count of the largest component |
| `mean_reprojection_error` | Mean reprojection error of the largest component |
| `runtime_seconds` | Wall-clock duration of the RealityScan process |

Missing or malformed individual report values remain `None` and appear as `N/A`. An empty or
unrecognized report makes the experiment fail cleanly and preserves diagnostics.

## Experiment Output Structure

```text
benchmark_runs/
└── experiment_YYYYMMDD_HHMMSS_name/
    ├── config.json
    ├── command.txt
    ├── alignment_report_template.html
    ├── stdout.log
    ├── stderr.log
    ├── runtime.json
    ├── result.json
    └── realityscan_output/
        ├── project.rsproj
        ├── alignment_report.html
        ├── components/*.rsalign
        └── crash_reports/
```

RealityScan creates the project, report, and component files; the application never fabricates
them. Even a non-zero exit, timeout, process-start error, or parser error leaves `result.json` and
logs for debugging. Files RealityScan did not successfully export may naturally be absent.

## Tests

```powershell
pytest
ruff check .
```

Unit tests use mocked/fake controllers and do not require RealityScan. Fixtures under
`tests/fixtures/` are minimal project-authored report samples, not copied RealityScan reports.

The opt-in test in `integration_tests/` loads an existing project and exports only the report. It
requires explicit `RSBA_RUN_REALITYSCAN_INTEGRATION=1` plus executable, project, and output paths;
ordinary `pytest` runs never launch RealityScan. The report template has been verified successfully
against RealityScan 2.2.0.119430 RS.

## Known Limitations

- Image discovery is intentionally non-recursive, matching the current single-folder workflow.
- A RealityScan login/license dialog can still require interaction even in headless mode.
- The report template is verified against RealityScan 2.2; other versions may expose different
  paRSer variables and should run the opt-in report-only integration test before full alignment.
- Sparse points and reprojection error are defined for the largest component, not aggregated across
  unrelated components.
- Cancellation is not implemented. The GUI exposes an execution timeout with a 60-minute default;
  choosing unlimited time maps back to `timeout_seconds=None`.
- Real RealityScan integration tests are machine-specific and are not part of CI.
