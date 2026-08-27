"""Benchmark orchestration boundary for the CLI integration phase.

The runner will depend on ``RealityScanControllerProtocol`` rather than Qt or a
concrete subprocess implementation, keeping orchestration unit-testable.
"""

