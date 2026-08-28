"""Minimal machine-readable template using official RealityScan report variables."""

ALIGNMENT_REPORT_TEMPLATE = """<!doctype html>
<html><body><pre>
$Using( "RealityScan.Report.ProjectInformationExportFunctionSet" )
$Using( "RealityScan.Report.IteratorsFunctionSet" )
$Using( "RealityScan.Report.ComponentFunctionSet" )
$ExportProjectInfo(
RSBA_PROJECT|version=$(appVersion)|total_images=$(imageCount)|component_count=$(componentCount)
)
$IterateComponents(
$ComponentInfo( "$(componentGUID)",
RSBA_COMPONENT_INFO|id=$(componentGUID)|cameras=$(componentCamerasCount)|points=$(componentPointsCount)
)
$ComponentStats( "$(componentGUID)",
RSBA_COMPONENT_STATS|id=$(componentGUID)|mean_error=$(componentMeanError)|alignment_time=$(componentAlignmentTimeSec)
)
)
</pre></body></html>
"""
