"""
AegisClaim AI - Live Pipeline E2E Test
Tests the full claim processing pipeline using the generated sample PDFs.
"""
import requests
import json
import os
import sys
import time

BASE_URL = "http://127.0.0.1:8000"
SAMPLES  = os.path.join(os.path.dirname(__file__), "..", "data", "samples")

BILL_PDF   = os.path.join(SAMPLES, "Apollo_Hospital_Bill_Rahul_Sharma.pdf")
POLICY_PDF = os.path.join(SAMPLES, "StarHealth_Comprehensive_Policy_50pg.pdf")

def separator(title=""):
    print("\n" + "═" * 60)
    if title:
        print(f"  {title}")
        print("─" * 60)

def check(label, condition, detail=""):
    icon = "✅" if condition else "❌"
    print(f"  {icon} {label}" + (f"  →  {detail}" if detail else ""))
    return condition

def run():
    passed = 0
    failed = 0

    # ── Health check ───────────────────────────────────────────────────────────
    separator("1. Health Check")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if check("Server reachable", r.status_code == 200, str(r.status_code)):
            passed += 1
    except Exception as e:
        print(f"  ❌ Cannot reach server: {e}")
        print("  ⚠️  Start the server first: uvicorn app.main:app --port 8000")
        sys.exit(1)

    # ── File check ────────────────────────────────────────────────────────────
    separator("2. Sample File Check")
    bill_ok   = check("Bill PDF exists",   os.path.exists(BILL_PDF),   BILL_PDF)
    policy_ok = check("Policy PDF exists", os.path.exists(POLICY_PDF), POLICY_PDF)
    if bill_ok:   passed += 1
    else:         failed += 1
    if policy_ok: passed += 1
    else:         failed += 1

    if not (bill_ok and policy_ok):
        print("\n  Run: python scripts/generate_samples.py")
        sys.exit(1)

    bill_size   = os.path.getsize(BILL_PDF)   / 1024
    policy_size = os.path.getsize(POLICY_PDF) / 1024
    print(f"  📄 Bill PDF:   {bill_size:.0f} KB")
    print(f"  📄 Policy PDF: {policy_size:.0f} KB")

    # ── Full pipeline ─────────────────────────────────────────────────────────
    separator("3. Full Pipeline Test (OCR → RAG → Decision → Explainability)")
    print("  ⏳ Processing claim... (may take 10-30 seconds)")
    t0 = time.time()

    with open(BILL_PDF, "rb") as bill_f, open(POLICY_PDF, "rb") as policy_f:
        r = requests.post(
            f"{BASE_URL}/api/v1/claims/process",
            files={
                "bill":   ("bill.pdf",   bill_f,   "application/pdf"),
                "policy": ("policy.pdf", policy_f, "application/pdf"),
            },
            data={"language": "eng"},
            timeout=120,
        )

    elapsed = time.time() - t0
    print(f"  ⏱  Response time: {elapsed:.1f}s")

    if not check("HTTP 200 OK", r.status_code == 200, str(r.status_code)):
        print(f"  Response: {r.text[:500]}")
        failed += 1
        separator("RESULT")
        print(f"  ❌ Pipeline test failed at HTTP level.")
        sys.exit(1)

    passed += 1
    data = r.json()

    # ── Response structure ────────────────────────────────────────────────────
    separator("4. Response Structure Validation")
    checks = [
        ("claim_id present",          bool(data.get("claim_id"))),
        ("errors is empty",           len(data.get("errors", [])) == 0),
        ("ocr_result present",        bool(data.get("ocr_result"))),
        ("explanation present",       bool(data.get("explanation"))),
        ("fraud_analysis present",    bool(data.get("fraud_analysis"))),
        ("simulation present",        bool(data.get("simulation"))),
        ("processing_time present",   data.get("processing_time_ms", 0) > 0),
    ]
    for label, cond in checks:
        if check(label, cond):
            passed += 1
        else:
            failed += 1

    errors = data.get("errors", [])
    warnings = data.get("warnings", [])
    if errors:
        print(f"\n  ⚠️  Errors:")
        for e in errors: print(f"     • {e}")
    if warnings:
        print(f"  ℹ️  Warnings ({len(warnings)}):")
        for w in warnings[:3]: print(f"     • {w}")

    # ── OCR ──────────────────────────────────────────────────────────────────
    separator("5. OCR Extraction")
    ocr = data.get("ocr_result", {})
    bill = ocr.get("bill_data", {})
    items = bill.get("line_items", [])
    total = bill.get("total_amount", 0)
    conf  = bill.get("extraction_confidence", 0)

    if check("Patient name extracted",   bool(bill.get("patient_name")),         str(bill.get("patient_name"))):  passed += 1
    else: failed += 1
    if check("Hospital name extracted",  bool(bill.get("hospital_name")),        str(bill.get("hospital_name"))): passed += 1
    else: failed += 1
    if check("Diagnosis extracted",      bool(bill.get("diagnosis")),            str(bill.get("diagnosis"))):     passed += 1
    else: failed += 1
    if check("Line items found ≥ 5",    len(items) >= 5,                         f"{len(items)} items"):          passed += 1
    else: failed += 1
    if check("Total amount > 0",        total > 0,                               f"₹{total:,.0f}"):               passed += 1
    else: failed += 1
    if check("Confidence > 0.3",        conf > 0.3,                             f"{conf:.0%}"):                  passed += 1
    else: failed += 1

    print(f"\n  📋 Line Items Extracted ({len(items)}):")
    for i, item in enumerate(items[:6], 1):
        print(f"     {i}. {item['description'][:40]:<40} ₹{item['amount']:>10,.2f}  [{item.get('category','?')}]")
    if len(items) > 6:
        print(f"     ... and {len(items)-6} more")

    # ── Decision ──────────────────────────────────────────────────────────────
    separator("6. Decision Engine")
    exp = data.get("explanation", {})
    decision   = exp.get("decision", "UNKNOWN")
    confidence = exp.get("confidence", 0)
    approved   = exp.get("total_approved_amount", 0)
    billed     = exp.get("total_bill_amount", 0)
    conf_pct   = confidence * 100 if confidence <= 1.0 else confidence

    print(f"  🏛  Decision:    {decision}")
    print(f"  🎯  Confidence:  {conf_pct:.1f}%")
    print(f"  💰  Billed:      ₹{billed:,.2f}")
    print(f"  ✅  Approved:    ₹{approved:,.2f}")
    if billed > 0:
        print(f"  📊  Coverage:    {approved/billed*100:.1f}%")

    if check("Decision is valid", decision in ("APPROVED","REJECTED","PARTIALLY_APPROVED","NEEDS_REVIEW"), decision): passed += 1
    else: failed += 1
    if check("Confidence in [0,1]", 0 <= confidence <= 1.0, f"{confidence:.3f}"): passed += 1
    else: failed += 1
    if check("Approved amount ≥ 0",  approved >= 0, f"₹{approved:,.0f}"): passed += 1
    else: failed += 1

    # ── Citations ─────────────────────────────────────────────────────────────
    separator("7. Citation Validation (Page + Paragraph)")
    cited = exp.get("cited_clauses", [])
    rejection_cit = exp.get("rejection_citations", [])
    item_exps = exp.get("item_explanations", [])

    print(f"  📌 Total citations:    {len(cited)}")
    print(f"  🚫 Rejection citations: {len(rejection_cit)}")
    print(f"  📝 Item explanations:  {len(item_exps)}")

    if check("At least 1 citation", len(cited) >= 1, f"{len(cited)}"): passed += 1
    else: failed += 1

    page_pinned = [c for c in cited if c.get("page")]
    if check("Citations have page numbers", len(page_pinned) >= 1, f"{len(page_pinned)}/{len(cited)}"): passed += 1
    else: failed += 1

    print(f"\n  📖 Sample Citations:")
    for c in cited[:3]:
        pg  = c.get("page", "?")
        par = c.get("paragraph", "?")
        sec = c.get("section", "general")
        txt = (c.get("clause_text") or "")[:80]
        print(f"     Page {pg}, Para {par} [{sec}]: {txt}...")

    # ── Fraud ─────────────────────────────────────────────────────────────────
    separator("8. Fraud Detection")
    fraud = data.get("fraud_analysis", {})
    score = fraud.get("fraud_risk_score", 0)
    level = fraud.get("risk_level", "UNKNOWN")
    flags = fraud.get("flags", [])

    print(f"  🛡  Risk Score: {score:.1f}/100  |  Level: {level}")
    print(f"  🔍 Flags: {len(flags)}")
    for f in flags[:3]:
        print(f"     • [{f.get('severity','?').upper()}] {f.get('description','')[:70]}")

    if check("Fraud score in [0,100]", 0 <= score <= 100, str(score)): passed += 1
    else: failed += 1
    if check("Risk level valid", level in ("LOW","MEDIUM","HIGH","CRITICAL"), level): passed += 1
    else: failed += 1

    # ── Simulation ────────────────────────────────────────────────────────────
    separator("9. What-If Simulation")
    sim = data.get("simulation", {})
    scenarios  = sim.get("scenarios", [])
    is_success = sim.get("status") in ("success", "not_needed")

    print(f"  🔮 Status: {sim.get('status', '?')}")
    print(f"  📋 Scenarios: {len(scenarios)}")
    for i, s in enumerate(scenarios[:3], 1):
        gain = s.get("potential_additional_approval", 0)
        diff = s.get("difficulty", "?")
        print(f"     {i}. {s.get('title','?'):<40} +₹{gain:,.0f}  [{diff}]")

    if check("Simulation returned valid status", is_success, sim.get("status")): passed += 1
    else: failed += 1

    # ── Analytics API ─────────────────────────────────────────────────────────
    separator("10. Analytics API")
    r2 = requests.get(f"{BASE_URL}/api/v1/analytics/stats", timeout=10)
    if check("Analytics endpoint OK", r2.status_code == 200, str(r2.status_code)):
        passed += 1
        stats = r2.json()
        print(f"  📊 Total Claims:   {stats.get('total_claims', 0)}")
        print(f"  ✅ Approval Rate:  {stats.get('approval_rate', 0):.1f}%")
        print(f"  💰 Total Billed:   ₹{stats.get('total_billed', 0):,.0f}")
    else:
        failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    separator("TEST SUMMARY")
    total_tests = passed + failed
    pct = (passed / total_tests * 100) if total_tests > 0 else 0
    print(f"  Tests Passed: {passed}/{total_tests} ({pct:.0f}%)")
    print()
    if failed == 0:
        print("  🎉 ALL TESTS PASSED — Pipeline is production-ready!")
    elif pct >= 80:
        print("  ✅ MOSTLY PASSING — Minor issues detected, review warnings above.")
    else:
        print("  ⚠️  ISSUES DETECTED — review failures above before submission.")
    print()

    # Print full JSON for inspection
    out_path = os.path.join(SAMPLES, "last_test_result.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Full response saved → {out_path}")

    separator()
    return failed == 0

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
