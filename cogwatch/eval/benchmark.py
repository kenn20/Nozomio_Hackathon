"""MLflow benchmark for CogWatch detection accuracy and advisory quality.

Evaluates:
1. Detection accuracy — does the agent correctly identify contradictions?
2. Advisory quality — are persona responses grounded and actionable?
3. Model viability — nemotron (free) vs proprietary baseline
"""

import json
import logging
from pathlib import Path

import mlflow

from cogwatch.config import JUDGE_MODEL, LLM_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from cogwatch.llm import check_contradiction

logger = logging.getLogger(__name__)

SCENARIOS_PATH = Path(__file__).parent / "scenarios" / "test_scenarios.json"


def load_scenarios() -> list[dict]:
    """Load test scenarios from JSON file."""
    with open(SCENARIOS_PATH) as f:
        return json.load(f)


def run_detection_eval() -> dict:
    """Evaluate detection accuracy on test scenarios."""
    scenarios = load_scenarios()
    results = []

    for scenario in scenarios:
        try:
            result = check_contradiction(
                old_decision=scenario["old_decision"],
                old_date="2 weeks ago",
                new_activity=scenario["new_activity"],
                new_date="today",
            )

            correct = result.get("is_contradiction", False) == scenario["expected_contradiction"]

            severity_correct = True
            if scenario["expected_contradiction"] and scenario["expected_severity"]:
                severity_correct = result.get("severity") == scenario["expected_severity"]

            type_correct = True
            if scenario["expected_contradiction"] and scenario["expected_type"]:
                type_correct = result.get("contradiction_type") == scenario["expected_type"]

            results.append(
                {
                    "scenario_id": scenario["id"],
                    "expected_contradiction": scenario["expected_contradiction"],
                    "predicted_contradiction": result.get("is_contradiction", False),
                    "detection_correct": correct,
                    "severity_correct": severity_correct,
                    "type_correct": type_correct,
                    "explanation": result.get("explanation", ""),
                    "notes": scenario.get("notes", ""),
                }
            )

        except Exception as e:
            logger.error("Error evaluating scenario %s: %s", scenario["id"], e)
            results.append(
                {
                    "scenario_id": scenario["id"],
                    "detection_correct": False,
                    "error": str(e),
                }
            )

    return _compute_metrics(results)


def run_advisory_eval() -> dict:
    """Evaluate advisory quality using LLM-as-Judge (Gemini via OpenRouter)."""
    if not OPENROUTER_API_KEY:
        logger.warning("No OPENROUTER_API_KEY set, skipping advisory eval")
        return {"skipped": True, "reason": "No OPENROUTER_API_KEY"}

    from openai import OpenAI

    judge = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )

    scenarios = load_scenarios()
    contradiction_scenarios = [s for s in scenarios if s["expected_contradiction"]]
    scores: list[dict] = []

    for scenario in contradiction_scenarios[:5]:
        # Generate advisory from CogWatch
        result = check_contradiction(
            old_decision=scenario["old_decision"],
            old_date="2 weeks ago",
            new_activity=scenario["new_activity"],
            new_date="today",
        )

        # Judge the output
        try:
            judge_response = judge.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert evaluator. Score the following contradiction detection output "
                            "on a 1-5 scale for each criterion. Respond as JSON: "
                            '{"relevance": int, "groundedness": int, "actionability": int, "explanation": str}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Old decision: {scenario['old_decision']}\n"
                            f"New activity: {scenario['new_activity']}\n\n"
                            f"Detection output:\n{json.dumps(result, indent=2)}\n\n"
                            f"Score this output:\n"
                            f"- Relevance (1-5): Is the detection relevant to the actual contradiction?\n"
                            f"- Groundedness (1-5): Does it reference real content vs hallucinate?\n"
                            f"- Actionability (1-5): Can the user act on this?"
                        ),
                    },
                ],
            )
            judge_scores = json.loads(judge_response.choices[0].message.content)
            scores.append(
                {
                    "scenario_id": scenario["id"],
                    **judge_scores,
                }
            )
        except Exception as e:
            logger.error("Error in advisory eval for %s: %s", scenario["id"], e)

    if not scores:
        return {"skipped": True, "reason": "No scores generated"}

    avg_relevance = sum(s.get("relevance", 0) for s in scores) / len(scores)
    avg_groundedness = sum(s.get("groundedness", 0) for s in scores) / len(scores)
    avg_actionability = sum(s.get("actionability", 0) for s in scores) / len(scores)

    return {
        "avg_relevance": round(avg_relevance, 2),
        "avg_groundedness": round(avg_groundedness, 2),
        "avg_actionability": round(avg_actionability, 2),
        "num_scenarios": len(scores),
        "scores": scores,
    }


