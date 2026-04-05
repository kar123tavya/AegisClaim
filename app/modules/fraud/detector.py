"""
AegisClaim AI - Fraud & Anomaly Detection
Detects abnormal billing patterns, duplicate claims, and unusual pricing.
"""
import logging
import numpy as np
from typing import Optional
from collections import Counter

logger = logging.getLogger("aegisclaim.fraud.detector")

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from app.modules.ocr.schemas import ExtractedBillData, BillItemCategory
from .schemas import FraudFlag, FraudAnalysisResult


# Average pricing benchmarks (INR) for medical services
PRICE_BENCHMARKS = {
    BillItemCategory.ROOM_CHARGES: {"min": 1000, "max": 25000, "median": 5000},
    BillItemCategory.ICU_CHARGES: {"min": 5000, "max": 75000, "median": 20000},
    BillItemCategory.SURGERY: {"min": 10000, "max": 1000000, "median": 100000},
    BillItemCategory.PROCEDURE: {"min": 2000, "max": 500000, "median": 30000},
    BillItemCategory.DIAGNOSTIC: {"min": 500, "max": 50000, "median": 5000},
    BillItemCategory.LABORATORY: {"min": 200, "max": 20000, "median": 2000},
    BillItemCategory.MEDICATION: {"min": 100, "max": 100000, "median": 5000},
    BillItemCategory.CONSULTATION: {"min": 500, "max": 10000, "median": 2000},
    BillItemCategory.NURSING: {"min": 500, "max": 10000, "median": 2000},
    BillItemCategory.SUPPLIES: {"min": 100, "max": 50000, "median": 3000},
    BillItemCategory.AMBULANCE: {"min": 500, "max": 15000, "median": 3000},
}


