"""
Tags each intervention with a mechanism_class based on its drug's known pharmacology.

Neither ClinicalTrials.gov nor openFDA gives you this directly, so this is a manual
lookup table built from established pharmacology + targeted research on the IPF-specific
investigational compounds that don't have a well-known mechanism off the top of the head.
Matching is done on a normalized (lowercase, dosage-stripped) version of the drug name.
"""

import psycopg2
import re

DB_CONFIG = {
    "host": "localhost",
    "dbname": "ipf_trial_intelligence",
    "user": "ipf_user",
    "password": "ipf_pass",
    "port": 5432,
}

# Normalized drug name -> mechanism class.
# Everything in here I either already knew or specifically looked up and confirmed -
# nothing in this dictionary is a guess.
MECHANISM_MAP = {
    # The two approved IPF drugs, plus their pipeline cousins and research codes
    "nintedanib": "antifibrotic",
    "bibf 1120": "antifibrotic",            # nintedanib's old research code before it had a name
    "pirfenidone": "antifibrotic",
    "pirfenidoneone": "antifibrotic",       # typo in the source data, same drug
    "deupirfenidone": "antifibrotic",
    "nerandomilast": "antifibrotic",        # PDE4B inhibitor - just got FDA approval Oct 2025 as Jascayd
    "pamrevlumab": "antifibrotic",          # anti-CTGF antibody, also listed as FG-3019
    "pbi4050": "antifibrotic",              # GPR40/FFAR1 agonist
    "bbt877": "antifibrotic",               # autotaxin inhibitor
    "glpg1690": "antifibrotic",             # ziritaxestat, also an autotaxin inhibitor
    "ziritaxestat": "antifibrotic",
    "pln74809": "antifibrotic",             # bexotegrast, blocks integrin-mediated TGF-b activation
    "bexotegrast": "antifibrotic",
    "prm151": "antifibrotic",               # zinpentraxin alfa
    "zinpentraxin alfa": "antifibrotic",
    "trk250": "antifibrotic",               # antisense oligo targeting TGF-b1 directly
    "gkt137831": "antifibrotic",            # setanaxib, NOX1/4 inhibitor
    "rxc007": "antifibrotic",               # ROCK2 inhibitor
    "gb0139": "antifibrotic",               # TD139, galectin-3 inhibitor
    "vismodegib": "antifibrotic",           # Hedgehog/SMO pathway
    "taladegib": "antifibrotic",
    "env101": "antifibrotic",               # ENV-101 is taladegib under a program code
    "bms986278": "antifibrotic",            # admilparant, LPA1 antagonist
    "hec585": "antifibrotic",               # in the same antifibrotic pipeline bucket as pirfenidone
    "gc1008": "antifibrotic",               # fresolimumab, anti-TGF-beta antibody
    "dwn12088": "antifibrotic",             # targets collagen synthesis directly
    "cc90001": "antifibrotic",              # JNK inhibitor
    "cc930": "antifibrotic",                # earlier JNK inhibitor from the same program

    # Drugs that work on the pulmonary vasculature rather than fibrosis itself
    "bosentan": "endothelin_receptor_antagonist",
    "macitentan": "endothelin_receptor_antagonist",
    "act064992": "endothelin_receptor_antagonist",  # macitentan's development code
    "ambrisentan": "endothelin_receptor_antagonist",
    "sildenafil": "pde_inhibitor",
    "sildenafil citrate": "pde_inhibitor",

    # Immune-modulating drugs, several borrowed from oncology/rheum
    "cyclophosphamide": "immunosuppressant",
    "azathioprine": "immunosuppressant",
    "rituximab": "immunosuppressant",
    "thalidomide": "immunosuppressant",
    "sirolimus": "immunosuppressant",
    "alemtuzumab": "immunosuppressant",
    "belumosudil": "immunosuppressant",
    "vay736": "immunosuppressant",
    "lebrikizumab": "immunosuppressant",     # anti-IL-13
    "qax576": "immunosuppressant",           # also anti-IL-13
    "axatilimab": "immunosuppressant",       # anti-CSF-1R
    "garadacimab": "immunosuppressant",      # anti-factor XIIa
    "atezolizumab": "immunosuppressant",     # checkpoint inhibitor
    "bevacizumab": "immunosuppressant",      # anti-VEGF
    "etanercept": "immunosuppressant",       # TNF inhibitor
    "simtuzumab": "immunosuppressant",       # anti-LOXL2
    "jaktinib hydrochloride tablets": "immunosuppressant",  # JAK inhibitor

    # Standard corticosteroids
    "methylprednisolone": "anti_inflammatory",
    "dexamethasone": "anti_inflammatory",
    "prednisone": "anti_inflammatory",
    "prednisolone": "anti_inflammatory",
    "azapred": "anti_inflammatory",

    "azithromycin": "antibiotic",
    "cotrimoxazole": "antibiotic",
    "cotrimoxazole or doxycycline": "antibiotic",
    "doxycycline": "antibiotic",
    "minocycline": "antibiotic",

    "warfarin": "anticoagulant",
    "dabigatran": "anticoagulant",
    "art123": "anticoagulant",               # thrombomodulin alfa

    # Established drugs from other disease areas being tested off-label for IPF
    "metformin": "repurposed_other",
    "losartan": "repurposed_other",
    "omeprazole": "repurposed_other",
    "lansoprazole": "repurposed_other",
    "octreotide": "repurposed_other",
    "tamoxifen": "repurposed_other",
    "danazol": "repurposed_other",
    "nebivolol": "repurposed_other",
    "paroxetine": "repurposed_other",
    "zileuton": "repurposed_other",
    "imatinib mesylate": "repurposed_other",
    "dasatinib quercetin": "repurposed_other",
    "venetoclax": "repurposed_other",
    "fludarabine": "repurposed_other",
    "thiotepa": "repurposed_other",
    "valganciclovir": "repurposed_other",
    "hydroxyurea": "repurposed_other",
    "gbt440": "repurposed_other",            # voxelotor, originally a sickle cell drug

    # Imaging/diagnostic tools that show up as "interventions" but aren't treatments
    "gadoterate meglumine": "diagnostic_agent",
    "mri": "diagnostic_agent",
    "genetic analysis": "diagnostic_agent",
    "hyperpolarized xe129": "diagnostic_agent",

    # Symptom management / quality-of-life support, not disease-modifying
    "oxygen": "supportive_care",
    "medical air": "supportive_care",
    "nitric oxide": "supportive_care",
    "n acetylcysteine": "supportive_care",
    "n acetyl cysteine": "supportive_care",
    "vitamin c tablets": "supportive_care",
    "nicotinamide riboside": "supportive_care",
    "salbutamol": "supportive_care",
    "morphine sulfate": "supportive_care",
    "morphine hydrochloride": "supportive_care",
    "zinc": "supportive_care",
    "gefapixant": "supportive_care",          # for cough control, not the fibrosis itself
    "pulmonary rehabilitation": "supportive_care",
    "no intervention": "supportive_care",
    "inhaled treprostinil": "supportive_care",
    "treprostinil ultrasonic nebulizer": "supportive_care",
    "treprostinil sodium for inhalation": "supportive_care",
    "inopulse": "supportive_care",
    "oxymizer compared to cnc": "supportive_care",
}


