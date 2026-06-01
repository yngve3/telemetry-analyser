from __future__ import annotations

import unittest

from support import ANALYSIS_MODULE_ROOT  # noqa: F401

import analysis_module


class PublicApiTest(unittest.TestCase):
    def test_public_api_exports_stable_symbols(self) -> None:
        self.assertIn("UnifiedTelemetry", analysis_module.__all__)
        self.assertIn("AnalysisContext", analysis_module.__all__)
        self.assertIn("AnalysisResult", analysis_module.__all__)
        self.assertIn("AnalysisTiming", analysis_module.__all__)
        self.assertIn("AnomalyReason", analysis_module.__all__)
        self.assertIn("AnomalySource", analysis_module.__all__)
        self.assertIn("AnomalyResult", analysis_module.__all__)
        self.assertIn("DetectedAnomaly", analysis_module.__all__)
        self.assertIn("DetectorTiming", analysis_module.__all__)
        self.assertIn("DetectorConfigurationError", analysis_module.__all__)
        self.assertIn("DetectorKind", analysis_module.__all__)
        self.assertIn("DetectorOutput", analysis_module.__all__)
        self.assertIn("DetectorStatus", analysis_module.__all__)
        self.assertIn("FeatureStatistics", analysis_module.__all__)
        self.assertIn("ReasonDiagnostics", analysis_module.__all__)
        self.assertIn("ReasonDiagnosticsResult", analysis_module.__all__)
        self.assertIn("AnomalyType", analysis_module.__all__)
        self.assertIn("PipelineAnalysisResult", analysis_module.__all__)
        self.assertIn("Severity", analysis_module.__all__)
        self.assertIn("TelemetryAnalyzer", analysis_module.__all__)
        self.assertIn("TelemetryDetector", analysis_module.__all__)
        self.assertIn("AnalyzerConfig", analysis_module.__all__)
        self.assertIn(
            "create_adaptive_correlation_based_detector",
            analysis_module.__all__,
        )
        self.assertIn("create_autoencoder_detector", analysis_module.__all__)
        self.assertIn("create_correlation_based_detector", analysis_module.__all__)
        self.assertIn("create_detectors", analysis_module.__all__)
        self.assertIn("create_default_analyzer", analysis_module.__all__)
        self.assertIn("create_isolation_forest_detector", analysis_module.__all__)


if __name__ == "__main__":
    unittest.main()
