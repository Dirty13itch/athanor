"""Tests for self-diagnosis engine.

Covers:
- Failure classification (PATTERN_RULES matching)
- Severity determination (critical services, resource failures)
- Pattern signature generation (normalization)
- Health score calculation
- Trend detection
- Analysis report generation
- Auto-remediation suggestions
"""

import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

# Mock dependencies before import
sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = MagicMock()
sys.modules["athanor_agents.services"] = MagicMock()

_DIAG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "diagnosis.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.diagnosis", _DIAG_PATH,
    submodule_search_locations=[],
)
diag = importlib.util.module_from_spec(spec)
diag.__package__ = "athanor_agents"
spec.loader.exec_module(diag)


class TestFailureClassification:
    """Pattern rule matching for error messages."""

    def test_cuda_oom(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "CUDA out of memory. Tried to allocate 2.0 GiB"
        )
        assert cat == diag.FailureCategory.INFERENCE
        assert "GPU memory" in desc

    def test_vllm_endpoint_down(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "connection refused at 192.168.1.244:8000"
        )
        assert cat == diag.FailureCategory.INFERENCE
        assert "vLLM endpoint" in desc

    def test_litellm_down(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "connection refused at 192.168.1.203:4000"
        )
        assert cat == diag.FailureCategory.INFERENCE
        assert "LiteLLM" in desc

    def test_nfs_stale(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "NFS stale file handle on /mnt/vault/models"
        )
        assert cat == diag.FailureCategory.NETWORK
        assert "NFS" in desc

    def test_disk_space(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "no space left on device"
        )
        assert cat == diag.FailureCategory.RESOURCE
        assert "Disk" in desc

    def test_qdrant_connection(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "qdrant connection error: refused"
        )
        assert cat == diag.FailureCategory.DEPENDENCY
        assert "Qdrant" in desc

    def test_redis_connection(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "redis connection error: refused"
        )
        assert cat == diag.FailureCategory.DEPENDENCY
        assert "Redis" in desc

    def test_permission_denied(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "Permission denied: /var/log/athanor"
        )
        assert cat == diag.FailureCategory.PERMISSION

    def test_kv_cache_corruption(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "kv cache corrupt: NaN values detected"
        )
        assert cat == diag.FailureCategory.INFERENCE
        assert "KV cache" in desc

    def test_unknown_error(self):
        cat, desc = diag.SelfDiagnosisEngine()._classify_failure(
            "something completely unexpected happened"
        )
        assert cat == diag.FailureCategory.UNKNOWN


class TestSeverityDetermination:
    """Severity levels based on service criticality and failure category."""

    def test_critical_service_resource_failure(self):
        engine = diag.SelfDiagnosisEngine()
        sev = engine._determine_severity(
            diag.FailureCategory.RESOURCE, "coordinator", "OOM"
        )
        assert sev == diag.Severity.CRITICAL

    def test_critical_service_dependency_failure(self):
        engine = diag.SelfDiagnosisEngine()
        sev = engine._determine_severity(
            diag.FailureCategory.DEPENDENCY, "redis", "connection refused"
        )
        assert sev == diag.Severity.CRITICAL

    def test_critical_service_other_failure(self):
        engine = diag.SelfDiagnosisEngine()
        sev = engine._determine_severity(
            diag.FailureCategory.INFERENCE, "coordinator", "model not found"
        )
        assert sev == diag.Severity.HIGH

    def test_non_critical_resource_failure(self):
        engine = diag.SelfDiagnosisEngine()
        sev = engine._determine_severity(
            diag.FailureCategory.RESOURCE, "tautulli", "disk full"
        )
        assert sev == diag.Severity.HIGH

    def test_non_critical_config_failure(self):
        engine = diag.SelfDiagnosisEngine()
        sev = engine._determine_severity(
            diag.FailureCategory.CONFIGURATION, "sonarr", "yaml error"
        )
        assert sev == diag.Severity.LOW


class TestPatternSignature:
    """Pattern signature normalization."""

    def test_ip_normalized(self):
        engine = diag.SelfDiagnosisEngine()
        sig1 = engine._generate_pattern_signature("error at 192.168.1.244:8000")
        sig2 = engine._generate_pattern_signature("error at 10.0.0.1:8000")
        # Both IPs should normalize to <IP>, ports to <PORT>
        assert sig1 == sig2

    def test_hex_ids_normalized(self):
        engine = diag.SelfDiagnosisEngine()
        sig1 = engine._generate_pattern_signature("request abcdef01 failed")
        sig2 = engine._generate_pattern_signature("request deadbeef failed")
        assert sig1 == sig2

    def test_different_errors_different_sigs(self):
        engine = diag.SelfDiagnosisEngine()
        sig1 = engine._generate_pattern_signature("CUDA out of memory")
        sig2 = engine._generate_pattern_signature("connection refused")
        assert sig1 != sig2


class TestHealthScore:
    """Health score calculation."""

    def test_perfect_health(self):
        engine = diag.SelfDiagnosisEngine()
        score = engine._health_score(0, {}, 24)
        assert score == 100.0

    def test_critical_failures_reduce_score(self):
        engine = diag.SelfDiagnosisEngine()
        score = engine._health_score(5, {"critical": 2}, 24)
        assert score < 100.0
        assert score == 80.0  # 100 - 2*10

    def test_mixed_severity(self):
        engine = diag.SelfDiagnosisEngine()
        score = engine._health_score(10, {"critical": 1, "high": 2, "medium": 3, "low": 4}, 24)
        # 100 - 10 - 10 - 6 - 2 = 72
        assert score == 72.0

    def test_score_never_negative(self):
        engine = diag.SelfDiagnosisEngine()
        score = engine._health_score(100, {"critical": 20}, 24)
        assert score == 0.0