def normalize_drug_name(name):
    """Strips dosages, punctuation, and formatting cruft so the same drug
    matches regardless of how a given trial happened to write it out."""
    if not name:
        return None
    n = name.lower()
    n = re.sub(r'\d+(\.\d+)?\s*(mg|mcg|ml|g|%)', '', n)
    n = re.sub(r'[®()]', '', n)
    n = re.sub(r'[^a-z0-9\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def get_mechanism_class(intervention_name):
    normalized = normalize_drug_name(intervention_name)
    if not normalized:
        return "unclassified"

    if normalized in MECHANISM_MAP:
        return MECHANISM_MAP[normalized]

    # Placebo/vehicle/sham arms aren't a "mechanism" at all, so they get their own bucket
    if any(term in normalized for term in ["placebo", "vehicle", "sham", "control", "untreated", "usual", "matching"]):
        return "comparator"

    # Combo arms that mention a known antifibrotic by name should still count as antifibrotic
    if "nintedanib" in normalized or "pirfenidone" in normalized:
        return "antifibrotic"

    # Anything left is a compound code or early pipeline drug without solid public data -
    # better to flag it honestly than force a guess
    return "investigational_unclassified"


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT intervention_id, intervention_name FROM interventions")
    rows = cur.fetchall()

    counts = {}
    for intervention_id, name in rows:
        mech_class = get_mechanism_class(name)
        counts[mech_class] = counts.get(mech_class, 0) + 1
        cur.execute(
            "UPDATE interventions SET mechanism_class = %s WHERE intervention_id = %s",
            (mech_class, intervention_id)
        )

    conn.commit()
    cur.close()
    conn.close()

    print("Mechanism class tagging complete.\n")
    for mech_class, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {mech_class}: {count}")


if __name__ == "__main__":
    main()