from pathlib import Path

from omp.evals.runner import _decision, load_config


def test_hash_v1_config_is_complete_and_frozen() -> None:
    config = load_config(Path("evals/configs/hash-v1.yaml"))
    assert config["threshold"] == 0.78
    assert config["result_limit"] == 5
    assert config["profile_id"] == "hash"


def test_gate_decision_rejects_a_deterministic_failure() -> None:
    metrics = {
        "precision_at_5": 1.0,
        "intrusion_at_5": 0.0,
        "abstention_rate": 1.0,
        "lifecycle_isolation_correctness": 0.99,
    }
    decision, reasons = _decision(metrics, {"query_kind": {}}, 12.0, {"p95_budget_ms": 2500})
    assert decision == "NO-GO"
    assert reasons == ["deterministic lifecycle/isolation/profile failure"]
