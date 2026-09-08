# Reproducibility

Each run records experiment configs, parsed results, tool and RealityScan versions when available,
Python and operating-system metadata, timestamps, and a dataset fingerprint derived from relative
file names, sizes, and modification times.

The exported ZIP uses an allow-list and includes sanitized benchmark metadata, summary JSON, CSV,
`analysis.json`, offline `report.html`, local charts, sweep definitions, and experiment configs. It
does not include input photographs, the RealityScan executable, process caches, or full RealityScan
project outputs. Absolute paths are shortened in public artifacts to forms such as
`<dataset>/Building01`.

A dataset fingerprint helps detect changed inputs; it does not embed or publish image content. Exact
runtime reproduction additionally requires comparable software, hardware, storage, and system load.

