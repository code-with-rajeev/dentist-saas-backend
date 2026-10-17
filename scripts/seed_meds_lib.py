"""
Seed script — System Medication Library
Populates med_library table with 141 preloaded Indian dental formulary entries.

Usage:
    python seed_meds_lib.py

Run ONCE after alembic upgrade head.
Safe to re-run — skips existing entries (upsert on name + dosage + dentist_id).
"""

# Standard library
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path so 'app' is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# Third-party
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Internal
from app.core.config import settings
from app.models.med_library import MedLibrary

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# 141 system meds — Indian dental formulary
# ============================================================

SYSTEM_MEDS = [
    # ── Antibiotics ──────────────────────────────────────────
    {"name": "Amoxicillin", "dosage": "250mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Amoxicillin", "dosage": "500mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Amoxicillin + Clavulanate", "dosage": "375mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Amoxicillin + Clavulanate", "dosage": "625mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Metronidazole", "dosage": "200mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Metronidazole", "dosage": "400mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Metronidazole", "dosage": "500mg", "frequency": "Three times a day", "duration": "7 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Amoxicillin + Metronidazole", "dosage": "500mg + 400mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Azithromycin", "dosage": "250mg", "frequency": "Once daily", "duration": "3 days", "instructions": "Before food", "category": "Antibiotic"},
    {"name": "Azithromycin", "dosage": "500mg", "frequency": "Once daily", "duration": "3 days", "instructions": "Before food", "category": "Antibiotic"},
    {"name": "Clindamycin", "dosage": "150mg", "frequency": "Four times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Clindamycin", "dosage": "300mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Doxycycline (High Dose)", "dosage": "100mg", "frequency": "Once daily", "duration": "7 days", "instructions": "After food with plenty of water", "category": "Antibiotic"},
    {"name": "Doxycycline (Low Dose)", "dosage": "100mg", "frequency": "Twice daily", "duration": "7 days", "instructions": "After food with plenty of water", "category": "Antibiotic"},
    {"name": "Ciprofloxacin", "dosage": "500mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "After food", "category": "Antibiotic"},
    {"name": "Erythromycin", "dosage": "250mg", "frequency": "Four times a day", "duration": "5 days", "instructions": "Before food", "category": "Antibiotic"},
    {"name": "Erythromycin", "dosage": "500mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "Before food", "category": "Antibiotic"},
    {"name": "Tetracycline", "dosage": "250mg", "frequency": "Four times a day", "duration": "7 days", "instructions": "Before food, avoid dairy products", "category": "Antibiotic"},
    {"name": "Metronidazole (Gel)", "dosage": "1%", "frequency": "Twice daily", "duration": "7 days", "instructions": "Apply on affected gum area", "category": "Antibiotic"},
    {"name": "Metronidazole (Gel)", "dosage": "0.75%", "frequency": "Twice daily", "duration": "7 days", "instructions": "Apply on affected gum area", "category": "Antibiotic"},
    {"name": "Doxycycline (Gel)", "dosage": "10%", "frequency": "Single application", "duration": "As directed", "instructions": "Apply into periodontal pocket after scaling", "category": "Antibiotic"},
    {"name": "Tetracycline (Fibre/Gel)", "dosage": "2%", "frequency": "Single application", "duration": "As directed", "instructions": "Place in periodontal pocket", "category": "Antibiotic"},

    # ── Analgesics ───────────────────────────────────────────
    {"name": "Paracetamol", "dosage": "325mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Paracetamol", "dosage": "500mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Paracetamol", "dosage": "650mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Tramadol", "dosage": "50mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Tramadol", "dosage": "100mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Tramadol + Paracetamol", "dosage": "37.5mg + 325mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Choline Salicylate + Benzalkonium Chloride (Gel)", "dosage": "8.7% + 0.01%", "frequency": "Three to four times a day", "duration": "7 days", "instructions": "Apply on ulcer after meals", "category": "Analgesic"},
    {"name": "Amlexanox (Paste)", "dosage": "5%", "frequency": "Four times a day", "duration": "10 days", "instructions": "Apply on ulcer after meals and at bedtime", "category": "Analgesic"},
    {"name": "Zinc Oxide Eugenol (Paste)", "dosage": None, "frequency": "Single application", "duration": "As directed", "instructions": "Pack in dry socket, replace every 2–3 days", "category": "Analgesic"},
    {"name": "Alvogyl (Butamben + Eugenol + Iodoform)", "dosage": None, "frequency": "Single application", "duration": "As directed", "instructions": "Place in dry socket, replace every 2–3 days", "category": "Analgesic"},
    {"name": "Potassium Nitrate (Toothpaste)", "dosage": "5%", "frequency": "Twice daily", "duration": "4 weeks", "instructions": "Use instead of regular toothpaste", "category": "Analgesic"},
    {"name": "Strontium Chloride (Toothpaste)", "dosage": "10%", "frequency": "Twice daily", "duration": "4 weeks", "instructions": "Use instead of regular toothpaste", "category": "Analgesic"},
    {"name": "Methocarbamol", "dosage": "500mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Chlorzoxazone", "dosage": "250mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Chlorzoxazone", "dosage": "500mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Thiocolchicoside", "dosage": "4mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "After food", "category": "Analgesic"},
    {"name": "Thiocolchicoside", "dosage": "8mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "After food", "category": "Analgesic"},

    # ── NSAIDs ───────────────────────────────────────────────
    {"name": "Ibuprofen", "dosage": "200mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Ibuprofen", "dosage": "600mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Ibuprofen + Paracetamol", "dosage": "400mg + 325mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Aceclofenac", "dosage": "100mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Aceclofenac + Paracetamol", "dosage": "100mg + 325mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Aceclofenac + Paracetamol + Serratiopeptidase", "dosage": "100mg + 325mg + 15mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Diclofenac", "dosage": "50mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Diclofenac", "dosage": "75mg", "frequency": "Once daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Diclofenac + Paracetamol", "dosage": "50mg + 325mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Ketorolac", "dosage": "10mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Ketorolac", "dosage": "30mg", "frequency": "Once", "duration": "Single dose", "instructions": "After food", "category": "NSAID"},
    {"name": "Nimesulide", "dosage": "100mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Nimesulide + Paracetamol", "dosage": "100mg + 325mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Etoricoxib", "dosage": "60mg", "frequency": "Once daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Etoricoxib", "dosage": "90mg", "frequency": "Once daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Mefenamic Acid", "dosage": "250mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Mefenamic Acid", "dosage": "500mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Celecoxib", "dosage": "100mg", "frequency": "Twice daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},
    {"name": "Celecoxib", "dosage": "200mg", "frequency": "Once daily", "duration": "3 days", "instructions": "After food", "category": "NSAID"},

    # ── Antifungals ──────────────────────────────────────────
    {"name": "Fluconazole", "dosage": "50mg", "frequency": "Once daily", "duration": "7 days", "instructions": "After food", "category": "Antifungal"},
    {"name": "Fluconazole", "dosage": "150mg", "frequency": "Once", "duration": "Single dose", "instructions": "After food", "category": "Antifungal"},
    {"name": "Clotrimazole (Gel)", "dosage": "1%", "frequency": "Three times a day", "duration": "14 days", "instructions": "Apply on affected area after meals", "category": "Antifungal"},
    {"name": "Nystatin (Oral Suspension)", "dosage": "100000 IU/mL", "frequency": "Four times a day", "duration": "14 days", "instructions": "Swish and swallow or swish and spit", "category": "Antifungal"},
    {"name": "Miconazole (Oral Gel)", "dosage": "2%", "frequency": "Four times a day", "duration": "14 days", "instructions": "Apply on affected area after food", "category": "Antifungal"},
    {"name": "Itraconazole", "dosage": "100mg", "frequency": "Once daily", "duration": "15 days", "instructions": "After food", "category": "Antifungal"},
    {"name": "Itraconazole", "dosage": "200mg", "frequency": "Once daily", "duration": "7 days", "instructions": "After food", "category": "Antifungal"},

    # ── Antiseptics ──────────────────────────────────────────
    {"name": "Chlorhexidine Gluconate (Mouthwash)", "dosage": "0.2%", "frequency": "Twice daily", "duration": "7 days", "instructions": "Rinse for 30 seconds after brushing, do not swallow", "category": "Antiseptic"},
    {"name": "Chlorhexidine Gluconate (Mouthwash)", "dosage": "0.12%", "frequency": "Twice daily", "duration": "7 days", "instructions": "Rinse for 30 seconds after brushing, do not swallow", "category": "Antiseptic"},
    {"name": "Chlorhexidine Gluconate (Gel)", "dosage": "1%", "frequency": "Twice daily", "duration": "7 days", "instructions": "Apply on gums after brushing", "category": "Antiseptic"},
    {"name": "Povidone-Iodine (Mouthwash)", "dosage": "1%", "frequency": "Three times a day", "duration": "5 days", "instructions": "Dilute with equal water, gargle for 30 seconds, do not swallow", "category": "Antiseptic"},
    {"name": "Hydrogen Peroxide (Mouthwash)", "dosage": "1.5%", "frequency": "Twice daily", "duration": "5 days", "instructions": "Rinse for 60 seconds, do not swallow", "category": "Antiseptic"},
    {"name": "Hexetidine (Mouthwash)", "dosage": "0.1%", "frequency": "Twice daily", "duration": "7 days", "instructions": "Rinse for 30 seconds after meals, do not swallow", "category": "Antiseptic"},
    {"name": "Benzydamine Hydrochloride (Mouthwash)", "dosage": "0.15%", "frequency": "Three times a day", "duration": "7 days", "instructions": "Rinse for 30 seconds, do not swallow", "category": "Antiseptic"},
    {"name": "Clove Oil", "dosage": None, "frequency": "As needed", "duration": "As directed", "instructions": "Apply on affected tooth with cotton pellet", "category": "Antiseptic"},
    {"name": "Hyaluronic Acid (Gel)", "dosage": "0.2%", "frequency": "Three times a day", "duration": "7 days", "instructions": "Apply on ulcer or surgical site after food", "category": "Antiseptic"},
    {"name": "Sodium Fluoride (Toothpaste/Gel)", "dosage": "1000 ppm", "frequency": "Twice daily", "duration": "Ongoing", "instructions": "Use instead of regular toothpaste, do not rinse after", "category": "Antiseptic"},
    {"name": "Sodium Fluoride (Varnish)", "dosage": None, "frequency": "Every 3–6 months", "duration": "As directed", "instructions": "Apply by dentist, avoid eating or drinking for 30 minutes", "category": "Antiseptic"},
    {"name": "Stannous Fluoride (Gel)", "dosage": "0.4%", "frequency": "Once daily", "duration": "Ongoing", "instructions": "Apply in tray for 4 minutes, do not swallow", "category": "Antiseptic"},
    {"name": "Silver Diamine Fluoride", "dosage": "38%", "frequency": "Single application", "duration": "As directed", "instructions": "Apply on carious lesion, may stain black", "category": "Antiseptic"},

    # ── Steroids ─────────────────────────────────────────────
    {"name": "Dexamethasone", "dosage": "0.5mg", "frequency": "Once daily", "duration": "3 days", "instructions": "After food, morning dose", "category": "Steroid"},
    {"name": "Dexamethasone", "dosage": "4mg", "frequency": "Once", "duration": "Single dose", "instructions": "After food, for post-operative swelling", "category": "Steroid"},
    {"name": "Prednisolone", "dosage": "5mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, morning dose", "category": "Steroid"},
    {"name": "Prednisolone", "dosage": "10mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, morning dose", "category": "Steroid"},
    {"name": "Prednisolone", "dosage": "20mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, morning dose", "category": "Steroid"},
    {"name": "Triamcinolone Acetonide (Dental Paste)", "dosage": "0.1%", "frequency": "Two to three times a day", "duration": "7 days", "instructions": "Apply thin coat on ulcer after meals and at bedtime", "category": "Steroid"},
    {"name": "Betamethasone (Mouthwash)", "dosage": "0.5mg/5mL", "frequency": "Three times a day", "duration": "7 days", "instructions": "Rinse for 2 minutes, do not swallow", "category": "Steroid"},
    {"name": "Hydrocortisone (Oral Paste)", "dosage": "2.5mg", "frequency": "Three times a day", "duration": "7 days", "instructions": "Apply on ulcer after food and at bedtime", "category": "Steroid"},

    # ── Local Anaesthetics ───────────────────────────────────
    {"name": "Lignocaine Hydrochloride (Injection)", "dosage": "2%", "frequency": "Single administration", "duration": "Per procedure", "instructions": "Administer by infiltration or nerve block as per procedure", "category": "Local Anaesthetic"},
    {"name": "Lignocaine + Adrenaline (Injection)", "dosage": "2% + 1:80000", "frequency": "Single administration", "duration": "Per procedure", "instructions": "Administer by infiltration or nerve block, aspirate before injection", "category": "Local Anaesthetic"},
    {"name": "Lignocaine + Adrenaline (Injection)", "dosage": "2% + 1:200000", "frequency": "Single administration", "duration": "Per procedure", "instructions": "Administer by infiltration or nerve block, aspirate before injection", "category": "Local Anaesthetic"},
    {"name": "Articaine + Adrenaline (Injection)", "dosage": "4% + 1:100000", "frequency": "Single administration", "duration": "Per procedure", "instructions": "Administer by infiltration, aspirate before injection", "category": "Local Anaesthetic"},
    {"name": "Articaine + Adrenaline (Injection)", "dosage": "4% + 1:200000", "frequency": "Single administration", "duration": "Per procedure", "instructions": "Administer by infiltration, aspirate before injection", "category": "Local Anaesthetic"},
    {"name": "Bupivacaine (Injection)", "dosage": "0.5%", "frequency": "Single administration", "duration": "Per procedure", "instructions": "For long procedures, nerve block, aspirate before injection", "category": "Local Anaesthetic"},
    {"name": "Mepivacaine (Injection)", "dosage": "3%", "frequency": "Single administration", "duration": "Per procedure", "instructions": "Plain solution, use in patients where adrenaline is contraindicated", "category": "Local Anaesthetic"},
    {"name": "Lignocaine (Topical Gel)", "dosage": "2%", "frequency": "Single application", "duration": "Per procedure", "instructions": "Apply on mucosa 2 minutes before injection", "category": "Local Anaesthetic"},
    {"name": "Lignocaine (Topical Spray)", "dosage": "10%", "frequency": "Single application", "duration": "Per procedure", "instructions": "Spray on mucosa, wait 2 minutes before procedure", "category": "Local Anaesthetic"},
    {"name": "Benzocaine (Topical Gel)", "dosage": "20%", "frequency": "Single application", "duration": "Per procedure", "instructions": "Apply on mucosa before injection or procedure", "category": "Local Anaesthetic"},

    # ── Antihistamines ───────────────────────────────────────
    {"name": "Cetirizine", "dosage": "5mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, preferably at night", "category": "Antihistamine"},
    {"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, preferably at night", "category": "Antihistamine"},
    {"name": "Levocetirizine", "dosage": "2.5mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, at night", "category": "Antihistamine"},
    {"name": "Levocetirizine", "dosage": "5mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food, at night", "category": "Antihistamine"},
    {"name": "Chlorpheniramine Maleate", "dosage": "4mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food, causes drowsiness", "category": "Antihistamine"},
    {"name": "Loratadine", "dosage": "10mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food", "category": "Antihistamine"},
    {"name": "Fexofenadine", "dosage": "120mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food", "category": "Antihistamine"},
    {"name": "Fexofenadine", "dosage": "180mg", "frequency": "Once daily", "duration": "5 days", "instructions": "After food", "category": "Antihistamine"},

    # ── Antacids ─────────────────────────────────────────────
    {"name": "Pantoprazole", "dosage": "20mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Pantoprazole", "dosage": "40mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Omeprazole", "dosage": "20mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Omeprazole", "dosage": "40mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Rabeprazole", "dosage": "10mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Rabeprazole", "dosage": "20mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Ranitidine", "dosage": "150mg", "frequency": "Twice daily", "duration": "5 days", "instructions": "Before food", "category": "Antacid"},
    {"name": "Esomeprazole", "dosage": "20mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},
    {"name": "Esomeprazole", "dosage": "40mg", "frequency": "Once daily", "duration": "5 days", "instructions": "Before food, morning", "category": "Antacid"},

    # ── Enzymes ──────────────────────────────────────────────
    {"name": "Serratiopeptidase", "dosage": "5mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "Before food", "category": "Enzyme"},
    {"name": "Serratiopeptidase", "dosage": "10mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "Before food", "category": "Enzyme"},
    {"name": "Trypsin + Chymotrypsin", "dosage": "100000 IU", "frequency": "Three times a day", "duration": "5 days", "instructions": "Before food", "category": "Enzyme"},
    {"name": "Trypsin + Chymotrypsin", "dosage": "200000 IU", "frequency": "Twice daily", "duration": "5 days", "instructions": "Before food", "category": "Enzyme"},
    {"name": "Bromelain", "dosage": "40mg", "frequency": "Three times a day", "duration": "5 days", "instructions": "Before food", "category": "Enzyme"},

    # ── Anxiolytics ──────────────────────────────────────────
    {"name": "Diazepam", "dosage": "2mg", "frequency": "Once", "duration": "Single dose", "instructions": "1 hour before procedure", "category": "Anxiolytic"},
    {"name": "Diazepam", "dosage": "5mg", "frequency": "Once", "duration": "Single dose", "instructions": "1 hour before procedure, do not drive", "category": "Anxiolytic"},
    {"name": "Alprazolam", "dosage": "0.25mg", "frequency": "Once", "duration": "Single dose", "instructions": "1 hour before procedure, do not drive", "category": "Anxiolytic"},
    {"name": "Alprazolam", "dosage": "0.5mg", "frequency": "Once", "duration": "Single dose", "instructions": "1 hour before procedure, do not drive", "category": "Anxiolytic"},
    {"name": "Triazolam", "dosage": "0.25mg", "frequency": "Once", "duration": "Single dose", "instructions": "1 hour before procedure, do not drive", "category": "Anxiolytic"},

    # ── Vitamins / Minerals ──────────────────────────────────
    {"name": "Vitamin C (Ascorbic Acid)", "dosage": "500mg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Vitamin C (Ascorbic Acid)", "dosage": "1000mg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Vitamin B Complex", "dosage": "1 tablet", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Vitamin B12 (Methylcobalamin)", "dosage": "500mcg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Vitamin B12 (Methylcobalamin)", "dosage": "1500mcg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Vitamin D3", "dosage": "1000 IU", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Vitamin D3", "dosage": "60000 IU", "frequency": "Once a week", "duration": "8 weeks", "instructions": "After food", "category": "Vitamin"},
    {"name": "Calcium + Vitamin D3", "dosage": "500mg + 250 IU", "frequency": "Twice daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Calcium + Vitamin D3", "dosage": "1000mg + 500 IU", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Folic Acid", "dosage": "5mg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Zinc Sulphate", "dosage": "50mg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},
    {"name": "Iron + Folic Acid", "dosage": "100mg + 1.5mg", "frequency": "Once daily", "duration": "30 days", "instructions": "After food", "category": "Vitamin"},

    # ── Haemostatics ─────────────────────────────────────────
    {"name": "Tranexamic Acid", "dosage": "500mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "Haemostatic"},
    {"name": "Tranexamic Acid", "dosage": "650mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "Haemostatic"},
    {"name": "Tranexamic Acid (Mouthwash)", "dosage": "4.8%", "frequency": "Four times a day", "duration": "2 days", "instructions": "Rinse for 2 minutes after extraction, do not swallow", "category": "Haemostatic"},
    {"name": "Etamsylate", "dosage": "250mg", "frequency": "Four times a day", "duration": "3 days", "instructions": "After food", "category": "Haemostatic"},
    {"name": "Etamsylate", "dosage": "500mg", "frequency": "Three times a day", "duration": "3 days", "instructions": "After food", "category": "Haemostatic"},
]


# ============================================================
# Seed logic
# ============================================================

async def seed(session: AsyncSession) -> None:
    inserted = 0
    skipped = 0

    for med in SYSTEM_MEDS:
        # Duplicate check — name + dosage + dentist_id (NULL for system)
        # Handles NULL dosage correctly via Python-level check
        if med["dosage"] is not None:
            existing = await session.execute(
                select(MedLibrary).where(
                    MedLibrary.name == med["name"],
                    MedLibrary.dosage == med["dosage"],
                    MedLibrary.dentist_id.is_(None),
                )
            )
        else:
            existing = await session.execute(
                select(MedLibrary).where(
                    MedLibrary.name == med["name"],
                    MedLibrary.dosage.is_(None),
                    MedLibrary.dentist_id.is_(None),
                )
            )

        if existing.scalar_one_or_none() is not None:
            skipped += 1
            continue

        session.add(MedLibrary(
            name=med["name"],
            dosage=med["dosage"],
            frequency=med["frequency"],
            duration=med["duration"],
            instructions=med["instructions"],
            category=med["category"],
            source="system",
            dentist_id=None,
            usage_count=0,
        ))
        inserted += 1

    await session.commit()
    logger.info("✅ Seed complete — inserted: %d, skipped (already exist): %d", inserted, skipped)


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())