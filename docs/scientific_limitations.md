# Scientific Limitations

This tool compares RealityScan outputs and processing behavior. It does not independently verify
absolute geometric accuracy unless external ground truth is provided.

Internal metric does not equal absolute accuracy. Registration rate, component count, sparse point
count, and reported reprojection error are useful descriptive indicators, but each can improve while
an unmeasured aspect of geometry becomes worse. A true accuracy study needs surveyed control points,
known distances, reference geometry, or another independent measurement process.

Pareto membership is conditional on the selected metrics and available values. The primary frontier
uses registration rate and runtime. The optional registration/reprojection frontier is explicitly a
metric-based comparison. Neither constitutes an overall ranking or an optimal-parameter claim.

Sweep observations are dataset-specific and rule-based. The diminishing-return message describes a
small registration-rate change accompanied by a large runtime increase; it does not recommend an
optimal setting or establish causality beyond the tested design.
