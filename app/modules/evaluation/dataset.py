"""
AegisClaim AI - Synthetic Dataset Generator
Generates realistic insurance claims for evaluation.
"""
import json
import random
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aegisclaim.evaluation.dataset")

# Realistic hospital names
HOSPITALS = [
    "Apollo Multispeciality Hospital", "Fortis Memorial Research Institute",
    "Max Super Speciality Hospital", "AIIMS Medical Centre",
    "Medanta - The Medicity", "Kokilaben Dhirubhai Ambani Hospital",
    "Sir Ganga Ram Hospital", "Narayana Health City",
    "Manipal Hospital Whitefield", "Artemis Hospital Gurgaon",
    "Hospital General de México", "Hôpital Saint-Louis Paris",
    "Charité Universitätsmedizin Berlin", "राम मनोहर लोहिया अस्पताल",
]

# Realistic patient names
PATIENT_NAMES = [
    "Rajesh Kumar", "Priya Sharma", "Mohammed Khalil", "Ananya Reddy",
    "Vikram Singh", "Lakshmi Devi", "Arjun Patel", "Meena Kumari",
    "John Smith", "María García", "Jean-Pierre Moreau", "Zhang Wei",
    "Suresh Nair", "Fatima Begum", "Amrita Das", "Ramesh Gupta",
    "Sanjay Verma", "Pooja Mishra", "Abdul Rahman", "Kavitha Subramanian",
]

# Procedures and costs
PROCEDURES = {
    "room_charges": [
        ("General Ward (per day)", 1500, 4000, "room_charges"),
        ("Semi-Private Room (per day)", 3000, 8000, "room_charges"),
        ("Private Room (per day)", 6000, 15000, "room_charges"),
        ("Deluxe Suite (per day)", 15000, 35000, "room_charges"),
    ],
    "icu_charges": [
        ("ICU Charges (per day)", 10000, 40000, "icu_charges"),
        ("NICU Charges (per day)", 8000, 30000, "icu_charges"),
    ],
    "surgeries": [
        ("Appendectomy", 30000, 80000, "surgery"),
        ("Cholecystectomy (Gallbladder)", 50000, 150000, "surgery"),
        ("Coronary Artery Bypass (CABG)", 200000, 500000, "surgery"),
        ("Total Knee Replacement", 150000, 400000, "surgery"),
        ("Cataract Surgery", 20000, 60000, "surgery"),
        ("Hernia Repair", 25000, 70000, "surgery"),
        ("Caesarean Section", 40000, 120000, "surgery"),
        ("Angioplasty with Stent", 100000, 350000, "surgery"),
    ],
    "diagnostics": [
        ("MRI Brain", 5000, 15000, "diagnostic"),
        ("CT Scan Abdomen", 3000, 10000, "diagnostic"),
        ("X-Ray Chest", 300, 1500, "diagnostic"),
        ("Ultrasound Abdomen", 1000, 3000, "diagnostic"),
        ("PET CT Scan", 15000, 40000, "diagnostic"),
        ("ECG", 200, 800, "diagnostic"),
        ("Echocardiogram", 2000, 5000, "diagnostic"),
    ],
    "lab_tests": [
        ("Complete Blood Count (CBC)", 200, 800, "laboratory"),
        ("Lipid Profile", 300, 1200, "laboratory"),
        ("Liver Function Test (LFT)", 400, 1500, "laboratory"),
        ("Kidney Function Test (KFT)", 400, 1500, "laboratory"),
        ("HbA1c", 300, 1000, "laboratory"),
        ("Thyroid Profile", 400, 1500, "laboratory"),
        ("Blood Culture", 500, 2000, "laboratory"),
    ],
    "medications": [
        ("IV Antibiotics (course)", 2000, 15000, "medication"),
        ("Pain Management", 500, 5000, "medication"),
        ("Intravenous Fluids", 500, 3000, "medication"),
        ("Anticoagulants", 1000, 8000, "medication"),
        ("Anesthesia Charges", 5000, 25000, "medication"),
    ],
    "consultations": [
        ("Physician Consultation", 500, 3000, "consultation"),
        ("Specialist Consultation", 1000, 5000, "consultation"),
        ("Surgeon Fees", 10000, 50000, "consultation"),
        ("Anesthetist Fees", 5000, 25000, "consultation"),
    ],
    "exclusions": [
        ("Cosmetic Surgery - Rhinoplasty", 50000, 200000, "surgery"),
        ("Hair Transplant", 30000, 150000, "procedure"),
        ("LASIK Eye Surgery", 25000, 80000, "surgery"),
        ("Dental Implants", 15000, 60000, "procedure"),
        ("Weight Loss Surgery (Bariatric)", 100000, 400000, "surgery"),
        ("Infertility Treatment (IVF)", 80000, 300000, "procedure"),
    ]
}

