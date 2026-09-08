# Experimental Design

## Manual

Use manually selected configurations for targeted hypotheses or a small comparison where each row
has an explicit purpose.

## Full Factorial

Runs the Cartesian product of supplied parameter values. It can expose interactions between tested
parameters, while experiment count grows quickly as levels are added.

## One Factor At A Time (OFAT)

Starts from an explicit baseline and changes one parameter per experiment. It provides clear local,
descriptive sensitivity comparisons but does not estimate interactions among changing parameters.

Generated designs store stable experiment IDs, sweep identity, mode, baseline, varied parameters,
and generation time. They support reproducibility; they do not imply automatic optimization.

