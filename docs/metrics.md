# Metrics

## Registration Rate

`registered_images / total_images × 100`. It describes how much of the input set RealityScan placed
in reported components. A high rate does not independently establish geometric correctness.

## Components

The number of alignment components reported by RealityScan. Multiple components often indicate a
disconnected camera network, although the cause requires dataset inspection.

## Sparse Point Count

The reported registered point count of the largest component. It can describe reconstruction
density and matching behavior. More points do not necessarily mean a more accurate or useful model.

## Mean Reprojection Error

The reported mean image-space residual for the largest component, in pixels. It is an internal fit
indicator. It cannot substitute for independent absolute 3D accuracy measurements.

## Runtime

Wall-clock duration of the RealityScan process attempt, in seconds. Runtime comparisons depend on
hardware, RealityScan version, dataset, thermal state, storage, and operating-system caching.