DIAGNOSES = {
    "valid": [
        "Acute Appendicitis", "Pneumonia", "Myocardial Infarction",
        "Fracture of Left Femur", "Acute Cholecystitis", "Dengue Fever",
        "Urinary Tract Infection", "Viral Encephalitis", "Intestinal Obstruction",
        "Acute Pancreatitis", "Cerebral Stroke", "Deep Vein Thrombosis",
    ],
    "pre_existing": [
        "Type 2 Diabetes Mellitus", "Essential Hypertension",
        "Chronic Kidney Disease", "Coronary Artery Disease",
        "Chronic Obstructive Pulmonary Disease", "Rheumatoid Arthritis",
    ],
    "excluded": [
        "Cosmetic Enhancement", "Elective Aesthetic Surgery",
        "Obesity Management", "Infertility Treatment",
    ]
}


def generate_synthetic_dataset(
    num_claims: int = 200,
    output_path: str = "data/synthetic/claims_dataset.json"
) -> list[dict]:
    """
    Generate a synthetic dataset of insurance claims.
    
    Distribution:
    - 60% valid claims (should be approved)
    - 25% invalid claims (should be rejected)
    - 15% edge cases (borderline, needs review)
    """
    random.seed(42)
    claims = []
    
    valid_count = int(num_claims * 0.60)
    invalid_count = int(num_claims * 0.25)
    edge_count = num_claims - valid_count - invalid_count

    # Generate valid claims
    for i in range(valid_count):
        claim = _generate_valid_claim(i)
        claims.append(claim)
    
    # Generate invalid claims
    for i in range(invalid_count):
        claim = _generate_invalid_claim(valid_count + i)
        claims.append(claim)
    
    # Generate edge cases
    for i in range(edge_count):
        claim = _generate_edge_case(valid_count + invalid_count + i)
        claims.append(claim)
    
    # Shuffle
    random.shuffle(claims)
    
    # Save to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(claims, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Generated {len(claims)} synthetic claims → {output_path}")
    return claims


def _generate_valid_claim(idx: int) -> dict:
    """Generate a claim that should be approved."""
    stay_days = random.randint(1, 15)
    
    # Select room within policy limits
    room = random.choice(PROCEDURES["room_charges"][:2])  # General/Semi-private
    room_cost = random.randint(room[1], room[2]) * stay_days
    
    # Add surgery
    surgery = random.choice(PROCEDURES["surgeries"])
    surgery_cost = random.randint(surgery[1], surgery[2])
    
    # Add diagnostics
    num_diagnostics = random.randint(1, 3)
    diagnostics = random.sample(PROCEDURES["diagnostics"], num_diagnostics)
    diag_costs = [(d[0], random.randint(d[1], d[2]), d[3]) for d in diagnostics]
    
    # Add labs
    num_labs = random.randint(2, 5)
    labs = random.sample(PROCEDURES["lab_tests"], min(num_labs, len(PROCEDURES["lab_tests"])))
    lab_costs = [(l[0], random.randint(l[1], l[2]), l[3]) for l in labs]
    
    # Add medications
    med = random.choice(PROCEDURES["medications"])
    med_cost = random.randint(med[1], med[2])
    
    # Add consultation
    consult = random.choice(PROCEDURES["consultations"])
    consult_cost = random.randint(consult[1], consult[2])
    
    # Build line items
    line_items = [
        {"description": room[0], "category": room[3], "amount": room_cost, "quantity": stay_days},
        {"description": surgery[0], "category": surgery[3], "amount": surgery_cost},
    ]
    for d_name, d_cost, d_cat in diag_costs:
        line_items.append({"description": d_name, "category": d_cat, "amount": d_cost})
    for l_name, l_cost, l_cat in lab_costs:
        line_items.append({"description": l_name, "category": l_cat, "amount": l_cost})
    line_items.append({"description": med[0], "category": med[3], "amount": med_cost})
    line_items.append({"description": consult[0], "category": consult[3], "amount": consult_cost})
    
    total = sum(item["amount"] for item in line_items)
    
    return {
        "claim_id": f"CLM-V-{idx:04d}",
        "patient_name": random.choice(PATIENT_NAMES),
        "hospital_name": random.choice(HOSPITALS),
        "diagnosis": random.choice(DIAGNOSES["valid"]),
        "line_items": line_items,
        "total_amount": total,
        "policy_limit": max(total * 1.5, 500000),
        "room_rent_limit_per_day": 8000,
        "copay_percentage": random.choice([0, 10, 20]),
        "waiting_period_months": 0,
        "expected_decision": "APPROVED",
        "claim_type": "valid",
        "stay_days": stay_days,
    }


