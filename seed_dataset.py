import time
import requests

API_URL = "http://127.0.0.1:5000/api/inventory/bulk"
AUTO_REPEAT_SECONDS = 0  # Set e.g. 300 to auto-push every 5 mins; 0 runs once immediately

HOSPITAL_DATASET: list[dict[str, object]] = [
    # --- Medicines (35 items) ---
    {"name": "Amoxicillin 250mg Capsules", "category": "Medicines", "quantity": 600, "unit": "Capsules"},
    {"name": "Amoxicillin + Clavulanate 625mg", "category": "Medicines", "quantity": 420, "unit": "Tablets"},
    {"name": "Ibuprofen 400mg", "category": "Medicines", "quantity": 25, "unit": "Tablets"},
    {"name": "Azithromycin 500mg", "category": "Medicines", "quantity": 180, "unit": "Tablets"},
    {"name": "Epinephrine Auto-Injector (0.3mg)", "category": "Medicines", "quantity": 15, "unit": "Units"},
    {"name": "Insulin Regular (100 IU/mL)", "category": "Medicines", "quantity": 45, "unit": "Vials"},
    {"name": "Insulin Glargine Pen", "category": "Medicines", "quantity": 38, "unit": "Pens"},
    {"name": "Ceftriaxone 1g Injection", "category": "Medicines", "quantity": 120, "unit": "Vials"},
    {"name": "Cefotaxime 1g Injection", "category": "Medicines", "quantity": 95, "unit": "Vials"},
    {"name": "Metronidazole 400mg", "category": "Medicines", "quantity": 310, "unit": "Tablets"},
    {"name": "Ciprofloxacin 500mg", "category": "Medicines", "quantity": 240, "unit": "Tablets"},
    {"name": "Omeprazole 40mg Capsules", "category": "Medicines", "quantity": 520, "unit": "Capsules"},
    {"name": "Pantoprazole 40mg IV Vial", "category": "Medicines", "quantity": 85, "unit": "Vials"},
    {"name": "Ondansetron 4mg Injection", "category": "Medicines", "quantity": 140, "unit": "Ampoules"},
    {"name": "Morphine Sulfate 10mg/mL", "category": "Medicines", "quantity": 18, "unit": "Ampoules"},
    {"name": "Diclofenac Sodium 75mg Injection", "category": "Medicines", "quantity": 160, "unit": "Ampoules"},
    {"name": "Atropine Sulfate 0.6mg/mL", "category": "Medicines", "quantity": 30, "unit": "Ampoules"},
    {"name": "Adrenaline 1mg/mL Injection", "category": "Medicines", "quantity": 42, "unit": "Ampoules"},
    {"name": "Heparin Sodium 5000 IU/mL", "category": "Medicines", "quantity": 28, "unit": "Vials"},
    {"name": "Aspirin 75mg Enteric Coated", "category": "Medicines", "quantity": 750, "unit": "Tablets"},
    {"name": "Clopidogrel 75mg", "category": "Medicines", "quantity": 290, "unit": "Tablets"},
    {"name": "Amlodipine 5mg", "category": "Medicines", "quantity": 480, "unit": "Tablets"},
    {"name": "Losartan 50mg", "category": "Medicines", "quantity": 360, "unit": "Tablets"},
    {"name": "Metformin 500mg SR", "category": "Medicines", "quantity": 640, "unit": "Tablets"},
    {"name": "Salbutamol Nebulizer Solution", "category": "Medicines", "quantity": 110, "unit": "Vials"},
    {"name": "Budesonide Respules 0.5mg", "category": "Medicines", "quantity": 35, "unit": "Packs"},
    {"name": "Hydrocortisone Sodium Succinate 100mg", "category": "Medicines", "quantity": 65, "unit": "Vials"},
    {"name": "Dexamethasone 4mg/mL Injection", "category": "Medicines", "quantity": 190, "unit": "Ampoules"},
    {"name": "Furosemide 20mg/2mL Injection", "category": "Medicines", "quantity": 130, "unit": "Ampoules"},
    {"name": "Tranexamic Acid 500mg Injection", "category": "Medicines", "quantity": 48, "unit": "Ampoules"},
    {"name": "Vitamin K1 (Phytomenadione) 10mg", "category": "Medicines", "quantity": 24, "unit": "Ampoules"},
    {"name": "Calcium Gluconate 10% Injection", "category": "Medicines", "quantity": 55, "unit": "Ampoules"},
    {"name": "Potassium Chloride 15% Concentrate", "category": "Medicines", "quantity": 40, "unit": "Ampoules"},
    {"name": "Magnesium Sulfate 50% Injection", "category": "Medicines", "quantity": 33, "unit": "Ampoules"},
    {"name": "Tetanus Toxoid Vaccine", "category": "Medicines", "quantity": 125, "unit": "Vials"},

    # --- PPE (20 items) ---
    {"name": "N95 Respirator Masks", "category": "PPE", "quantity": 40, "unit": "Pieces"},
    {"name": "Isolation Gowns (Disposable)", "category": "PPE", "quantity": 85, "unit": "Pieces"},
    {"name": "Face Shields", "category": "PPE", "quantity": 22, "unit": "Units"},
    {"name": "Sterile Nitrile Gloves (L)", "category": "PPE", "quantity": 300, "unit": "Pairs"},
    {"name": "Sterile Nitrile Gloves (S)", "category": "PPE", "quantity": 220, "unit": "Pairs"},
    {"name": "Shoe Covers (Disposable)", "category": "PPE", "quantity": 400, "unit": "Pairs"},
    {"name": "Surgical Bouffant Caps", "category": "PPE", "quantity": 500, "unit": "Pieces"},
    {"name": "3-Ply Surgical Procedure Masks", "category": "PPE", "quantity": 1500, "unit": "Pieces"},
    {"name": "Lead Apron (Radiation Protection)", "category": "PPE", "quantity": 8, "unit": "Units"},
    {"name": "Chemical Splash Goggles", "category": "PPE", "quantity": 29, "unit": "Units"},
    {"name": "Sterile Surgical Gowns (XL)", "category": "PPE", "quantity": 75, "unit": "Pieces"},
    {"name": "Examination Latex Gloves (M)", "category": "PPE", "quantity": 450, "unit": "Pairs"},
    {"name": "Long Cuff Sterile Gloves", "category": "PPE", "quantity": 60, "unit": "Pairs"},
    {"name": "Full-Body Coverall Suit", "category": "PPE", "quantity": 19, "unit": "Units"},
    {"name": "Plastic Aprons (Waterproof)", "category": "PPE", "quantity": 260, "unit": "Pieces"},
    {"name": "Patient Isolation Capes", "category": "PPE", "quantity": 95, "unit": "Pieces"},
    {"name": "Sterile Shoe Booties", "category": "PPE", "quantity": 180, "unit": "Pairs"},
    {"name": "Fume/Respirator Filter Cartridges", "category": "PPE", "quantity": 34, "unit": "Pairs"},
    {"name": "PAPR Hood Assembly", "category": "PPE", "quantity": 6, "unit": "Units"},
    {"name": "Visitor Disposable Masks", "category": "PPE", "quantity": 800, "unit": "Pieces"},

    # --- Equipment (25 items) ---
    {"name": "Pulse Oximeter", "category": "Equipment", "quantity": 20, "unit": "Units"},
    {"name": "Digital Blood Pressure Monitor", "category": "Equipment", "quantity": 18, "unit": "Units"},
    {"name": "Disposable Syringes (5mL)", "category": "Equipment", "quantity": 950, "unit": "Units"},
    {"name": "Disposable Syringes (10mL)", "category": "Equipment", "quantity": 620, "unit": "Units"},
    {"name": "Insulin Syringes (1mL U-100)", "category": "Equipment", "quantity": 410, "unit": "Units"},
    {"name": "IV Cannula (20G)", "category": "Equipment", "quantity": 240, "unit": "Units"},
    {"name": "IV Cannula (22G)", "category": "Equipment", "quantity": 280, "unit": "Units"},
    {"name": "IV Cannula (18G)", "category": "Equipment", "quantity": 135, "unit": "Units"},
    {"name": "Sterile Gauze Pads (4x4)", "category": "Equipment", "quantity": 350, "unit": "Packs"},
    {"name": "Nebulizer Mask Kit", "category": "Equipment", "quantity": 32, "unit": "Sets"},
    {"name": "Scalpel Blades (#15 Sterile)", "category": "Equipment", "quantity": 210, "unit": "Units"},
    {"name": "Suture Kit (Nylon 3-0)", "category": "Equipment", "quantity": 72, "unit": "Packs"},
    {"name": "Foley Catheter (16Fr Silicone)", "category": "Equipment", "quantity": 44, "unit": "Units"},
    {"name": "Urine Collection Bag (2000mL)", "category": "Equipment", "quantity": 115, "unit": "Units"},
    {"name": "Nasogastric Feeding Tube (14Fr)", "category": "Equipment", "quantity": 39, "unit": "Units"},
    {"name": "Endotracheal Tube (7.5mm Cuffed)", "category": "Equipment", "quantity": 27, "unit": "Units"},
    {"name": "Oxygen Nasal Cannula", "category": "Equipment", "quantity": 145, "unit": "Units"},
    {"name": "Non-Rebreather Oxygen Mask", "category": "Equipment", "quantity": 58, "unit": "Units"},
    {"name": "ECG Electrodes (Adult Pack)", "category": "Equipment", "quantity": 310, "unit": "Packs"},
    {"name": "Glucometer Test Strips", "category": "Equipment", "quantity": 185, "unit": "Boxes"},
    {"name": "Lancets (Sterile Safety)", "category": "Equipment", "quantity": 500, "unit": "Units"},
    {"name": "Tourniquet Band", "category": "Equipment", "quantity": 46, "unit": "Units"},
    {"name": "Elastic Crepe Bandage (6-inch)", "category": "Equipment", "quantity": 92, "unit": "Rolls"},
    {"name": "Medical Adhesive Tape (1-inch)", "category": "Equipment", "quantity": 155, "unit": "Rolls"},
    {"name": "Clinical Stethoscope", "category": "Equipment", "quantity": 14, "unit": "Units"},

    # --- Fluids (20 items) ---
    {"name": "Ringer Lactate IV Solution (500mL)", "category": "Fluids", "quantity": 150, "unit": "Bottles"},
    {"name": "Dextrose 5% IV Fluid (500mL)", "category": "Fluids", "quantity": 95, "unit": "Bottles"},
    {"name": "Dextrose Normal Saline (DNS 500mL)", "category": "Fluids", "quantity": 120, "unit": "Bottles"},
    {"name": "Normal Saline Flush Syringes (10mL)", "category": "Fluids", "quantity": 180, "unit": "Units"},
    {"name": "Chlorhexidine Antiseptic Solution", "category": "Fluids", "quantity": 28, "unit": "Bottles"},
    {"name": "Povidone Iodine Solution 10% (500mL)", "category": "Fluids", "quantity": 64, "unit": "Bottles"},
    {"name": "Isopropyl Alcohol Rub 70% (1L)", "category": "Fluids", "quantity": 88, "unit": "Bottles"},
    {"name": "Hand Sanitizer Gel (500mL Pump)", "category": "Fluids", "quantity": 110, "unit": "Bottles"},
    {"name": "Mannitol 20% IV Infusion (100mL)", "category": "Fluids", "quantity": 36, "unit": "Bottles"},
    {"name": "Metronidazole IV Infusion 500mg (100mL)", "category": "Fluids", "quantity": 78, "unit": "Bottles"},
    {"name": "Ciprofloxacin IV Infusion 200mg (100mL)", "category": "Fluids", "quantity": 52, "unit": "Bottles"},
    {"name": "Paracetamol IV Infusion 1g (100mL)", "category": "Fluids", "quantity": 135, "unit": "Bottles"},
    {"name": "Sterile Water for Injection (10mL)", "category": "Fluids", "quantity": 340, "unit": "Ampoules"},
    {"name": "Sodium Bicarbonate 8.4% IV (50mL)", "category": "Fluids", "quantity": 21, "unit": "Vials"},
    {"name": "Albumin Human 20% Solution (50mL)", "category": "Fluids", "quantity": 12, "unit": "Vials"},
    {"name": "Gelatin Plasma Substitute (500mL)", "category": "Fluids", "quantity": 31, "unit": "Bottles"},
    {"name": "Hydrogen Peroxide 6% Antiseptic (500mL)", "category": "Fluids", "quantity": 49, "unit": "Bottles"},
    {"name": "Sodium Hypochlorite Disinfectant (5L)", "category": "Fluids", "quantity": 26, "unit": "Bottles"},
    {"name": "Ultrasound Gel Bottle (250mL)", "category": "Fluids", "quantity": 43, "unit": "Bottles"},
    {"name": "Oral Rehydration Salts (ORS) Sachets", "category": "Fluids", "quantity": 420, "unit": "Sachets"},
]

assert len(HOSPITAL_DATASET) == 100, f"Expected 100 items, got {len(HOSPITAL_DATASET)}"


def sync_dataset() -> None:
    try:
        response = requests.post(API_URL, json=HOSPITAL_DATASET, timeout=15)
        data = response.json()
        print("Status Code:", response.status_code)
        print("Message:", data.get("message"))
        print("Total items returned:", len(data.get("items", [])))
    except requests.RequestException as exc:
        print(f"Failed to connect to Flask API: {exc}")


def main() -> None:
    if AUTO_REPEAT_SECONDS <= 0:
        sync_dataset()
        return

    print(f"Running automatic sync every {AUTO_REPEAT_SECONDS} seconds (press Ctrl+C to stop)...")
    while True:
        sync_dataset()
        time.sleep(AUTO_REPEAT_SECONDS)


if __name__ == "__main__":
    main()