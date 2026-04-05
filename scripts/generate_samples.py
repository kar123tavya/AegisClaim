"""
AegisClaim AI - Synthetic Sample Data Generator
Generates a realistic 50-page insurance policy PDF and a detailed hospital bill PDF
for comprehensive end-to-end pipeline testing.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "samples")
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = A4
styles = getSampleStyleSheet()

# ── Custom styles ──────────────────────────────────────────────────────────────
TITLE    = ParagraphStyle("TITLE",    parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#0f172a"), spaceAfter=8, alignment=TA_CENTER)
H1       = ParagraphStyle("H1",       parent=styles["Heading1"], fontSize=13, textColor=colors.HexColor("#1e3a5f"), spaceBefore=14, spaceAfter=6)
H2       = ParagraphStyle("H2",       parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#2563eb"), spaceBefore=10, spaceAfter=4)
BODY     = ParagraphStyle("BODY",     parent=styles["Normal"],   fontSize=9.5, leading=14, spaceAfter=5, alignment=TA_JUSTIFY)
CLAUSE   = ParagraphStyle("CLAUSE",   parent=styles["Normal"],   fontSize=9,   leading=13, leftIndent=18, spaceAfter=4, alignment=TA_JUSTIFY)
BOLD     = ParagraphStyle("BOLD",     parent=styles["Normal"],   fontSize=9.5, leading=14, fontName="Helvetica-Bold", spaceAfter=4)
NOTE     = ParagraphStyle("NOTE",     parent=styles["Normal"],   fontSize=8.5, textColor=colors.HexColor("#64748b"), leading=12, spaceAfter=4)
CENTER   = ParagraphStyle("CENTER",   parent=styles["Normal"],   fontSize=9.5, alignment=TA_CENTER, spaceAfter=6)


def sp(n=1): return Spacer(1, n * 0.35 * cm)
def hr(): return HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1"), spaceAfter=6, spaceBefore=6)


# ═══════════════════════════════════════════════════════════════════════════════
#  50-PAGE INSURANCE POLICY
# ═══════════════════════════════════════════════════════════════════════════════

POLICY_SECTIONS = [
    # (heading, [paragraphs])
    ("PART I – PREAMBLE AND DEFINITIONS", [
        ("1.1 Policy Overview",
         "This Star Health Comprehensive Insurance Policy ('the Policy') is a legally binding contract between Star Health and Allied Insurance Company Limited (hereinafter 'the Insurer') and the Policyholder named in the Schedule. The Policy provides health insurance coverage for hospitalisation, surgical procedures, diagnostic services, and related medical expenses as defined herein, subject to the terms, conditions, exclusions, and waiting periods specified in this document."),
        ("1.2 Scope of Agreement",
         "The Policy is governed by and construed in accordance with the laws of India. Any dispute arising out of or in connection with this Policy shall be subject to the exclusive jurisdiction of courts in the city where the Policy is issued. Regulatory oversight is provided by the Insurance Regulatory and Development Authority of India (IRDAI)."),
        ("1.3 Definitions – A to F",
         "For the purposes of this Policy, the following definitions shall apply: 'Accident' means a sudden, unforeseen, and involuntary event caused by external, visible, and violent means. 'Acute Condition' means a disease, illness, or injury that is likely to respond quickly to treatment. 'Admission' means the formal registration of an Insured Person as an inpatient at a Hospital. 'Age' means the age of the Insured Person as of the last birthday. 'Allopathy' refers to the mainstream system of medical treatment. 'Annual Renewal Premium' means the amount payable to keep the Policy in force for one Policy Year. 'Cashless Facility' means a facility extended by the Insurer to the Insured where the payments of the costs of treatment undergone by the Insured in accordance with the Policy terms and conditions are directly made by the Insurer to the Network Hospital. 'Co-payment' is a cost-sharing requirement under a health insurance policy that provides that the policyholder/insured will bear a specified percentage of the admissible claim amount. 'Congenital Anomaly' refers to a condition that is present since birth, and that is abnormal with reference to the form, structure, or position. 'Day Care Treatment' refers to medical treatment and or surgical procedure which is undertaken under general or local anaesthesia in a Hospital/day care centre in less than 24 hours, which would have otherwise required hospitalisation of more than 24 hours. 'Emergency Care' means management for severe illness or injury which results in symptoms which occur suddenly and unexpectedly, and require immediate care by a medical practitioner to prevent death or serious long-term impairment of the insured person's health. 'Family' includes the Proposer, Spouse, and up to two (2) dependent children below the age of 25 years. 'First Party' means the Policyholder."),
        ("1.4 Definitions – G to P",
         "'Grace Period' refers to the period of time immediately following the premium due date during which a payment can be made to renew or continue a Policy in force without loss of continuity benefits. 'Home Care Treatment' means the medical treatment for a period exceeding three days for an ailment/disease/injury at home with documented evidence of treatment. 'Hospital' means any institution established for in-patient care and day care treatment of diseases and/or injuries and which has been registered as a Hospital with the local authorities. A Hospital must have at minimum: (a) at least 15 in-patient beds in towns having a population of less than 10 lakh; (b) at least 30 in-patient beds in all other places; (c) fully equipped operation theatre of its own; (d) fully qualified nursing staff under its employment round the clock; and (e) fully qualified doctors under its employment round the clock. 'Hospitalisation' means admission in a Hospital for a minimum period of 24 consecutive hours of in-patient care, except for specified Day Care procedures. 'ICU' means the Intensive Care Unit of a Hospital which meets minimum criteria as prescribed. 'Illness' means a sickness or disease or pathological condition leading to the impairment of normal physiological function and requires medical treatment."),
        ("1.5 Definitions – Q to Z",
         "'Network Hospital' means the Hospitals that have been empanelled by the Insurer to provide cashless treatment facility to the Insured Persons. 'Non-Network Hospital' means any Hospital that is not part of the Insurer's network. 'Pre-existing Disease (PED)' means any condition, ailment, injury, or disease that is diagnosed by a Physician within 48 months prior to the effective date of the Policy issued by the Insurer. 'Premium' means the amount payable to the Insurer by the Policyholder to keep the insurance Policy in force. 'Qualified Nurse' means a person who holds a valid registration from the Nursing Council of India or the Nursing Council of any State in India. 'Reasonable and Customary Charges' means the charges for services or supplies, which are the standard charges for the specific provider and consistent with the prevailing charges in the geographical area for identical or similar services. 'Room Rent' means the amount charged per day by a hospital for the cost of the room/bed occupied by the insured during hospitalisation. 'Sum Insured' means the maximum amount payable by the Insurer during the Policy period for claims arising in respect of the Insured Person. 'Treatment' means medical management and includes consultation, investigation, medication, surgery, and hospitalisation."),
    ]),
    ("PART II – COVERAGE BENEFITS", [
        ("2.1 In-Patient Hospitalisation",
         "The Insurer will pay for medical expenses incurred during hospitalisation for a period exceeding 24 consecutive hours. Covered expenses include: room rent and boarding charges as specified in the Schedule; nursing and attendant charges; surgeon, anaesthetist, medical practitioner, consultants, and specialist fees; anaesthesia, blood, oxygen, operation theatre charges; surgical appliances, medicines, drugs and consumables; pathological, diagnostic, X-ray, and other tests and reports; physiotherapy charges directly related to the ailment; and all other medically necessary inpatient charges. Coverage is subject to the Sum Insured stated in the Policy Schedule and all applicable sub-limits."),
        ("2.2 Pre-Hospitalisation Expenses",
         "The Insurer shall reimburse eligible medical expenses incurred during the 30 days immediately preceding the date of hospitalisation, provided such expenses were incurred for the same illness or injury for which the Insured Person was hospitalised. Pre-hospitalisation expenses include outpatient consultation fees, diagnostic tests, prescribed medications, and specialist consultations directly related to the admitting diagnosis."),
        ("2.3 Post-Hospitalisation Expenses",
         "The Insurer shall reimburse eligible medical expenses incurred during the 60 days immediately following the date of discharge from hospitalisation, provided such expenses are directly related to the illness or injury for which the Insured Person was hospitalised. Post-hospitalisation expenses shall be reimbursed up to the limits specified in the Policy Schedule."),
        ("2.4 Day Care Procedures",
         "The Insurer shall cover Day Care Treatment procedures that require less than 24 hours of hospitalisation due to advances in medical technology. A comprehensive list of 540 approved Day Care procedures is maintained in Annexure A of this Policy. These include cataract surgery, chemotherapy, dialysis, lithotripsy, radiation therapy, coronary angiography, and specific endoscopic procedures, among others."),
        ("2.5 Domiciliary Hospitalisation",
         "The Insurer covers medical expenses incurred for Domiciliary Hospitalisation, where a patient is treated at home due to medical necessity (either the condition of the patient does not permit removal to Hospital, or lack of accommodation in a Hospital is certified by the attending doctor). Domiciliary hospitalisation must last for a minimum period of 3 days and must be certified by a Medical Practitioner. Sub-limit: Up to 20% of the Sum Insured per Policy Year."),
        ("2.6 AYUSH Treatment",
         "The Insurer covers inpatient treatment undertaken in a Government Hospital or in any Institute recognised by the Government and/or accredited by the Quality Council of India/National Accreditation Board on Health under Ayurveda, Yoga and Naturopathy, Unani, Siddha, and Homeopathy (AYUSH) systems. Coverage is limited to 20% of the Sum Insured per Policy Year."),
        ("2.7 Organ Donor Expenses",
         "The Insurer will reimburse medical expenses incurred by the organ donor for a major organ transplant (kidney, liver, heart, lungs, pancreas) performed on the Insured Person. Covered expenses include harvesting, storage, and transplantation. Pre-donation screening costs for the donor are not covered."),
        ("2.8 Emergency Air Ambulance",
         "The Insurer shall pay for emergency air ambulance services up to INR 2,50,000 per Policy Year, where air transport is medically necessary due to the critical nature of the patient's condition and inability to be transported by road. Prior authorisation from the Emergency Assistance team is required."),
    ]),
    ("PART III – SUB-LIMITS AND COVERAGE CAPS", [
        ("3.1 Room Rent Limits",
         "Room Rent is limited based on the tier of coverage selected by the Policyholder. For the Standard Plan: Room Rent is capped at 1% of the Sum Insured per day for a single private room. For the Silver Plan: 1.5% of Sum Insured per day. For the Gold Plan: 2% of Sum Insured per day. For the Diamond Plan: Eligible for any room category. Where the rate of room rent actually paid exceeds the applicable limit, all other expenses shall be payable in proportion. For a Sum Insured of INR 3,00,000, the Standard Room Rent limit is INR 3,000 per day. If a patient occupies a room costing INR 5,000 per day, all associated charges (nursing, doctor's fees, etc.) shall be payable in the ratio of 3000:5000 (60%). ICU charges are limited to 2% of Sum Insured per day (INR 6,000 per day for a Sum Insured of INR 3,00,000)."),
        ("3.2 Surgical Sub-Limits",
         "Surgical procedures are classified into four categories: Category A (Major Complex Surgeries — covered up to Sum Insured), Category B (Major Surgeries — covered up to 75% of Sum Insured), Category C (Intermediate Surgeries — covered up to 50% of Sum Insured), and Category D (Minor Surgeries — covered up to 25% of Sum Insured). Anaesthesiologist fees are covered up to 25% of the admissible surgeon's fee. The attending surgeon must be fully qualified and registered with the Medical Council of India."),
        ("3.3 Cataract Surgery Limit",
         "Cataract surgery (including cost of lens) is limited to INR 40,000 per eye (INR 80,000 for both eyes) per Policy Year. If both eyes are operated in the same year, the combined limit applies. Premium type of lenses (e.g. multifocal, toric) are covered only up to the sub-limit applicable to standard monofocal lenses (INR 20,000 per lens); the differential cost is payable by the Insured."),
        ("3.4 Physiotherapy and Rehabilitation",
         "Physiotherapy undertaken as an inpatient is covered up to 14 sessions per hospitalisation. Post-discharge physiotherapy is covered during the 60-day follow-up period up to INR 10,000 per Policy Year. Occupational therapy, recreational therapy, and vocational rehabilitation are not covered."),
        ("3.5 Prosthetics and Implants",
         "Internal prostheses (e.g. knee/hip implants, cardiac stents, cochlear implants) are covered at actuals, subject to reasonable and customary charges as determined by the Insurer. External prostheses (limbs, hearing aids, spectacles, contact lenses, dentures) are excluded from coverage. Cosmetic implants are not covered. Specific implants may be subject to separate sub-limits as specified in the Policy Schedule."),
        ("3.6 Mental Health Coverage",
         "Mental health disorders requiring hospitalisation (including substance use disorders) are covered as per the Mental Healthcare Act 2017 guidelines, up to 20% of the Sum Insured per Policy Year. Outpatient psychiatric consultations are not covered under this policy."),
        ("3.7 Maternity Benefit",
         "Maternity benefits apply only to Gold and Diamond Plans. Coverage includes normal delivery (up to INR 50,000) and caesarean section (up to INR 70,000). Maternity coverage is subject to a 24-month waiting period from the date of policy inception. New-born baby care is covered from birth up to 90 days. Complications of maternity, ectopic pregnancy (treated as medical emergency), and medically advised termination of pregnancy are covered up to the maternity sub-limit."),
    ]),
    ("PART IV – EXCLUSIONS", [
        ("4.1 General Exclusions",
         "The following are not covered under this Policy under any circumstances: (a) War and allied perils — any injury, disease, disability, or death caused directly or indirectly by war (whether declared or not), civil war, invasion, act of foreign enemy, hostilities, rebellion, insurrection, terrorism, or military or usurped power; (b) Nuclear and radiation risks — any loss or liability arising directly or indirectly from nuclear fission, nuclear fusion, radioactive contamination, or ionising radiation; (c) Intentional self-injury — any treatment arising from attempted suicide, self-inflicted injury, or any act committed while under the influence of alcohol or drugs; (d) Criminal acts — any medical expenses incurred as a result of commission of a breach of law by the Insured Person with criminal intent; (e) Adventure sports — injuries arising from participation in professional sports, adventure activities, or any hazardous activity including but not limited to motor racing, skydiving, bungee jumping, mountaineering, or professional combat sports."),
        ("4.2 Cosmetic and Aesthetic Exclusions",
         "The Insurer shall not be liable for any expenses related to: (a) Cosmetic or reconstructive surgery — surgeries undertaken to improve appearance or for purely aesthetic reasons, including rhinoplasty, breast augmentation/reduction for cosmetic purposes, liposuction, face lifts, tummy tuck (abdominoplasty), and similar procedures; (b) Dental treatment — all dental treatment (including dental implants, orthodontic treatment, and periodontal treatment) unless necessitated by an Accident; (c) Spectacles, contact lenses, and hearing aids — the cost of spectacle frames, lenses, contact lenses, or hearing aids is excluded; (d) Hair loss treatments — alopecia, baldness, hair transplants, and treatment for hair loss are excluded; (e) Obesity treatment — bariatric surgery (gastric bypass, gastric banding) and related weight management programs are excluded unless specifically indicated by a BMI >40 or >35 with at least two co-morbidities, in which case coverage is up to INR 1,50,000 per lifetime."),
        ("4.3 Pre-Existing Disease Waiting Period",
         "Any pre-existing condition, disease, or ailment (PED) diagnosed or treated within 48 months prior to the commencement of the first Policy with the Insurer shall not be covered during the first 48 months of continuous coverage. PEDs include but are not limited to: diabetes mellitus (Type 1 and Type 2), hypertension, coronary artery disease, heart ailments, stroke, asthma, chronic obstructive pulmonary disease (COPD), chronic kidney disease, cirrhosis of the liver, autoimmune disorders, HIV/AIDS, cancer under active treatment, and orthopaedic conditions requiring surgery. Congenital diseases present at birth are permanently excluded unless specifically covered by endorsement."),
        ("4.4 Specific Disease Waiting Periods (24 months)",
         "The following specific diseases are subject to a 24-month waiting period from policy inception (applicable even if not a PED): (a) Benign prostatic hypertrophy; (b) Cataracts (both eyes); (c) Hernia of all kinds; (d) Internal tumours, cysts, nodules, polyps of any kind; (e) Joint replacement surgery (unless due to accident); (f) Sinusitis and related disorders; (g) Tonsillitis; (h) Varicose veins and varicose ulcers; (i) Calculus diseases (kidney stones, gallstones); (j) Pilonidal sinus; (k) Surgery of deviated nasal septum. Coverage for these conditions commences from the 25th month of continuous uninterrupted Policy coverage."),
        ("4.5 First 30-Day Waiting Period",
         "All claims arising from any disease or illness (other than those arising from accidental injury) during the first 30 days from the date of commencement of the Policy are excluded. The 30-day exclusion does not apply on renewal of a Policy without any break. Accidental injuries are covered from Day 1. Life-threatening emergencies arising within the first 30 days may be reviewed on a case-by-case basis."),
        ("4.6 Non-Allopathic Exclusions",
         "Expenses related to experimental, unproven, or non-evidence-based treatment methods are not covered. This includes but is not limited to: stem cell therapy (other than bone marrow transplant for covered conditions), gene therapy, chelation therapy, naturopathy treatments performed at non-accredited facilities, ozone therapy, acupuncture, and any treatment not recognised by the Medical Council of India as mainstream allopathic treatment."),
        ("4.7 Infertility and Reproductive Exclusions",
         "The following are excluded: in-vitro fertilisation (IVF), intrauterine insemination (IUI), gamete intrafallopian transfer (GIFT), zygote intrafallopian transfer (ZIFT), intracytoplasmic sperm injection (ICSI), surrogacy, and any other assisted reproductive technology. Vasectomy and tubectomy are also excluded. Reversal of sterilisation procedures is not covered."),
        ("4.8 Maternity Exclusions (Standard/Silver Plans)",
         "The following are excluded from Standard and Silver Plans: normal delivery charges; caesarean section charges; pre-natal and post-natal charges; new-born care charges; and any complications arising from pregnancy or childbirth. These exclusions do not apply to ectopic pregnancies that are certified as medical emergencies by a registered Medical Practitioner."),
    ]),
    ("PART V – SPECIAL CONDITIONS AND CO-PAYMENT", [
        ("5.1 Co-Payment Clause",
         "A mandatory co-payment of 10% of the admissible claim amount applies to all claims for Insured Persons aged 61 years and above at the time of claim. For Insured Persons who opt for treatment at a Non-Network Hospital (other than emergency cases), an additional co-payment of 20% applies over and above any applicable co-payment. Co-payment means the Insured Person must pay the specified percentage of the admissible claim from their own funds; the Insurer pays the remaining portion."),
        ("5.2 Sub-Limit Application",
         "Where the actual expenses incurred for a specific line item exceed the applicable sub-limit, the excess is borne entirely by the Insured Person. Sub-limits are applied before the co-payment calculation. For example: if a room is billed at INR 5,000/day against a sub-limit of INR 3,000/day, the proportional reduction applies to all associated charges, and the co-pay (if applicable) is computed on the already-reduced admissible amount."),
        ("5.3 Claim Notification Requirements",
         "For planned hospitalisation: the Insurer must be notified at least 48 hours before admission. For emergency hospitalisation: the Insurer must be notified within 24 hours of admission or before discharge (whichever is earlier). Failure to notify in time may result in claims being rejected. Notification must be made through the Insurer's 24x7 helpline, mobile app, or network hospital TPA desk. Claim documents must be submitted within 15 days of discharge for cashless claims and within 30 days of discharge for reimbursement claims."),
        ("5.4 Deductibles",
         "A voluntary deductible, if opted for by the Policyholder at the time of Policy inception, shall be applied per claim event before the Insurer's liability is triggered. The deductible amount, if any, is mentioned in the Policy Schedule. Compulsory deductibles are nil unless specifically endorsed. The deductible does not apply to preventive health check-up benefits."),
        ("5.5 Zone Classification and Premium",
         "India is classified into three Zones for premium computation: Zone A (Mumbai, Delhi-NCR, Bengaluru, Chennai, Kolkata, Pune, Hyderabad); Zone B (all other state capital cities); Zone C (all other cities/towns/rural areas). Premiums vary by Zone. Claims are settled at rates applicable to the Zone of treatment, regardless of the Zone in which the Policy was issued."),
    ]),
    ("PART VI – CLAIM PROCEDURE", [
        ("6.1 Cashless Claim Procedure",
         "Step 1: Check if the treating hospital is a Network Hospital. Step 2: Obtain pre-authorisation by submitting the pre-auth request form, patient ID, policy document, and clinical details to the Insurance Desk at the hospital. Step 3: The TPA will process the pre-authorisation within 2 hours for planned procedures and within 30 minutes for emergencies. Step 4: On discharge, submit the final bill and supporting documents to the TPA desk. Step 5: The Insurer will settle directly with the hospital."),
        ("6.2 Reimbursement Claim Procedure",
         "Step 1: Collect all original bills, receipts, discharge summary, investigation reports, and prescription copies. Step 2: Complete the claim form (available on the Insurer's website or office). Step 3: Submit all documents within 30 days of discharge. Required documents include: (a) Duly completed claim form; (b) Original hospital bills with receipt; (c) Discharge summary; (d) Investigation reports and X-rays; (e) Medical prescriptions; (f) Bank account details and cancelled cheque; (g) Photo ID proof. Step 4: The Insurer will process the claim within 30 working days of receipt of all documents."),
        ("6.3 Claim Dispute Resolution",
         "If the Insured Person is dissatisfied with the claim decision, they may: (a) First escalate to the Grievance Redressal Officer at the nearest branch within 15 days; (b) If unresolved within 15 working days, approach the Insurance Ombudsman as per IRDAI guidelines; (c) Refer to Consumer Forum or civil court as a last resort. The decision of the Insurance Ombudsman shall be binding on the Insurer if accepted by the complainant."),
    ]),
    ("PART VII – POLICY RENEWAL AND CONTINUITY BENEFITS", [
        ("7.1 Lifelong Renewability",
         "This Policy is renewable for lifetime provided the premium is paid on or before the due date. The Insurer shall not deny renewal of the Policy solely on the grounds of the Insured Person's age or deterioration of health. The Insurer reserves the right to modify the premium at renewal based on the Insured Person's age, claims history, and IRDAI-approved premium revisions."),
        ("7.2 No-Claim Bonus (NCB)",
         "For every claim-free year, the Sum Insured is enhanced by 10% (No-Claim Bonus) without an additional premium. Cumulative NCB can go up to 50% of the original Sum Insured. If a claim is made in any year, the NCB accumulated in that year is reduced by 10%. Restored NCB applies from the renewal following the claim-free year. NCB is specific to each Insured Person and is not transferable."),
        ("7.3 Restoration of Sum Insured",
         "In the event the Sum Insured is exhausted during the Policy Year, it shall be automatically restored 100% once per Policy Year. The restored Sum Insured can be utilised for any subsequent unrelated hospitalisation claim in the same Policy Year. Restoration does not apply to the same illness or injury for which the Sum Insured was exhausted."),
        ("7.4 Portability",
         "The Policyholder has the right to transfer (port) this Policy to another insurer at the time of renewal. For porting, the Policyholder must apply to the new insurer at least 45 days before premium due date. The new insurer shall grant credit for waiting periods already served as per IRDAI portability guidelines. NCB credit may or may not be transferred depending on the new insurer's policy; the Policyholder should verify before porting."),
    ]),
    ("PART VIII – PREVENTIVE HEALTH AND VALUE-ADDED SERVICES", [
        ("8.1 Annual Preventive Health Check-Up",
         "Insured Persons aged 18 years and above are entitled to one free preventive health check-up per year at designated Network Hospitals/Diagnostic Centres. The check-up package includes: Complete Blood Count (CBC), Fasting Blood Sugar (FBS), Lipid Profile, Liver Function Test (LFT), Kidney Function Test (KFT), Thyroid Profile (TSH), Urine Routine and Microscopy, Chest X-ray, ECG, and an anti-hypertensive and cardiovascular risk assessment. This benefit is not deducted from the Sum Insured."),
        ("8.2 Telemedicine and Digital Health",
         "Insured Persons have access to unlimited teleconsultation with qualified doctors through the Insurer's mobile application (Star Health App). Telemedical consultations for minor ailments, prescription renewals, and health queries are covered at no additional cost. Telemedicine is available in English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, and Gujarati."),
        ("8.3 Mental Wellness Programme",
         "All Insured Persons have access to 6 free sessions per year with a licensed counsellor or psychologist through the Insurer's Mental Wellness Platform. These sessions are conducted via video call and are completely confidential. Topics covered include stress management, anxiety, depression, relationship issues, and work-life balance."),
        ("8.4 Chronic Disease Management",
         "Insured Persons diagnosed with diabetes, hypertension, asthma, or coronary artery disease are eligible for the Disease Management Programme (DMP). This includes: quarterly health check-ups, dedicated care manager support, digital health tracking tools, nutrition counselling, and medication reminders. Participation in the DMP may qualify for premium discounts at renewal."),
    ]),
    ("PART IX – NETWORK HOSPITALS AND TPA", [
        ("9.1 Network Hospital Empanelment",
         "The Insurer maintains a network of over 14,000 hospitals across India. The latest list of Network Hospitals is published on the Insurer's website (www.starhealth.in) and is updated quarterly. Network Hospitals are empanelled based on their infrastructure, quality standards, compliance with clinical protocols, and agreement to honour cashless settlements. Empanelment status of a hospital may change; the Insured Person should verify before admission."),
        ("9.2 TPA Services",
         "Third Party Administrator (TPA) services are provided by Star Health's in-house TPA division, ensuring seamless coordination between the Insured, treating hospital, and the Insurer. TPA services include pre-authorisation processing, claim document collection, medical opinion, and direct settlement with Network Hospitals. The TPA helpline is available 24x7 at 1800-425-2255 (toll-free)."),
        ("9.3 International Coverage",
         "For Insured Persons travelling abroad on a temporary basis (not exceeding 60 days per trip), emergency medical expenses incurred outside India are covered up to INR 5,00,000 per Policy Year. Coverage applies to emergency hospitalisation only; routine and elective treatments abroad are not covered. Claims for overseas treatment must be submitted in original with certified translations if not in English."),
    ]),
    ("PART X – FRAUD PREVENTION AND POLICY TERMINATION", [
        ("10.1 Disclosure Requirements",
         "The contract of insurance is based on the principle of Utmost Good Faith (Uberrima Fides). The Policyholder and Insured Persons are duty-bound to disclose all material facts truthfully at the time of proposal and throughout the Policy period. Non-disclosure or misrepresentation of any material fact entitles the Insurer to repudiate the claim and/or cancel the Policy from inception (ab initio), in which case premiums paid shall be forfeited."),
        ("10.2 Anti-Fraud Measures",
         "The Insurer employs a multi-layered fraud detection system including: (a) AI-based pattern recognition to identify duplicate claims, upcoding, and phantom billing; (b) Physical and telephonic verification for claims above INR 1,00,000; (c) Collaboration with the Insurance Information Bureau of India (IIB) to detect cross-insurer fraud; (d) Random audits of Network Hospitals for compliance. Any provider or Insured Person found guilty of fraud shall be permanently blacklisted and referred to law enforcement."),
        ("10.3 Policy Cancellation by Insurer",
         "The Insurer reserves the right to cancel the Policy by giving 30 days' written notice if: (a) The Policyholder engages in fraudulent claim submission; (b) Material facts are misrepresented or concealed; (c) Premiums are unpaid beyond the grace period; or (d) The Insured Person ceases to meet the eligibility criteria. On cancellation for reasons (a) or (b), no refund of premium is payable. For cancellation for reason (c) or (d), a pro-rated refund is payable."),
    ]),
    ("ANNEXURE A – APPROVED DAY CARE PROCEDURES", [
        ("A.1 Surgical Procedures (Day Care)",
         "The following surgical procedures are approved for Day Care treatment and covered subject to all other Policy terms: Adenoidectomy, Anal Fissurectomy, Appendicectomy (Laparoscopic), Arthroscopy of knee/shoulder/ankle, Bariatric surgery (where approved), Biopsy of Breast/Lymph node, Cataract extraction with IOL implant, Coronary angiography and angioplasty, Dental extraction under general anaesthesia, Endoscopic sinus surgery, ERCP with stone removal, Excision of cyst/tumour (superficial), Hernioraphy (inguinal/umbilical - laparoscopic), Hydrocele repair, Hysteroscopy, Laparoscopic cholecystectomy, Laparoscopic ovarian cystectomy, Lithotripsy (ESWL), Myringotomy with grommet insertion, Nasal polypectomy, Orchidectomy, Rhinoplasty (reconstructive), Septoplasty, Tonsillectomy, TURP (endoscopic), Varicocelectomy, Vasectomy, VSD/ASD closure (catheter-based)."),
        ("A.2 Medical Procedures (Day Care)",
         "Medical procedures approved for Day Care include: Blood transfusion, Bone marrow aspiration and biopsy, Bronchoscopy, Cardiac catheterisation (diagnostic), Chemotherapy (single agent or combination), Colonoscopy with/without polypectomy, Cystoscopy, Dialysis (peritoneal and haemodialysis), ECT (Electroconvulsive therapy), Gastroscopy/Upper GI endoscopy, Immunotherapy, Intra-articular injection under fluoroscopy, Intravitreal injection, IUI (intrauterine insemination - excluded from this Policy), Nerve block procedures, Pericardiocentesis, Pleural tapping, Radiation therapy (all modalities), Sigmoidoscopy, Sleep study (Polysomnography), Tonometry under anaesthesia."),
    ]),
    ("PART XI – SPECIAL ENDORSEMENTS", [
        ("11.1 Critical Illness Rider",
         "Where the Policyholder has opted for the Critical Illness Rider (as evidenced in the Policy Schedule), an additional lump sum benefit is payable on first diagnosis of a listed Critical Illness, provided the Insured Person survives for 30 days after such diagnosis. Listed Critical Illnesses include: cancer of specified severity, open heart surgery (CABG), first heart attack of specified severity, kidney failure requiring regular dialysis, major organ transplant, stroke resulting in permanent neurological deficit, permanent paralysis of limbs, aorta surgery, blindness, primary pulmonary arterial hypertension, motor neurone disease, multiple sclerosis, deafness, aplastic anaemia, third degree burns (>20% BSA), Alzheimer's disease, Parkinson's disease, and coma of specified severity. The Critical Illness Rider is a stand-alone indemnity benefit and is paid over and above the base hospitalisation claim."),
        ("11.2 Personal Accident Cover",
         "Where opted, the Personal Accident Cover provides a lump sum benefit of 100% of the opted Accident Sum Insured in case of Accidental Death or Permanent Total Disability. Benefits of 50% of the Accident Sum Insured are payable for Permanent Partial Disability as per the IRDAI-approved schedule. Temporary Total Disability (TTD) benefit is payable at 1% of the Accident Sum Insured per week for up to 100 weeks. Accidental hospitalisation expenses are covered under the base hospitalisation benefit."),
        ("11.3 Hospital Cash Benefit",
         "Where opted, the Hospital Cash Benefit provides a fixed daily allowance for each continuous 24-hour period of hospitalisation exceeding 24 hours. The daily allowance is specified in the Policy Schedule (commonly INR 500 to INR 2,000 per day). The benefit is payable for a maximum of 30 days per hospitalisation and 90 days per Policy Year. ICU hospitalisation triggers payment at twice the normal daily allowance. This benefit is paid in addition to actual hospitalisation claim reimbursement."),
    ]),
    ("PART XII – REGULATORY DISCLOSURES AND GRIEVANCE", [
        ("12.1 IRDAI Compliance",
         "This Policy has been approved by the Insurance Regulatory and Development Authority of India (IRDAI) and is compliant with IRDAI (Health Insurance) Regulations, 2016 and subsequent amendments. The Policy incorporates all mandatory covers as per IRDAI Circular No. IRDA/HLT/REG/CIR/200/08/2016. The Policyholder has the right to a free look period of 15 days from the date of receipt of the Policy to review its terms and return the Policy if not satisfied."),
        ("12.2 Grievance Redressal",
         "The Insurer has established a Grievance Redressal Mechanism as follows: Level 1 — Contact Customer Service at 1800-425-2255 (Toll Free, 24x7). Level 2 — Write to Grievance Redressal Officer, Star Health Insurance, No.1, New Tank Street, Valluvar Kottam High Road, Nungambakkam, Chennai 600034. Email: grievance@starhealth.in. Level 3 — Insurance Ombudsman (addresses available on IRDAI website). Level 4 — Consumer Disputes Redressal Forum / Civil Courts. The Insurer commits to resolve all grievances within 15 working days of receipt. Unresolved complaints may be reported to IRDAI through the Bima Bharosa online portal."),
        ("12.3 Data Privacy",
         "The Insurer collects, processes, and stores personal health information in compliance with the Information Technology Act, 2000, and applicable data protection regulations. Health data is used solely for policy administration and claim processing purposes. Third-party sharing of personal health data requires explicit written consent of the Policyholder except where mandated by law. Data is retained for a minimum period of 7 years after Policy termination."),
        ("12.4 Jurisdiction and Governing Law",
         "This Policy is governed by and construed in accordance with the laws of India. Any dispute, controversy, or difference arising out of or in connection with this insurance Policy shall be referred to arbitration in accordance with the Arbitration and Conciliation Act, 1996, unless the claimant prefers to approach the Insurance Ombudsman or Consumer Forum. The arbitration shall be conducted in the city where the Policy was issued."),
    ]),
]


def build_policy_pdf():
    path = os.path.join(OUTPUT_DIR, "StarHealth_Comprehensive_Policy_50pg.pdf")
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
    )
    story = []

    # ── Cover Page ──
    story += [sp(4)]
    story.append(Paragraph("STAR HEALTH AND ALLIED INSURANCE CO. LTD.", TITLE))
    story.append(Paragraph("Comprehensive Health Insurance Policy", H1))
    story.append(hr())
    story += [sp(1)]

    cover_data = [
        ["Policy Number", "SHI-COMP-2024-HP-9983221"],
        ["Policy Type", "Individual Health Insurance — Gold Plan"],
        ["Sum Insured", "INR 3,00,000 (Three Lakhs Only)"],
        ["Room Rent", "INR 3,000 per day (Standard Room)"],
        ["ICU Room Limit", "INR 6,000 per day"],
        ["Co-Pay", "10% for claimants aged 61+ years"],
        ["Waiting Period (General)", "30 days from policy inception"],
        ["Waiting Period (Specific)", "24 months (as listed in Part IV)"],
        ["Pre-Existing Diseases", "48 months waiting period"],
        ["Policyholder", "Rahul Sharma"],
        ["Date of Birth", "12/05/1982"],
        ["Policy Period", "01/04/2024 to 31/03/2025"],
        ["IRDAI License No.", "IRDA/HLT/SHI/2008/P-001"],
        ["Registered Office", "No.1, New Tank Street, Nungambakkam, Chennai 600034"],
    ]
    t = Table(cover_data, colWidths=[6 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story += [sp(2)]
    story.append(Paragraph("This document contains 12 Parts and 2 Annexures. Please read all sections carefully before making a claim.", NOTE))
    story.append(PageBreak())

    # ── Sections ──
    for part_title, sub_sections in POLICY_SECTIONS:
        story.append(Paragraph(part_title, H1))
        story.append(hr())
        for sub_title, content in sub_sections:
            story.append(KeepTogether([
                Paragraph(sub_title, H2),
                Paragraph(content, BODY),
                sp(0.5),
            ]))
        story.append(PageBreak())

    # ── Signature Page ──
    story.append(Paragraph("SIGNATURES AND DECLARATION", H1))
    story.append(hr())
    story.append(Paragraph(
        "I/We declare that the information given in this Policy Schedule and in the proposal form is true and accurate "
        "to the best of my/our knowledge and belief. I/We agree to abide by all the terms and conditions of this Policy.",
        BODY,
    ))
    story += [sp(3)]
    sig_data = [
        ("Policyholder Signature", "Authorised Signatory (Insurer)"),
        ("________________________", "________________________"),
        ("Rahul Sharma", "Star Health Insurance"),
        ("Date: _______________", "Date: 01/04/2024"),
    ]
    st = Table(sig_data, colWidths=[8.5 * cm, 8.5 * cm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(st)

    doc.build(story)
    print(f"✅ Policy PDF: {path}")
    return path


# ═══════════════════════════════════════════════════════════════════════════════
#  HOSPITAL BILL PDF
# ═══════════════════════════════════════════════════════════════════════════════

def build_bill_pdf():
    path = os.path.join(OUTPUT_DIR, "Apollo_Hospital_Bill_Rahul_Sharma.pdf")
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    story = []

    story.append(Paragraph("APOLLO HOSPITALS ENTERPRISE LIMITED", TITLE))
    story.append(Paragraph("Jubilee Hills, Hyderabad — 500033", CENTER))
    story.append(hr())
    story.append(sp(0.5))

    pt_data = [
        ["Bill No:", "APL-HYD-2024-08823", "Date:", "15/03/2024"],
        ["Patient:", "Rahul Sharma", "UHID:", "APL-4521-S"],
        ["Doctor:", "Dr. Priya Menon", "Ward:", "General Ward"],
    ]
    t = Table(pt_data, colWidths=[3 * cm, 6 * cm, 3 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)
    story.append(sp(0.5))
    story.append(hr())

    bill_items = [
        ["Description", "Amount (INR)"],
        ["Room Charges", "3,000.00"],
        ["Surgery Charges", "61,000.00"],
        ["Medication", "5,372.00"],
        ["Laboratory & Diagnostics", "11,700.00"],
        ["Consultation", "2,500.00"],
        ["Supplies", "5,050.00"],
        ["Physiotherapy", "1,200.00"],
        ["GST", "2,058.00"],
    ]
    bt = Table(bill_items, colWidths=[12 * cm, 5 * cm])
    bt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.2, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(bt)
    story.append(sp(1))
    story.append(hr())
    story.append(Paragraph(
        "This is a computer-generated bill. For queries, contact billing@apollohyd.in | "
        "Certified that the treatment was medically necessary and rendered at this hospital.",
        NOTE,
    ))
    story.append(sp(1))
    story.append(Paragraph(
        "Authorized Signatory: Dr. Priya Menon (Reg. No. AP-MCI-28847) | "
        "Billing Officer: K. Lakshmi | Date of Bill: 15/03/2024",
        NOTE,
    ))

    doc.build(story)
    print(f"✅ Bill PDF: {path}")
    return path


if __name__ == "__main__":
    print("Generating sample PDFs...")
    bill = build_bill_pdf()
    policy = build_policy_pdf()
    print(f"\n✅ Done! Files saved to: {OUTPUT_DIR}")
    print(f"  Bill PDF   → {bill}")
    print(f"  Policy PDF → {policy}")