def _generate_invalid_claim(idx: int) -> dict:
    """Generate a claim that should be rejected."""
    reason = random.choice(["exclusion", "over_limit", "pre_existing", "room_rent_excess"])
    stay_days = random.randint(1, 10)
    
    if reason == "exclusion":
        # Use excluded procedure
        procedure = random.choice(PROCEDURES["exclusions"])
        proc_cost = random.randint(procedure[1], procedure[2])
        line_items = [
            {"description": procedure[0], "category": procedure[3], "amount": proc_cost},
        ]
        total = proc_cost
        diagnosis = random.choice(DIAGNOSES["excluded"])
        
    elif reason == "over_limit":
        # Total exceeds policy limit significantly
        surgery = random.choice(PROCEDURES["surgeries"][-3:])  # Expensive ones
        surgery_cost = random.randint(surgery[1], surgery[2]) * 3  # Triple the cost
        room = PROCEDURES["room_charges"][3]  # Deluxe suite
        room_cost = random.randint(room[1], room[2]) * stay_days
        
        line_items = [
            {"description": room[0], "category": room[3], "amount": room_cost, "quantity": stay_days},
            {"description": surgery[0], "category": surgery[3], "amount": surgery_cost},
        ]
        total = room_cost + surgery_cost
        diagnosis = random.choice(DIAGNOSES["valid"])
        
    elif reason == "pre_existing":
        surgery = random.choice(PROCEDURES["surgeries"])
        surgery_cost = random.randint(surgery[1], surgery[2])
        line_items = [
            {"description": surgery[0], "category": surgery[3], "amount": surgery_cost},
        ]
        total = surgery_cost
        diagnosis = random.choice(DIAGNOSES["pre_existing"])
        
    else:  # room_rent_excess
        room = PROCEDURES["room_charges"][3]  # Deluxe suite (expensive)
        room_cost = random.randint(20000, 35000) * stay_days
        line_items = [
            {"description": room[0], "category": room[3], "amount": room_cost, "quantity": stay_days},
        ]
        total = room_cost
        diagnosis = random.choice(DIAGNOSES["valid"])
    
    return {
        "claim_id": f"CLM-I-{idx:04d}",
        "patient_name": random.choice(PATIENT_NAMES),
        "hospital_name": random.choice(HOSPITALS),
        "diagnosis": diagnosis,
        "line_items": line_items,
        "total_amount": total,
        "policy_limit": 300000 if reason == "over_limit" else 500000,
        "room_rent_limit_per_day": 5000,
        "copay_percentage": 20,
        "waiting_period_months": 48 if reason == "pre_existing" else 0,
        "expected_decision": "REJECTED",
        "claim_type": "invalid",
        "rejection_reason": reason,
        "stay_days": stay_days,
    }


def _generate_edge_case(idx: int) -> dict:
    """Generate borderline/ambiguous claims."""
    edge_type = random.choice([
        "borderline_amount", "mixed_items", "missing_data", "ambiguous_diagnosis"
    ])
    stay_days = random.randint(1, 7)
    
    if edge_type == "borderline_amount":
        # Amount very close to policy limit
        policy_limit = random.choice([300000, 500000])
        target_amount = policy_limit * random.uniform(0.95, 1.05)
        
        surgery = random.choice(PROCEDURES["surgeries"])
        surgery_cost = target_amount * 0.7
        room = random.choice(PROCEDURES["room_charges"][:2])
        room_cost = target_amount * 0.3
        
        line_items = [
            {"description": room[0], "category": room[3], "amount": round(room_cost), "quantity": stay_days},
            {"description": surgery[0], "category": surgery[3], "amount": round(surgery_cost)},
        ]
        total = round(target_amount)
        diagnosis = random.choice(DIAGNOSES["valid"])
        
    elif edge_type == "mixed_items":
        # Mix of valid and potentially excluded items
        valid_proc = random.choice(PROCEDURES["surgeries"])
        valid_cost = random.randint(valid_proc[1], valid_proc[2])
        
        # Add a borderline item
        borderline_items = [
            ("Alternative Medicine Consultation", 5000, 15000, "consultation"),
            ("Physiotherapy (Extended)", 3000, 10000, "procedure"),
            ("Experimental Drug Trial", 10000, 50000, "medication"),
        ]
        border = random.choice(borderline_items)
        border_cost = random.randint(border[1], border[2])
        
        line_items = [
            {"description": valid_proc[0], "category": valid_proc[3], "amount": valid_cost},
            {"description": border[0], "category": border[3], "amount": border_cost},
        ]
        total = valid_cost + border_cost
        diagnosis = random.choice(DIAGNOSES["valid"])
        
    elif edge_type == "missing_data":
        surgery = random.choice(PROCEDURES["surgeries"])
        surgery_cost = random.randint(surgery[1], surgery[2])
        line_items = [
            {"description": surgery[0], "category": surgery[3], "amount": surgery_cost},
        ]
        total = surgery_cost
        diagnosis = None  # Missing diagnosis
        
    else:  # ambiguous_diagnosis
        surgery = random.choice(PROCEDURES["surgeries"])
        surgery_cost = random.randint(surgery[1], surgery[2])
        line_items = [
            {"description": surgery[0], "category": surgery[3], "amount": surgery_cost},
        ]
        total = surgery_cost
        diagnosis = "Condition under investigation - provisional"
    
    return {
        "claim_id": f"CLM-E-{idx:04d}",
        "patient_name": random.choice(PATIENT_NAMES),
        "hospital_name": random.choice(HOSPITALS),
        "diagnosis": diagnosis,
        "line_items": line_items,
        "total_amount": round(total),
        "policy_limit": 500000,
        "room_rent_limit_per_day": 5000,
        "copay_percentage": 10,
        "waiting_period_months": 0,
        "expected_decision": "NEEDS_REVIEW",
        "claim_type": "edge_case",
        "edge_type": edge_type,
        "stay_days": stay_days,
    }
