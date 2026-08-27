# RealityScan Benchmark Assistant

A Windows desktop application for reproducible RealityScan / RealityCapture alignment experiments.
It will run the same image dataset with multiple alignment parameter sets, preserve each run's
inputs and outputs, and compare registration quality and runtime.

> **Project status:** foundation phase. The typed models, official CLI parameter mapping,
> process-controller boundary, settings persistence, logging, minimal GUI, and unit-test suite are
> in place. Full RealityScan execution is deliberately not enabled yet.

## Why this project exists

Photogrammetry settings involve trade-offs between registration success, geometric quality, and
runtime. Manual comparisons are slow and easy to document inconsistently. This tool is designed to
make those comparisons repeatable and reviewable.

## Current MVP scope

The planned MVP covers RealityScan **Alignment only**. It excludes mesh reconstruction, texture,
dense point clouds, machine learning, automatic optimization, and a 3D viewer.

The initial parameter model uses the current official RealityScan keys:

| Internal name | RealityScan CLI key | Default |
| --- | --- | --- |
| `feature_detection_quality` | `sfmFeatureDetectionQuality` | `High` |
| `max_features_per_image` | `sfmMaxFeaturesPerImage` | `40000` |
| `image_overlap` | `sfmImagesOverlap` | `Medium` |
| `max_feature_reprojection_error` | `sfmMaxFeatureReprojectionError` | `2.0` |

Sources: [RealityScan CLI keys and values](https://rshelp.capturingreality.com/en-US/tutorials/setkeyvaluetable.htm),
[all CLI commands](https://rshelp.capturingreality.com/en-US/appbasics/allcommands.htm), and
[alignment examples](https://rshelp.capturingreality.com/en-US/tutorials/commandline_1.htm).

## Architecture

```text
src/rs_benchmark/
├── gui/          PySide6 presentation; no subprocess calls
├── models/       Typed dataclasses and serialization
├── realityscan/  CLI keys, command builder, controller, parser boundary
├── services/     Settings now; benchmark orchestration next
├── reports/      CSV and chart extension points
└── utils/        Paths and logging configuration
```

`RealityScanController` is the only layer that invokes a subprocess. Its protocol makes it
replaceable with a test double, so CI does not require RealityScan. Internal parameter names are
separate from the official CLI strings, which are centralized in `realityscan/commands.py`.

See [docs/architecture.md](docs/architecture.md) for the dependency boundaries.

## Installation

Requirements: Windows 11 and Python 3.12 or newer. RealityScan is not bundled.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Select `RealityScan.exe` (or the legacy `RealityCapture.exe`) from the GUI. Its path is stored in the
ignored local file `config/app_settings.json`; no machine-specific path is committed.

## Run the GUI

### Windows 一鍵啟動

在 Windows 檔案總管中雙擊 `run.bat` 即可啟動 GUI。第一次啟動時，腳本可能需要建立
`.venv` 虛擬環境並下載 runtime dependencies；後續啟動會直接使用既有的 `.venv`，只有在
必要套件或專案本身無法 import 時才會重新安裝。系統需已安裝 Python 3.12 或更新版本。

以下手動啟動方式仍然保留：

```powershell
python -m rs_benchmark.main
```

After editable installation, `rs-benchmark` is also available. Application logs are written to the
ignored file `logs/app.log`.

## Development

```powershell
pytest
ruff check .
```

Tests currently cover dataclass serialization, validation, official-key command construction,
invalid executable handling, incomplete report safety, missing image folders, and reproducible run
folder creation. They never launch RealityScan.

## Known limitations

- Benchmark orchestration and the background `QThread` worker are not implemented.
- The report parser currently returns optional metrics as `None`; official report export and field
  mapping must be integrated before parsing real results.
- Experiment editing, CSV export, result tables, and charts are placeholders.
- RealityScan version detection and real-process behavior have not been verified on an installed
  RealityScan system.
- Image counting is non-recursive in this phase.

## Roadmap

1. Define an official, versioned RealityScan report template and implement parser fixtures.
2. Add benchmark orchestration with per-experiment artifacts and failure isolation.
3. Run orchestration in a Qt background worker with progress and cancellation.
4. Add experiment editing and comparison results.
5. Export CSV plus registration-rate and runtime charts.

## Repository hygiene

Generated benchmark runs, logs, local settings, datasets, RealityScan binaries, project files, and
caches are ignored. Never commit private datasets, credentials, or machine-specific absolute paths.
