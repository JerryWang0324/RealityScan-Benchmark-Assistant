from rs_benchmark.realityscan.report_template import ALIGNMENT_REPORT_TEMPLATE


def test_template_uses_realityscan_22_parser_syntax() -> None:
    assert '$Using( "RealityScan.Report.ProjectInformationExportFunctionSet" )' in (
        ALIGNMENT_REPORT_TEMPLATE
    )
    assert '$Using( "RealityScan.Report.IteratorsFunctionSet" )' in ALIGNMENT_REPORT_TEMPLATE
    assert '$Using( "RealityScan.Report.ComponentFunctionSet" )' in ALIGNMENT_REPORT_TEMPLATE
    assert "componentCamerasCount" in ALIGNMENT_REPORT_TEMPLATE
    assert "componentPointsCount" in ALIGNMENT_REPORT_TEMPLATE
    assert "componentMeanError" in ALIGNMENT_REPORT_TEMPLATE
    assert "componentAlignmentTimeSec" in ALIGNMENT_REPORT_TEMPLATE
    assert "componentCameraCount" not in ALIGNMENT_REPORT_TEMPLATE
    assert "componentPointCount" not in ALIGNMENT_REPORT_TEMPLATE
