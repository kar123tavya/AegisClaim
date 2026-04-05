"""
AegisClaim AI - Evaluation Metrics
Computes accuracy, precision, recall, F1, false rejection rate, and confusion matrix.
"""
import logging
from typing import Optional
from collections import Counter

logger = logging.getLogger("aegisclaim.evaluation.metrics")

try:
    import numpy as np
    NP_AVAILABLE = True
except ImportError:
    NP_AVAILABLE = False


class EvaluationMetrics:
    """Computes comprehensive evaluation metrics for claim decisions."""

    @staticmethod
    def compute_all(
        predictions: list[str],
        ground_truth: list[str],
        confidences: list[float] = None,
    ) -> dict:
        """
        Compute all evaluation metrics.
        
        Args:
            predictions: List of predicted decisions
            ground_truth: List of expected decisions
            confidences: List of confidence scores
            
        Returns:
            Dictionary with all metrics
        """
        # Normalize labels
        preds = [EvaluationMetrics._normalize_label(p) for p in predictions]
        truth = [EvaluationMetrics._normalize_label(t) for t in ground_truth]
        
        # Basic accuracy
        correct = sum(1 for p, t in zip(preds, truth) if p == t)
        total = len(preds)
        accuracy = correct / max(total, 1)
        
        # Per-class metrics
        classes = sorted(set(preds + truth))
        per_class = {}
        for cls in classes:
            tp = sum(1 for p, t in zip(preds, truth) if p == cls and t == cls)
            fp = sum(1 for p, t in zip(preds, truth) if p == cls and t != cls)
            fn = sum(1 for p, t in zip(preds, truth) if p != cls and t == cls)
            tn = sum(1 for p, t in zip(preds, truth) if p != cls and t != cls)
            
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)
            
            per_class[cls] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": tp + fn,
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn,
            }
        
        # Macro average
        macro_precision = sum(m["precision"] for m in per_class.values()) / max(len(per_class), 1)
        macro_recall = sum(m["recall"] for m in per_class.values()) / max(len(per_class), 1)
        macro_f1 = sum(m["f1"] for m in per_class.values()) / max(len(per_class), 1)
        
        # Weighted average
        total_support = sum(m["support"] for m in per_class.values())
        weighted_precision = sum(
            m["precision"] * m["support"] for m in per_class.values()
        ) / max(total_support, 1)
        weighted_recall = sum(
            m["recall"] * m["support"] for m in per_class.values()
        ) / max(total_support, 1)
        weighted_f1 = sum(
            m["f1"] * m["support"] for m in per_class.values()
        ) / max(total_support, 1)
        
        # False Rejection Rate (critical for healthcare)
        # FRR = claims that should be approved but were rejected
        frr = EvaluationMetrics._false_rejection_rate(preds, truth)
        
        # Confusion matrix
        confusion = EvaluationMetrics._confusion_matrix(preds, truth, classes)
        
        # Confidence calibration
        calibration = None
        if confidences:
            calibration = EvaluationMetrics._confidence_calibration(
                preds, truth, confidences
            )
        
        return {
            "accuracy": round(accuracy, 4),
            "total_predictions": total,
            "correct_predictions": correct,
            "per_class_metrics": per_class,
            "macro_avg": {
                "precision": round(macro_precision, 4),
                "recall": round(macro_recall, 4),
                "f1": round(macro_f1, 4),
            },
            "weighted_avg": {
                "precision": round(weighted_precision, 4),
                "recall": round(weighted_recall, 4),
                "f1": round(weighted_f1, 4),
            },
            "false_rejection_rate": round(frr, 4),
            "confusion_matrix": confusion,
            "calibration": calibration,
            "classes": classes,
        }

    @staticmethod
    def _normalize_label(label: str) -> str:
        """Normalize decision labels."""
        label = label.upper().strip()
        if label in ("APPROVED", "APPROVE", "ACCEPTED", "ACCEPT"):
            return "APPROVED"
        elif label in ("REJECTED", "REJECT", "DENIED", "DENY"):
            return "REJECTED"
        elif label in ("NEEDS_REVIEW", "REVIEW", "PENDING", "NEEDS REVIEW"):
            return "NEEDS_REVIEW"
        elif label in ("PARTIALLY_APPROVED", "PARTIAL", "PARTIALLY APPROVED"):
            return "PARTIALLY_APPROVED"
        return label

    @staticmethod
    def _false_rejection_rate(predictions: list[str], ground_truth: list[str]) -> float:
        """
        Calculate False Rejection Rate.
        FRR = (Valid claims incorrectly rejected) / (Total valid claims)
        """
        total_valid = sum(1 for t in ground_truth if t == "APPROVED")
        false_rejections = sum(
            1 for p, t in zip(predictions, ground_truth)
            if t == "APPROVED" and p in ("REJECTED", "NEEDS_REVIEW")
        )
        return false_rejections / max(total_valid, 1)

    @staticmethod
    def _confusion_matrix(
        predictions: list[str],
        ground_truth: list[str],
        classes: list[str],
    ) -> dict:
        """Build confusion matrix."""
        matrix = {actual: {pred: 0 for pred in classes} for actual in classes}
        
        for pred, actual in zip(predictions, ground_truth):
            if actual in matrix and pred in matrix[actual]:
                matrix[actual][pred] += 1
        
        return {
            "matrix": matrix,
            "labels": classes,
        }

    @staticmethod
    def _confidence_calibration(
        predictions: list[str],
        ground_truth: list[str],
        confidences: list[float],
    ) -> dict:
        """Analyze confidence calibration."""
        bins = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
        calibration = []
        
        for low, high in bins:
            bin_mask = [low <= c < high for c in confidences]
            bin_preds = [p for p, m in zip(predictions, bin_mask) if m]
            bin_truth = [t for t, m in zip(ground_truth, bin_mask) if m]
            
            if bin_preds:
                accuracy = sum(1 for p, t in zip(bin_preds, bin_truth) if p == t) / len(bin_preds)
                avg_confidence = sum(c for c, m in zip(confidences, bin_mask) if m) / len(bin_preds)
                calibration.append({
                    "confidence_range": f"{low}-{high}%",
                    "count": len(bin_preds),
                    "accuracy": round(accuracy, 4),
                    "avg_confidence": round(avg_confidence, 2),
                    "gap": round(abs(accuracy - avg_confidence / 100), 4),
                })
        
        return calibration

    @staticmethod
    def format_report(metrics: dict) -> str:
        """Format metrics as a readable report."""
        report = "=" * 60 + "\n"
        report += "       AegisClaim AI - Evaluation Report\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Overall Accuracy: {metrics['accuracy']:.2%}\n"
        report += f"Total Predictions: {metrics['total_predictions']}\n"
        report += f"Correct: {metrics['correct_predictions']}\n"
        report += f"False Rejection Rate: {metrics['false_rejection_rate']:.2%}\n\n"
        
        report += "-" * 50 + "\n"
        report += f"{'Class':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}\n"
        report += "-" * 50 + "\n"
        
        for cls, m in metrics["per_class_metrics"].items():
            report += f"{cls:<20} {m['precision']:>10.4f} {m['recall']:>10.4f} {m['f1']:>10.4f} {m['support']:>10d}\n"
        
        report += "-" * 50 + "\n"
        report += f"{'Macro Avg':<20} {metrics['macro_avg']['precision']:>10.4f} {metrics['macro_avg']['recall']:>10.4f} {metrics['macro_avg']['f1']:>10.4f}\n"
        report += f"{'Weighted Avg':<20} {metrics['weighted_avg']['precision']:>10.4f} {metrics['weighted_avg']['recall']:>10.4f} {metrics['weighted_avg']['f1']:>10.4f}\n"
        
        report += "\n" + "=" * 60 + "\n"
        report += "Confusion Matrix:\n"
        cm = metrics["confusion_matrix"]
        labels = cm["labels"]
        matrix = cm["matrix"]
        
        header = f"{'Actual \\ Predicted':<20}" + "".join(f"{l:>15}" for l in labels)
        report += header + "\n"
        for actual in labels:
            row = f"{actual:<20}"
            for pred in labels:
                row += f"{matrix[actual][pred]:>15d}"
            report += row + "\n"
        
        if metrics.get("calibration"):
            report += "\nConfidence Calibration:\n"
            for cal in metrics["calibration"]:
                report += (
                    f"  {cal['confidence_range']:>8}: "
                    f"Accuracy={cal['accuracy']:.2%}, "
                    f"Avg Conf={cal['avg_confidence']:.0f}%, "
                    f"Gap={cal['gap']:.2%} "
                    f"(n={cal['count']})\n"
                )
        
        return report