class FraudDetector:
    """
    Multi-layer fraud detection combining statistical analysis,
    pattern matching, and ML-based anomaly detection.
    """

    def __init__(self):
        self.isolation_forest = None
        self.scaler = None
        if SKLEARN_AVAILABLE:
            self._initialize_model()

    def _initialize_model(self):
        """Initialize the Isolation Forest model with synthetic training data."""
        # Generate synthetic normal claims for training
        np.random.seed(42)
        n_samples = 500
        
        features = np.column_stack([
            np.random.lognormal(10, 0.8, n_samples),   # total_amount
            np.random.randint(1, 20, n_samples),         # num_items
            np.random.uniform(0.5, 1.0, n_samples),     # price_ratio (actual/benchmark)
            np.random.randint(1, 30, n_samples),         # stay_duration
            np.random.uniform(0, 5, n_samples),          # category_diversity
        ])
        
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features)
        
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        self.isolation_forest.fit(features_scaled)
        logger.info("Fraud detection model initialized")

    def analyze(
        self,
        bill_data: ExtractedBillData,
        historical_claims: list[dict] = None,
    ) -> FraudAnalysisResult:
        """
        Perform comprehensive fraud analysis on a claim.
        
        Args:
            bill_data: Structured bill data
            historical_claims: Optional list of previous claims for duplicate detection
            
        Returns:
            FraudAnalysisResult with risk score and detailed flags
        """
        flags = []
        
        # Layer 1: Statistical Anomaly Detection
        pricing_flags = self._check_pricing_anomalies(bill_data)
        flags.extend(pricing_flags)
        
        # Layer 2: Pattern-Based Detection
        pattern_flags = self._check_fraud_patterns(bill_data)
        flags.extend(pattern_flags)
        
        # Layer 3: Duplicate Detection
        if historical_claims:
            duplicate_flags = self._check_duplicates(bill_data, historical_claims)
            flags.extend(duplicate_flags)
        
        # Layer 4: ML-Based Anomaly Score
        ml_score = self._ml_anomaly_score(bill_data)
        if ml_score > 0.7:
            flags.append(FraudFlag(
                flag_type="anomaly",
                severity="high" if ml_score > 0.85 else "medium",
                description=f"Machine learning model flags this claim as anomalous (score: {ml_score:.2f})",
                score=ml_score,
                evidence="Statistical deviation from normal claim patterns"
            ))

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(flags, ml_score)
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 60:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Build summary
        summary = self._build_summary(flags, risk_score, risk_level)
        
        # Recommendation
        if risk_level == "CRITICAL":
            recommendation = "BLOCK claim processing. Escalate to fraud investigation team immediately."
        elif risk_level == "HIGH":
            recommendation = "Flag for manual review by senior adjudicator before processing."
        elif risk_level == "MEDIUM":
            recommendation = "Proceed with caution. Additional verification recommended."
        else:
            recommendation = "No significant fraud indicators detected. Proceed normally."

        return FraudAnalysisResult(
            fraud_risk_score=round(risk_score, 1),
            risk_level=risk_level,
            flags=flags,
            anomalies_detected=len(flags),
            summary=summary,
            recommendation=recommendation
        )

    def _check_pricing_anomalies(self, bill_data: ExtractedBillData) -> list[FraudFlag]:
        """Detect unusual pricing compared to benchmarks."""
        flags = []
        
        for item in bill_data.line_items:
            benchmark = PRICE_BENCHMARKS.get(item.category)
            if not benchmark:
                continue
            
            # Check if price is abnormally high
            if item.amount > benchmark["max"] * 2:
                flags.append(FraudFlag(
                    flag_type="pricing",
                    severity="high",
                    description=f"'{item.description}' priced at ₹{item.amount:,.0f} — "
                               f"significantly above typical maximum (₹{benchmark['max']:,.0f})",
                    score=min(item.amount / benchmark["max"], 5.0),
                    evidence=f"Category: {item.category.value}, "
                            f"Benchmark range: ₹{benchmark['min']:,.0f} - ₹{benchmark['max']:,.0f}"
                ))
            elif item.amount > benchmark["max"]:
                flags.append(FraudFlag(
                    flag_type="pricing",
                    severity="medium",
                    description=f"'{item.description}' priced above typical maximum "
                               f"(₹{item.amount:,.0f} vs ₹{benchmark['max']:,.0f})",
                    score=item.amount / benchmark["max"],
                    evidence=f"Category: {item.category.value}"
                ))

        return flags

    def _check_fraud_patterns(self, bill_data: ExtractedBillData) -> list[FraudFlag]:
        """Detect known fraud patterns."""
        flags = []
        
        # Pattern 1: Duplicate billing codes / descriptions
        descriptions = [item.description.lower().strip() for item in bill_data.line_items]
        desc_counts = Counter(descriptions)
        for desc, count in desc_counts.items():
            if count > 1:
                flags.append(FraudFlag(
                    flag_type="duplicate",
                    severity="high",
                    description=f"Duplicate billing: '{desc}' appears {count} times",
                    score=float(count),
                    evidence=f"Item '{desc}' billed {count} times"
                ))
        
        # Pattern 2: Suspicious item combinations
        categories = set(item.category for item in bill_data.line_items)
        if BillItemCategory.ROOM_CHARGES not in categories and BillItemCategory.ICU_CHARGES not in categories:
            if any(c in categories for c in [BillItemCategory.SURGERY, BillItemCategory.PROCEDURE]):
                # Surgery/procedure without room charges is unusual
                if bill_data.total_amount > 50000:
                    flags.append(FraudFlag(
                        flag_type="pattern",
                        severity="medium",
                        description="Surgery/procedure billed without room charges (unusual for inpatient)",
                        score=0.6,
                        evidence="Typically, surgical procedures require hospital stay"
                    ))
        
        # Pattern 3: Bill total discrepancy (>25% after reconciliation)
        if bill_data.line_items:
            computed_total = sum(item.amount for item in bill_data.line_items)
            if bill_data.total_amount > 0:
                discrepancy = abs(computed_total - bill_data.total_amount)
                if discrepancy > bill_data.total_amount * 0.25:  # >25% threshold
                    flags.append(FraudFlag(
                        flag_type="anomaly",
                        severity="medium",
                        description=f"Bill total discrepancy: computed ₹{computed_total:,.0f} vs "
                                   f"stated ₹{bill_data.total_amount:,.0f}",
                        score=discrepancy / max(bill_data.total_amount, 1),
                        evidence=f"Difference: ₹{discrepancy:,.0f} ({discrepancy/max(bill_data.total_amount,1)*100:.1f}%)"
                    ))
        
        # Pattern 4: All round thousands (flag only if >5 items)
        if len(bill_data.line_items) > 5:
            round_count = sum(
                1 for item in bill_data.line_items
                if item.amount > 0 and item.amount == int(item.amount) and item.amount % 1000 == 0
            )
            if round_count == len(bill_data.line_items):
                flags.append(FraudFlag(
                    flag_type="pattern",
                    severity="low",
                    description="All line items are round thousands — potential fabrication indicator",
                    score=0.4,
                    evidence=f"All {len(bill_data.line_items)} items are exact multiples of ₹1,000"
                ))

        # Pattern 5: Unusually high total
        if bill_data.total_amount > 2_000_000:
            flags.append(FraudFlag(
                flag_type="anomaly",
                severity="medium",
                description=f"Very high claim amount: ₹{bill_data.total_amount:,.0f}",
                score=bill_data.total_amount / 1_000_000,
                evidence="Claims above ₹20 lakhs require additional scrutiny"
            ))

        return flags

    def _check_duplicates(
        self,
        bill_data: ExtractedBillData,
        historical_claims: list[dict],
    ) -> list[FraudFlag]:
        """Check for duplicate claims against historical data."""
        flags = []
        
        for claim in historical_claims:
            # Check for exact match on amount and hospital
            if (claim.get("total_amount") == bill_data.total_amount and
                claim.get("hospital_name") == bill_data.hospital_name and
                claim.get("bill_number") == bill_data.bill_number):
                flags.append(FraudFlag(
                    flag_type="duplicate",
                    severity="critical",
                    description="Exact duplicate claim detected",
                    score=1.0,
                    evidence=f"Matches claim from {claim.get('date', 'unknown date')} "
                            f"at {bill_data.hospital_name}"
                ))
            
            # Check for similar claims (same hospital, similar amount)
            elif (claim.get("hospital_name") == bill_data.hospital_name and
                  claim.get("total_amount") and
                  abs(claim["total_amount"] - bill_data.total_amount) < bill_data.total_amount * 0.05):
                flags.append(FraudFlag(
                    flag_type="duplicate",
                    severity="high",
                    description="Very similar claim exists in history",
                    score=0.8,
                    evidence=f"Similar amount at same hospital on {claim.get('date', 'unknown date')}"
                ))
        
        return flags

    def _ml_anomaly_score(self, bill_data: ExtractedBillData) -> float:
        """Calculate ML-based anomaly score using Isolation Forest."""
        if not SKLEARN_AVAILABLE or not self.isolation_forest:
            return 0.0
        
        try:
            # Extract features
            total_amount = bill_data.total_amount or 0
            num_items = len(bill_data.line_items)
            
            # Calculate price ratio
            price_ratios = []
            for item in bill_data.line_items:
                benchmark = PRICE_BENCHMARKS.get(item.category)
                if benchmark and benchmark["median"] > 0:
                    price_ratios.append(item.amount / benchmark["median"])
            avg_price_ratio = np.mean(price_ratios) if price_ratios else 1.0
            
            # Estimate stay duration from room charges
            stay_days = 1
            for item in bill_data.line_items:
                if item.category in (BillItemCategory.ROOM_CHARGES, BillItemCategory.ICU_CHARGES):
                    stay_days = max(item.quantity or 1, stay_days)
            
            # Category diversity
            categories = set(item.category for item in bill_data.line_items)
            category_diversity = len(categories)
            
            features = np.array([[
                total_amount,
                num_items,
                avg_price_ratio,
                stay_days,
                category_diversity
            ]])
            
            features_scaled = self.scaler.transform(features)
            score = self.isolation_forest.decision_function(features_scaled)[0]
            
            # Convert to 0-1 range (more negative = more anomalous)
            anomaly_score = max(0.0, min(1.0, (0.5 - score)))
            
            return float(anomaly_score)
            
        except Exception as e:
            logger.warning(f"ML anomaly scoring failed: {e}")
            return 0.0

    def _calculate_risk_score(self, flags: list[FraudFlag], ml_score: float) -> float:
        """Calculate overall fraud risk score (0-100)."""
        if not flags and ml_score < 0.3:
            return max(ml_score * 20, 0)
        
        severity_weights = {
            "critical": 40,
            "high": 25,
            "medium": 15,
            "low": 5,
        }
        
        weighted_sum = sum(
            severity_weights.get(flag.severity, 10) for flag in flags
        )
        
        # ML component (20% weight)
        ml_component = ml_score * 20
        
        # Cap at 100
        return min(weighted_sum + ml_component, 100.0)

    def _build_summary(self, flags: list[FraudFlag], score: float, level: str) -> str:
        """Build human-readable fraud analysis summary."""
        if not flags:
            return f"No fraud indicators detected. Risk Score: {score:.1f}/100 ({level})"
        
        summary = f"Fraud Risk Score: {score:.1f}/100 ({level})\n"
        summary += f"Detected {len(flags)} potential indicator(s):\n"
        
        for flag in flags:
            icon = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}.get(flag.severity, "•")
            summary += f"  {icon} [{flag.severity.upper()}] {flag.description}\n"
        
        return summary