def _compute_metrics(results: list[dict]) -> dict:
    """Compute aggregate metrics from detection results."""
    total = len(results)
    correct = sum(1 for r in results if r.get("detection_correct", False))
    accuracy = correct / total if total > 0 else 0

    # Precision/recall for contradiction detection
    true_positives = sum(
        1 for r in results if r.get("detection_correct") and r.get("expected_contradiction")
    )
    false_positives = sum(
        1 for r in results if not r.get("detection_correct") and not r.get("expected_contradiction")
    )
    false_negatives = sum(
        1 for r in results if not r.get("detection_correct") and r.get("expected_contradiction")
    )

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )

    severity_correct = sum(1 for r in results if r.get("severity_correct", False))
    type_correct = sum(1 for r in results if r.get("type_correct", False))

    return {
        "accuracy": round(accuracy, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "severity_accuracy": round(severity_correct / total, 3) if total > 0 else 0,
        "type_accuracy": round(type_correct / total, 3) if total > 0 else 0,
        "total_scenarios": total,
        "correct_detections": correct,
        "model": LLM_MODEL,
        "results": results,
    }


def run_full_benchmark() -> None:
    """Run the full benchmark and log to MLflow."""
    mlflow.set_experiment("cogwatch-eval")

    with mlflow.start_run(run_name="cogwatch-detection-eval"):
        # Detection eval
        detection_metrics = run_detection_eval()
        mlflow.log_metric("detection_accuracy", detection_metrics["accuracy"])
        mlflow.log_metric("detection_precision", detection_metrics["precision"])
        mlflow.log_metric("detection_recall", detection_metrics["recall"])
        mlflow.log_metric("severity_accuracy", detection_metrics["severity_accuracy"])
        mlflow.log_metric("type_accuracy", detection_metrics["type_accuracy"])
        mlflow.log_param("model", detection_metrics["model"])
        mlflow.log_param("total_scenarios", detection_metrics["total_scenarios"])

        # Log detailed results as artifact
        results_path = "/tmp/detection_results.json"
        with open(results_path, "w") as f:
            json.dump(detection_metrics["results"], f, indent=2)
        mlflow.log_artifact(results_path)

        # Advisory eval
        advisory_metrics = run_advisory_eval()
        if not advisory_metrics.get("skipped"):
            mlflow.log_metric("advisory_relevance", advisory_metrics["avg_relevance"])
            mlflow.log_metric("advisory_groundedness", advisory_metrics["avg_groundedness"])
            mlflow.log_metric("advisory_actionability", advisory_metrics["avg_actionability"])

        print(f"\n{'=' * 60}")
        print("CogWatch Benchmark Results")
        print(f"{'=' * 60}")
        print(f"Model: {detection_metrics['model']}")
        print(f"Detection Accuracy: {detection_metrics['accuracy']:.1%}")
        print(f"Precision: {detection_metrics['precision']:.1%}")
        print(f"Recall: {detection_metrics['recall']:.1%}")
        if not advisory_metrics.get("skipped"):
            print(f"Advisory Relevance: {advisory_metrics['avg_relevance']}/5")
            print(f"Advisory Groundedness: {advisory_metrics['avg_groundedness']}/5")
            print(f"Advisory Actionability: {advisory_metrics['avg_actionability']}/5")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_benchmark()