class TestTrend:
    """Trend detection based on failure comparison."""

    def test_stable_no_failures(self):
        engine = diag.SelfDiagnosisEngine()
        trend = engine._trend(24)
        assert trend == "stable"

    def test_degrading_many_recent(self):
        engine = diag.SelfDiagnosisEngine()
        now = datetime.now(timezone.utc)
        # Add 10 recent failures, 0 in previous period
        for i in range(10):
            engine.events.append(diag.FailureEvent(
                id=f"f-{i}", timestamp=(now - timedelta(hours=1)).isoformat(),
                category="inference", severity="medium",
                service="test", error_message="test error",
            ))
        trend = engine._trend(24)
        assert trend == "degrading"


class TestAnalysis:
    """Full analysis report generation."""

    def test_empty_analysis(self):
        engine = diag.SelfDiagnosisEngine()
        report = engine.analyze(hours=24)
        assert report.total_failures == 0
        assert report.health_score == 100.0
        assert "No critical issues" in report.recommendations[0]

    def test_analysis_with_failures(self):
        engine = diag.SelfDiagnosisEngine()
        now = datetime.now(timezone.utc)
        for i in range(5):
            engine.events.append(diag.FailureEvent(
                id=f"f-{i}", timestamp=(now - timedelta(hours=1)).isoformat(),
                category="inference", severity="medium",
                service="coordinator", error_message="timeout",
            ))
        report = engine.analyze(hours=24)
        assert report.total_failures == 5
        assert report.health_score < 100.0
        assert report.failures_by_category.get("inference") == 5

    def test_analysis_excludes_resolved(self):
        engine = diag.SelfDiagnosisEngine()
        now = datetime.now(timezone.utc)
        engine.events.append(diag.FailureEvent(
            id="f-resolved", timestamp=(now - timedelta(hours=1)).isoformat(),
            category="inference", severity="medium",
            service="coordinator", error_message="timeout",
            resolved=True,
        ))
        report = engine.analyze(hours=24, include_resolved=False)
        assert report.total_failures == 0


class TestAutoRemediation:
    """Auto-remediation suggestion logic."""

    def test_container_down_suggestion(self):
        engine = diag.SelfDiagnosisEngine()
        engine.patterns["test-sig"] = diag.FailurePattern(
            id="test-sig", category="dependency",
            pattern_signature="test-sig",
            description="Container down",
            occurrences=5,
        )
        event = diag.FailureEvent(
            id="f-1", timestamp=datetime.now(timezone.utc).isoformat(),
            category="dependency", severity="high",
            service="redis", error_message="container not running",
            pattern_id="test-sig",
        )
        suggestion = engine.suggest_auto_remediation(event)
        assert suggestion is not None
        assert "docker restart" in suggestion["command"]
        assert suggestion["requires_confirmation"] is False

    def test_gpu_oom_requires_confirmation(self):
        engine = diag.SelfDiagnosisEngine()
        engine.patterns["gpu-sig"] = diag.FailurePattern(
            id="gpu-sig", category="inference",
            pattern_signature="gpu-sig",
            description="GPU memory exhaustion",
            occurrences=3,
        )
        event = diag.FailureEvent(
            id="f-2", timestamp=datetime.now(timezone.utc).isoformat(),
            category="inference", severity="critical",
            service="vllm-coordinator", error_message="CUDA OOM",
            pattern_id="gpu-sig",
        )
        suggestion = engine.suggest_auto_remediation(event)
        assert suggestion is not None
        assert suggestion["requires_confirmation"] is True

    def test_no_suggestion_for_unknown(self):
        engine = diag.SelfDiagnosisEngine()
        engine.patterns["unk-sig"] = diag.FailurePattern(
            id="unk-sig", category="unknown",
            pattern_signature="unk-sig",
            description="Some random thing",
            occurrences=1,
        )
        event = diag.FailureEvent(
            id="f-3", timestamp=datetime.now(timezone.utc).isoformat(),
            category="unknown", severity="low",
            service="test", error_message="weird error",
            pattern_id="unk-sig",
        )
        suggestion = engine.suggest_auto_remediation(event)
        assert suggestion is None

    def test_no_pattern_no_suggestion(self):
        engine = diag.SelfDiagnosisEngine()
        event = diag.FailureEvent(
            id="f-4", timestamp=datetime.now(timezone.utc).isoformat(),
            category="unknown", severity="low",
            service="test", error_message="error",
            pattern_id=None,
        )
        suggestion = engine.suggest_auto_remediation(event)
        assert suggestion is None


class TestCriticalServices:
    """Verify critical service list."""

    def test_expected_services(self):
        expected = {"coordinator", "utility", "worker", "litellm",
                    "qdrant", "redis", "neo4j", "athanor-agents", "grafana"}
        assert set(diag.CRITICAL_SERVICES) == expected

    def test_pattern_rules_categories(self):
        """All expected categories have pattern rules."""
        for cat in [diag.FailureCategory.INFERENCE, diag.FailureCategory.NETWORK,
                    diag.FailureCategory.RESOURCE, diag.FailureCategory.DEPENDENCY,
                    diag.FailureCategory.CONFIGURATION]:
            assert cat in diag.PATTERN_RULES
            assert len(diag.PATTERN_RULES[cat]) >= 2
