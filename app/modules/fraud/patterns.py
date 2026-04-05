"""
AegisClaim AI - Known Fraud Patterns
Database of known insurance fraud patterns and indicators.
"""

# Medical billing fraud patterns
FRAUD_PATTERNS = {
    "upcoding": {
        "description": "Billing for more expensive services than provided",
        "indicators": [
            "Procedure code upgraded to higher-cost version",
            "ICU charges when patient was in general ward",
            "Specialist consultation billed for routine checkup"
        ],
        "severity": "high"
    },
    "unbundling": {
        "description": "Separating procedures that should be billed together at lower cost",
        "indicators": [
            "Multiple related procedure codes billed separately",
            "Lab tests billed individually instead of as a panel",
            "Surgical procedure components billed separately"
        ],
        "severity": "high"
    },
    "phantom_billing": {
        "description": "Billing for services never rendered",
        "indicators": [
            "Services billed on dates patient was not admitted",
            "Billing for procedures inconsistent with diagnosis",
            "Excessive number of consultations in short period"
        ],
        "severity": "critical"
    },
    "inflated_billing": {
        "description": "Charges significantly above market rates",
        "indicators": [
            "Room charges > 3x average for hospital class",
            "Medication prices > 2x MRP",
            "Consumable charges disproportionate to procedure"
        ],
        "severity": "high"
    },
    "fabricated_diagnosis": {
        "description": "Fake or exaggerated diagnosis to justify claims",
        "indicators": [
            "Diagnosis inconsistent with treatment",
            "Multiple unrelated serious diagnoses",
            "Rapidly escalating severity without medical basis"
        ],
        "severity": "critical"
    },
    "kickback_scheme": {
        "description": "Unnecessary referrals and tests for financial gain",
        "indicators": [
            "Multiple expensive diagnostics for minor complaints",
            "Referral to specific high-cost providers",
            "Repeated similar tests within short timeframe"
        ],
        "severity": "high"
    }
}

# Procedure-diagnosis compatibility matrix (simplified)
COMPATIBLE_PROCEDURES = {
    "cardiac": ["heart", "cardiac", "chest pain", "angina", "myocardial", "coronary"],
    "orthopedic": ["fracture", "bone", "joint", "spine", "arthritis", "knee", "hip"],
    "neurological": ["brain", "nerve", "headache", "seizure", "stroke", "paralysis"],
    "gastrointestinal": ["stomach", "liver", "intestine", "gastric", "abdominal"],
    "respiratory": ["lung", "breathing", "asthma", "pneumonia", "bronchitis"],
    "urological": ["kidney", "bladder", "urinary", "renal", "prostate"],
}
