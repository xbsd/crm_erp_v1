"""Reference data for realistic electronic components industry simulation.

Real-world public-domain references:
- Account names: Fortune 1000 industrial / automotive / aerospace / consumer-electronics buyers
- Product families: standard semiconductor / electronic-component taxonomy
- Test standards: real JEDEC, AEC-Q, MIL-STD, IPC standards
- Failure modes: standard FMEA categorization
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Customer / Account universe
# ---------------------------------------------------------------------------
# Realistic blend of automotive, aerospace, industrial, medical, and consumer
# electronics buyers — the kinds of companies that buy power-management,
# sensors, MCUs, etc.  Names are real publicly-listed companies; data values
# (revenue, opportunity counts) are SYNTHETIC.
ACCOUNT_UNIVERSE = [
    # --- Automotive (high volume, AEC-Q100 driven) ---
    {"name": "Tesla, Inc.",              "industry": "Automotive",  "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Ford Motor Company",       "industry": "Automotive",  "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "General Motors",           "industry": "Automotive",  "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Toyota Motor Corporation", "industry": "Automotive",  "segment": "Enterprise", "country": "Japan",   "key": True},
    {"name": "Volkswagen AG",            "industry": "Automotive",  "segment": "Enterprise", "country": "Germany", "key": True},
    {"name": "BMW Group",                "industry": "Automotive",  "segment": "Enterprise", "country": "Germany", "key": True},
    {"name": "Stellantis N.V.",          "industry": "Automotive",  "segment": "Enterprise", "country": "Netherlands", "key": False},
    {"name": "Rivian Automotive",        "industry": "Automotive",  "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Lucid Motors",             "industry": "Automotive",  "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Hyundai Motor Company",    "industry": "Automotive",  "segment": "Enterprise", "country": "Korea",   "key": True},
    {"name": "Honda Motor Co., Ltd.",    "industry": "Automotive",  "segment": "Enterprise", "country": "Japan",   "key": False},
    {"name": "Denso Corporation",        "industry": "Automotive",  "segment": "Enterprise", "country": "Japan",   "key": True},
    {"name": "Continental AG",           "industry": "Automotive",  "segment": "Enterprise", "country": "Germany", "key": False},
    {"name": "Bosch Mobility",           "industry": "Automotive",  "segment": "Enterprise", "country": "Germany", "key": True},

    # --- Aerospace & Defense (long life, low volume, MIL-STD) ---
    {"name": "The Boeing Company",       "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Lockheed Martin",          "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Raytheon Technologies",    "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Northrop Grumman",         "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Airbus SE",                "industry": "Aerospace",   "segment": "Enterprise", "country": "France",  "key": True},
    {"name": "General Dynamics",         "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "SpaceX",                   "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Honeywell Aerospace",      "industry": "Aerospace",   "segment": "Enterprise", "country": "USA",     "key": False},

    # --- Industrial / Automation ---
    {"name": "Siemens AG",               "industry": "Industrial",  "segment": "Enterprise", "country": "Germany", "key": True},
    {"name": "ABB Ltd.",                 "industry": "Industrial",  "segment": "Enterprise", "country": "Switzerland","key": True},
    {"name": "Schneider Electric",       "industry": "Industrial",  "segment": "Enterprise", "country": "France",  "key": True},
    {"name": "Emerson Electric",         "industry": "Industrial",  "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Rockwell Automation",      "industry": "Industrial",  "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Honeywell International",  "industry": "Industrial",  "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Eaton Corporation",        "industry": "Industrial",  "segment": "Enterprise", "country": "Ireland", "key": False},
    {"name": "Mitsubishi Electric",      "industry": "Industrial",  "segment": "Enterprise", "country": "Japan",   "key": False},
    {"name": "Fanuc Corporation",        "industry": "Industrial",  "segment": "Mid-Market", "country": "Japan",   "key": False},
    {"name": "Yaskawa Electric",         "industry": "Industrial",  "segment": "Mid-Market", "country": "Japan",   "key": False},

    # --- Medical Devices ---
    {"name": "Medtronic plc",            "industry": "Medical",     "segment": "Enterprise", "country": "Ireland", "key": True},
    {"name": "GE HealthCare",            "industry": "Medical",     "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Philips Healthcare",       "industry": "Medical",     "segment": "Enterprise", "country": "Netherlands","key": False},
    {"name": "Siemens Healthineers",     "industry": "Medical",     "segment": "Enterprise", "country": "Germany", "key": False},
    {"name": "Abbott Laboratories",      "industry": "Medical",     "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Stryker Corporation",      "industry": "Medical",     "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Boston Scientific",        "industry": "Medical",     "segment": "Mid-Market", "country": "USA",     "key": False},

    # --- Consumer Electronics ---
    {"name": "Apple Inc.",               "industry": "Consumer",    "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Samsung Electronics",      "industry": "Consumer",    "segment": "Enterprise", "country": "Korea",   "key": True},
    {"name": "Sony Group Corporation",   "industry": "Consumer",    "segment": "Enterprise", "country": "Japan",   "key": False},
    {"name": "LG Electronics",           "industry": "Consumer",    "segment": "Enterprise", "country": "Korea",   "key": False},
    {"name": "Xiaomi Corporation",       "industry": "Consumer",    "segment": "Enterprise", "country": "China",   "key": False},
    {"name": "Dell Technologies",        "industry": "Consumer",    "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "HP Inc.",                  "industry": "Consumer",    "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Lenovo Group",             "industry": "Consumer",    "segment": "Enterprise", "country": "China",   "key": False},

    # --- Telecom / Networking ---
    {"name": "Cisco Systems",            "industry": "Telecom",     "segment": "Enterprise", "country": "USA",     "key": True},
    {"name": "Ericsson",                 "industry": "Telecom",     "segment": "Enterprise", "country": "Sweden",  "key": False},
    {"name": "Nokia Corporation",        "industry": "Telecom",     "segment": "Enterprise", "country": "Finland", "key": False},
    {"name": "Juniper Networks",         "industry": "Telecom",     "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Arista Networks",          "industry": "Telecom",     "segment": "Mid-Market", "country": "USA",     "key": False},

    # --- Energy / Renewables ---
    {"name": "Vestas Wind Systems",      "industry": "Energy",      "segment": "Enterprise", "country": "Denmark", "key": True},
    {"name": "First Solar",              "industry": "Energy",      "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "SunPower Corporation",     "industry": "Energy",      "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Enphase Energy",           "industry": "Energy",      "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Tesla Energy",             "industry": "Energy",      "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "GE Vernova",               "industry": "Energy",      "segment": "Enterprise", "country": "USA",     "key": True},

    # --- Mid-market & SMB (varied) ---
    {"name": "iRobot Corporation",       "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "GoPro Inc.",               "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Fitbit (Google)",          "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Garmin Ltd.",              "industry": "Consumer",    "segment": "Mid-Market", "country": "Switzerland","key": False},
    {"name": "Whirlpool Corporation",    "industry": "Consumer",    "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Dyson Ltd.",               "industry": "Consumer",    "segment": "Mid-Market", "country": "UK",      "key": False},
    {"name": "Bose Corporation",         "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Logitech International",   "industry": "Consumer",    "segment": "Mid-Market", "country": "Switzerland","key": False},
    {"name": "Roomba Robotics LLC",      "industry": "Consumer",    "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "Skydio Inc.",              "industry": "Aerospace",   "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "Joby Aviation",            "industry": "Aerospace",   "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Anduril Industries",       "industry": "Aerospace",   "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Peloton Interactive",      "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Sonos Inc.",               "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Ring LLC (Amazon)",        "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Nest Labs (Google)",       "industry": "Consumer",    "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Arlo Technologies",        "industry": "Consumer",    "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "Wahl Clipper",             "industry": "Consumer",    "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "iRhythm Technologies",     "industry": "Medical",     "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Insulet Corporation",      "industry": "Medical",     "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Dexcom Inc.",              "industry": "Medical",     "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Penumbra Inc.",            "industry": "Medical",     "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "iRhythm Cardiology Lab",   "industry": "Medical",     "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "Velo3D Inc.",              "industry": "Industrial",  "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "Desktop Metal",            "industry": "Industrial",  "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Markforged Holding",       "industry": "Industrial",  "segment": "SMB",        "country": "USA",     "key": False},
    {"name": "Cognex Corporation",       "industry": "Industrial",  "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Trimble Inc.",             "industry": "Industrial",  "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Keysight Technologies",    "industry": "Industrial",  "segment": "Enterprise", "country": "USA",     "key": False},
    {"name": "Teradyne Inc.",            "industry": "Industrial",  "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Bloom Energy",             "industry": "Energy",      "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "ChargePoint Holdings",     "industry": "Energy",      "segment": "Mid-Market", "country": "USA",     "key": False},
    {"name": "Wallbox N.V.",             "industry": "Energy",      "segment": "SMB",        "country": "Spain",   "key": False},
    {"name": "Generac Holdings",         "industry": "Energy",      "segment": "Mid-Market", "country": "USA",     "key": False},
]

# ---------------------------------------------------------------------------
# Sales rep / user data
# ---------------------------------------------------------------------------
SALES_ROLES = [
    ("VP Sales", 2),
    ("Sales Manager", 6),
    ("Account Executive", 18),
    ("Sales Engineer", 6),
    ("SDR", 8),
]

REGIONS = ["NA", "EMEA", "APAC", "LATAM"]

# ---------------------------------------------------------------------------
# Product catalog — realistic semiconductor / electronic-component taxonomy
# ---------------------------------------------------------------------------
# Each entry: (family, category, sku_prefix, base_price_range, target_industries)
PRODUCT_CATALOG = [
    # --- Power Management ---
    {"family": "Power Management", "category": "DC-DC Buck Converter",  "sku": "PMB",  "base_price": (1.20, 8.50),  "industries": ["Automotive", "Industrial", "Consumer"]},
    {"family": "Power Management", "category": "DC-DC Boost Converter", "sku": "PMS",  "base_price": (1.50, 9.20),  "industries": ["Industrial", "Consumer", "Energy"]},
    {"family": "Power Management", "category": "LDO Regulator",         "sku": "LDO",  "base_price": (0.45, 3.20),  "industries": ["Consumer", "Industrial", "Medical"]},
    {"family": "Power Management", "category": "Battery Management IC", "sku": "BMS",  "base_price": (2.80, 15.00), "industries": ["Automotive", "Consumer", "Energy"]},
    {"family": "Power Management", "category": "Gate Driver",           "sku": "GDR",  "base_price": (1.80, 7.40),  "industries": ["Automotive", "Industrial", "Energy"]},
    {"family": "Power Management", "category": "PMIC",                  "sku": "PMI",  "base_price": (3.50, 22.00), "industries": ["Consumer", "Industrial", "Medical"]},

    # --- Sensors ---
    {"family": "Sensors", "category": "Temperature Sensor",     "sku": "TSN", "base_price": (0.85, 6.40),  "industries": ["Automotive", "Industrial", "Consumer", "Medical"]},
    {"family": "Sensors", "category": "Pressure Sensor",        "sku": "PSN", "base_price": (3.20, 18.00), "industries": ["Automotive", "Industrial", "Medical"]},
    {"family": "Sensors", "category": "Hall Effect Sensor",     "sku": "HAL", "base_price": (0.70, 4.20),  "industries": ["Automotive", "Industrial", "Consumer"]},
    {"family": "Sensors", "category": "Accelerometer / IMU",    "sku": "IMU", "base_price": (2.40, 14.00), "industries": ["Automotive", "Aerospace", "Consumer"]},
    {"family": "Sensors", "category": "Gas Sensor",             "sku": "GAS", "base_price": (4.20, 28.00), "industries": ["Industrial", "Medical"]},
    {"family": "Sensors", "category": "Light/Proximity Sensor", "sku": "LPS", "base_price": (0.50, 3.80),  "industries": ["Consumer", "Industrial"]},
    {"family": "Sensors", "category": "Current Sensor",         "sku": "CSN", "base_price": (1.40, 8.20),  "industries": ["Automotive", "Energy", "Industrial"]},

    # --- Microcontrollers ---
    {"family": "MCU & Processors", "category": "32-bit ARM MCU",  "sku": "MCU", "base_price": (1.10, 12.00), "industries": ["Automotive", "Industrial", "Consumer", "Medical"]},
    {"family": "MCU & Processors", "category": "8/16-bit MCU",    "sku": "M16", "base_price": (0.40, 3.20),  "industries": ["Consumer", "Industrial"]},
    {"family": "MCU & Processors", "category": "Automotive MCU",  "sku": "AMC", "base_price": (4.50, 28.00), "industries": ["Automotive"]},
    {"family": "MCU & Processors", "category": "DSP",             "sku": "DSP", "base_price": (8.00, 52.00), "industries": ["Industrial", "Aerospace", "Telecom"]},
    {"family": "MCU & Processors", "category": "FPGA",            "sku": "FPG", "base_price": (15.00, 380.00), "industries": ["Aerospace", "Telecom", "Industrial"]},

    # --- Memory ---
    {"family": "Memory", "category": "NOR Flash",     "sku": "NOR", "base_price": (0.65, 12.00), "industries": ["Automotive", "Industrial", "Consumer"]},
    {"family": "Memory", "category": "NAND Flash",    "sku": "NND", "base_price": (1.50, 28.00), "industries": ["Consumer", "Industrial"]},
    {"family": "Memory", "category": "SRAM",          "sku": "SRM", "base_price": (1.20, 18.00), "industries": ["Industrial", "Telecom"]},
    {"family": "Memory", "category": "EEPROM",        "sku": "EPR", "base_price": (0.30, 2.80),  "industries": ["Automotive", "Industrial", "Consumer"]},

    # --- Interface / Connectivity ---
    {"family": "Connectivity", "category": "Bluetooth SoC",  "sku": "BLE", "base_price": (1.80, 8.40),  "industries": ["Consumer", "Medical", "Industrial"]},
    {"family": "Connectivity", "category": "Wi-Fi Module",   "sku": "WIF", "base_price": (3.20, 18.00), "industries": ["Consumer", "Industrial"]},
    {"family": "Connectivity", "category": "Ethernet PHY",   "sku": "ETH", "base_price": (2.40, 14.00), "industries": ["Industrial", "Telecom", "Automotive"]},
    {"family": "Connectivity", "category": "CAN Transceiver","sku": "CAN", "base_price": (0.90, 4.80),  "industries": ["Automotive", "Industrial"]},
    {"family": "Connectivity", "category": "USB Controller", "sku": "USB", "base_price": (0.70, 5.20),  "industries": ["Consumer", "Industrial"]},

    # --- Analog / Mixed Signal ---
    {"family": "Analog", "category": "Op-Amp",        "sku": "OPA", "base_price": (0.30, 4.80),  "industries": ["Industrial", "Medical", "Consumer"]},
    {"family": "Analog", "category": "ADC",           "sku": "ADC", "base_price": (1.80, 32.00), "industries": ["Industrial", "Medical", "Aerospace"]},
    {"family": "Analog", "category": "DAC",           "sku": "DAC", "base_price": (1.60, 28.00), "industries": ["Industrial", "Medical", "Telecom"]},
    {"family": "Analog", "category": "Comparator",    "sku": "CMP", "base_price": (0.40, 3.20),  "industries": ["Industrial", "Consumer"]},

    # --- Discrete Power ---
    {"family": "Discrete Power", "category": "MOSFET",       "sku": "MOS", "base_price": (0.20, 18.00), "industries": ["Automotive", "Industrial", "Energy"]},
    {"family": "Discrete Power", "category": "IGBT",         "sku": "IGB", "base_price": (3.50, 52.00), "industries": ["Industrial", "Energy", "Automotive"]},
    {"family": "Discrete Power", "category": "SiC MOSFET",   "sku": "SIC", "base_price": (8.00, 95.00), "industries": ["Automotive", "Energy"]},
    {"family": "Discrete Power", "category": "GaN HEMT",     "sku": "GAN", "base_price": (4.50, 60.00), "industries": ["Industrial", "Energy", "Telecom"]},
]

# ---------------------------------------------------------------------------
# Test / QA reference data
# ---------------------------------------------------------------------------
TEST_TYPES = [
    ("Electrical Parametric", "JESD22-A108", 168),
    ("High Temperature Operating Life (HTOL)", "JESD22-A108", 1000),
    ("Temperature Cycling", "JESD22-A104", 500),
    ("HAST (Humidity Accelerated Stress)", "JESD22-A110", 96),
    ("ESD HBM (Human Body Model)", "JESD22-A114", 1),
    ("ESD CDM (Charged Device Model)", "JESD22-C101", 1),
    ("Latch-Up", "JESD78", 1),
    ("Solder Reflow", "JESD22-A113", 1),
    ("Mechanical Shock", "MIL-STD-883 Method 2002", 1),
    ("Vibration", "MIL-STD-883 Method 2007", 4),
    ("Salt Spray Corrosion", "MIL-STD-810G", 96),
    ("Burn-In", "MIL-STD-883 Method 1015", 168),
    ("EMC Radiated Emissions", "FCC Part 15", 2),
    ("Functional Test", "Custom",  0.1),
]

FAILURE_MODES = [
    "Open Circuit", "Short Circuit", "Parametric Drift", "Thermal Runaway",
    "Latch-Up", "ESD Damage", "Solder Joint Failure", "Wire Bond Lift",
    "Die Crack", "Package Crack", "Moisture Ingress", "Tin Whiskers",
    "Electromigration", "Hot Carrier Injection", "Marginal Performance",
]

ROOT_CAUSE_CATEGORIES = ["Design", "Process", "Material", "Handling", "Application", "Unknown"]

RETURN_REASONS = [
    "Defective on Arrival", "Performance Below Spec", "Premature Field Failure",
    "Wrong Item Shipped", "Damaged in Transit", "Customer Application Error",
    "Quality Concern", "Reliability Concern", "Cosmetic Defect",
]

COMPLIANCE_STANDARDS = [
    ("UL 60950", "Safety", 36),
    ("CE Mark", "EU Conformity", 60),
    ("FCC Part 15", "EMC", 60),
    ("RoHS", "Environmental", 36),
    ("REACH", "Environmental", 36),
    ("AEC-Q100", "Automotive Reliability", 60),
    ("AEC-Q200", "Passive Components", 60),
    ("IATF 16949", "Automotive Quality System", 36),
    ("ISO 9001", "Quality Management", 36),
    ("ISO 13485", "Medical Devices", 36),
    ("MIL-STD-883", "Microcircuits", 60),
    ("JESD47", "Stress Test Qualification", 60),
]

# ---------------------------------------------------------------------------
# Opportunity / sales pipeline reference
# ---------------------------------------------------------------------------
OPP_STAGES = [
    ("Prospecting",       0.10, "Pipeline"),
    ("Qualification",     0.20, "Pipeline"),
    ("Needs Analysis",    0.35, "Pipeline"),
    ("Proposal",          0.50, "Best Case"),
    ("Negotiation",       0.75, "Commit"),
    ("Closed Won",        1.00, "Closed"),
    ("Closed Lost",       0.00, "Closed"),
]

LEAD_SOURCES = [
    "Web - Website Form", "Web - SEO/Organic", "Trade Show", "Partner Referral",
    "Cold Outreach", "Inbound Call", "Email Campaign", "LinkedIn", "Customer Referral",
    "Webinar", "Distributor", "Field Application Engineer",
]

LEAD_STATUSES = ["New", "Working", "Qualified", "Converted", "Disqualified"]

LOSS_REASONS = [
    "Lost to Competitor", "Budget Constraints", "No Decision",
    "Product Fit Issue", "Timing - Deferred", "Reliability Concerns",
    "Pricing Too High", "Delivery Timeline",
]

COMPETITORS = [
    "Texas Instruments", "Analog Devices", "STMicroelectronics", "NXP Semiconductors",
    "Infineon", "Renesas", "Microchip Technology", "ON Semiconductor",
    "Maxim Integrated", "Linear Technology",
]

# ---------------------------------------------------------------------------
# Industry → design requirements mapping (for "best product" matching)
# ---------------------------------------------------------------------------
INDUSTRY_REQUIREMENTS = {
    "Automotive": {
        "operating_temp_min_c": -40, "operating_temp_max_c": 125,
        "qualification": "AEC-Q100", "lifetime_yrs": 15,
        "typical_voltage_v": [3.3, 5.0, 12.0, 48.0],
        "key_certifications": ["AEC-Q100", "IATF 16949"],
    },
    "Aerospace": {
        "operating_temp_min_c": -55, "operating_temp_max_c": 125,
        "qualification": "MIL-STD-883", "lifetime_yrs": 25,
        "typical_voltage_v": [3.3, 5.0, 28.0],
        "key_certifications": ["MIL-STD-883", "DO-254"],
    },
    "Industrial": {
        "operating_temp_min_c": -40, "operating_temp_max_c": 85,
        "qualification": "JESD47", "lifetime_yrs": 10,
        "typical_voltage_v": [3.3, 5.0, 24.0],
        "key_certifications": ["UL 60950", "CE Mark", "RoHS"],
    },
    "Medical": {
        "operating_temp_min_c": 0, "operating_temp_max_c": 60,
        "qualification": "JESD47", "lifetime_yrs": 10,
        "typical_voltage_v": [3.3, 5.0],
        "key_certifications": ["ISO 13485", "IEC 60601"],
    },
    "Consumer": {
        "operating_temp_min_c": -10, "operating_temp_max_c": 70,
        "qualification": "JESD47", "lifetime_yrs": 5,
        "typical_voltage_v": [1.8, 3.3, 5.0],
        "key_certifications": ["FCC Part 15", "CE Mark", "RoHS"],
    },
    "Energy": {
        "operating_temp_min_c": -40, "operating_temp_max_c": 105,
        "qualification": "JESD47 + Field Reliability", "lifetime_yrs": 20,
        "typical_voltage_v": [12.0, 48.0, 400.0, 800.0],
        "key_certifications": ["UL 1741", "CE Mark"],
    },
    "Telecom": {
        "operating_temp_min_c": -40, "operating_temp_max_c": 85,
        "qualification": "Telcordia GR-468", "lifetime_yrs": 15,
        "typical_voltage_v": [3.3, 5.0, 48.0],
        "key_certifications": ["Telcordia GR-468", "ISO 9001"],
    },
}
