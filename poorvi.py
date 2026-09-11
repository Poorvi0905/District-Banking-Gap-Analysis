
import pandas as pd
import difflib

# ============================================================
# BANKING OUTLET GAP ANALYSIS
# CENSUS 2011 POPULATION + RBI 2026 BANKING OUTLETS
# ============================================================

CENSUS_FILE = "dataa/raw/DDW_PCA0000_2011_Indiastatedist.xlsx"
RBI_FILE = "dataa/raw/india.csv"

CENSUS_OUTPUT = "dataa/processed/census_district_population.csv"
FINAL_OUTPUT = "dataa/processed/district_banking_analysis.csv"
GAP_OUTPUT = "dataa/processed/district_banking_gap_analysis.csv"
STATE_OUTPUT = "dataa/processed/state_banking_analysis.csv"
UNMATCHED_OUTPUT = "dataa/processed/unmatched_districts.csv"
SPLIT_OUTPUT = "dataa/processed/district_split_mapping.csv"


# ============================================================
# HELPER FUNCTION
# ============================================================

def clean_text(series):
    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )


# ============================================================
# 1. LOAD CENSUS 2011 DATA
# ============================================================

print("\n" + "=" * 70)
print("1. LOADING CENSUS 2011 DATA")
print("=" * 70)

df = pd.read_excel(CENSUS_FILE)

# Keep district-level TOTAL population
districts = df[
    (df["Level"] == "DISTRICT") &
    (df["TRU"] == "Total")
].copy()

districts = districts[["State", "Name", "TOT_P"]]

districts = districts.rename(
    columns={
        "State": "State_Code",
        "Name": "District",
        "TOT_P": "Population"
    }
)

# Get state names
states = df[
    df["Level"] == "STATE"
][["State", "Name"]].copy()

states = states.drop_duplicates()

states = states.rename(
    columns={
        "State": "State_Code",
        "Name": "State"
    }
)

# Add state name
districts = districts.merge(
    states,
    on="State_Code",
    how="left"
)

districts = districts[
    ["State", "District", "Population"]
]

# Clean
districts["State"] = clean_text(districts["State"])
districts["District"] = clean_text(districts["District"])

print("Total Census districts:", len(districts))

print("\nFirst 10 Census districts:")
print(districts.head(10).to_string(index=False))

print("\nDuplicate Census districts:",
      districts.duplicated(
          subset=["State", "District"]
      ).sum())

print("\nMissing Census values:")
print(districts.isnull().sum())

# Save Census data
districts.to_csv(
    CENSUS_OUTPUT,
    index=False
)

print("\nCensus data saved:")
print(CENSUS_OUTPUT)


# ============================================================
# 2. LOAD RBI BANKING OUTLET DATA
# ============================================================

print("\n" + "=" * 70)
print("2. LOADING RBI BANKING DATA")
print("=" * 70)

bank_df = pd.read_csv(
    RBI_FILE,
    sep="|",
    encoding="utf-8-sig",
    low_memory=False
)

print("RBI rows:", len(bank_df))
print("RBI columns:", len(bank_df.columns))

# Keep required columns
bank_df = bank_df[
    [
        "State",
        "District",
        "Bank Name",
        "Banking Channel Type"
    ]
].copy()

bank_df["State"] = clean_text(bank_df["State"])
bank_df["District"] = clean_text(bank_df["District"])

print("\nTotal RBI banking outlets:", len(bank_df))

print(
    "Unique RBI State-District combinations:",
    bank_df[
        ["State", "District"]
    ].drop_duplicates().shape[0]
)

print("\nRBI states:")
print(
    bank_df["State"]
    .value_counts()
    .to_string()
)


# ============================================================
# 3. LOAD FULL RBI DATA FOR SUB-DISTRICT INFORMATION
# ============================================================

full_bank = pd.read_csv(
    RBI_FILE,
    sep="|",
    encoding="utf-8-sig",
    low_memory=False
)

for col in [
    "State",
    "District",
    "Sub District"
]:
    full_bank[col] = clean_text(full_bank[col])


# ============================================================
# 4. COUNT RBI BANKING OUTLETS
# ============================================================

print("\n" + "=" * 70)
print("3. COUNTING RBI BANKING OUTLETS")
print("=" * 70)

bank_counts = (
    full_bank
    .groupby(
        ["State", "District"]
    )
    .size()
    .reset_index(
        name="Banking_Outlets"
    )
)

print(
    "RBI State-District combinations:",
    len(bank_counts)
)

# ============================================================
# TEMPORARY CHECK — TELANGANA RBI DISTRICTS
# ============================================================
print("\n" + "=" * 70)
print("CHECKING TELANGANA RBI DISTRICTS")
print("=" * 70)

telangana_check = bank_counts[
    bank_counts["State"] == "TELANGANA"
].sort_values("District")

print(telangana_check.to_string(index=False))

# ============================================================
# 5. SPECIAL PUDUCHERRY HANDLING
# ============================================================

print("\n" + "=" * 70)
print("4. PUDUCHERRY CORRECTION")
print("=" * 70)

puducherry_data = full_bank[
    full_bank["State"] == "PUDUCHERRY"
].copy()

# Remove original Puducherry counts
bank_counts = bank_counts[
    bank_counts["State"] != "PUDUCHERRY"
].copy()

# Use Sub District
puducherry_data["Correct_District"] = (
    puducherry_data["Sub District"]
)

puducherry_valid = puducherry_data[
    puducherry_data["Correct_District"].isin(
        [
            "PUDUCHERRY",
            "KARAIKAL",
            "MAHE",
            "YANAM"
        ]
    )
].copy()

puducherry_counts = (
    puducherry_valid
    .groupby(
        [
            "State",
            "Correct_District"
        ]
    )
    .size()
    .reset_index(
        name="Banking_Outlets"
    )
)

puducherry_counts = puducherry_counts.rename(
    columns={
        "Correct_District": "District"
    }
)

bank_counts = pd.concat(
    [
        bank_counts,
        puducherry_counts
    ],
    ignore_index=True
)

print("\nCorrected Puducherry counts:")
print(
    bank_counts[
        bank_counts["State"] == "PUDUCHERRY"
    ].to_string(index=False)
)


# ============================================================
# 6. STATE REMAPPING
# ============================================================

print("\n" + "=" * 70)
print("5. STATE REMAPPING")
print("=" * 70)

state_remap = {

    # --------------------------------------------------------
    # Jammu & Kashmir -> Ladakh
    # --------------------------------------------------------

    ("JAMMU & KASHMIR", "LEH(LADAKH)"):
        "LADAKH",

    ("JAMMU & KASHMIR", "KARGIL"):
        "LADAKH",

    # --------------------------------------------------------
    # Union Territories
    # --------------------------------------------------------

    ("DAMAN & DIU", "DIU"):
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",

    ("DAMAN & DIU", "DAMAN"):
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",

    ("DADRA & NAGAR HAVELI", "DADRA & NAGAR HAVELI"):
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
}


def get_state_match(row):

    key = (
        row["State"],
        row["District"]
    )

    return state_remap.get(
        key,
        row["State"]
    )


districts["State_Match"] = districts.apply(
    get_state_match,
    axis=1
)

remapped = districts[
    districts["State"] != districts["State_Match"]
].copy()

print(
    "\nNumber of state remappings:",
    len(remapped)
)

if len(remapped) > 0:
    print(
        remapped[
            [
                "State",
                "District",
                "State_Match"
            ]
        ].to_string(index=False)
    )


# ============================================================
# 7. DISTRICT NAME MAPPING
# ============================================================

print("\n" + "=" * 70)
print("6. DISTRICT NAME MAPPING")
print("=" * 70)

district_name_mapping = {
     # --------------------------------------------------------
    # ASSAM
    # --------------------------------------------------------
    ("ASSAM", "SIVASAGAR"):
    "SIBSAGAR",

   ("ASSAM", "KARIMGANJ"):
    "SRIBHUMI",

   ("ASSAM", "KAMRUP METROPOLITAN"):
    "KAMRUP METROPOLITAN",
    # --------------------------------------------------------
    # JAMMU & KASHMIR
    # --------------------------------------------------------

    ("JAMMU & KASHMIR", "PUNCH"):
        "POONCH",

    ("JAMMU & KASHMIR", "LEH(LADAKH)"):
        "LEH",

    ("JAMMU & KASHMIR", "KARGIL"):
        "KARGIL",

    ("JAMMU & KASHMIR", "BARAMULA"):
        "BARAMULLA",

    ("JAMMU & KASHMIR", "BANDIPORE"):
        "BANDIPORA",

    ("JAMMU & KASHMIR", "SHUPIYAN"):
        "SHOPIAN",

    # --------------------------------------------------------
    # HIMACHAL PRADESH
    # --------------------------------------------------------

    ("HIMACHAL PRADESH", "KULLU"):
        "KULU",

    # --------------------------------------------------------
    # PUNJAB
    # --------------------------------------------------------

    ("PUNJAB", "FIROZPUR"):
        "FEROZPUR",

    # --------------------------------------------------------
    # UTTARAKHAND
    # --------------------------------------------------------

    ("UTTARAKHAND", "HARDWAR"):
        "HARIDWAR",

    ("UTTARAKHAND", "UTTARKASHI"):
        "UTTAR KASHI",

    ("UTTARAKHAND", "DEHRADUN"):
        "DEHRA DUN",

    # --------------------------------------------------------
    # HARYANA
    # --------------------------------------------------------

    ("HARYANA", "GURGAON"):
        "GURUGRAM",

    ("HARYANA", "MEWAT"):
        "NUH",

    # --------------------------------------------------------
    # DELHI
    # --------------------------------------------------------

    ("NCT OF DELHI", "NORTH WEST"):
        "NORTH-WEST DELHI",

    ("NCT OF DELHI", "NORTH"):
        "NORTH DELHI",

    ("NCT OF DELHI", "NORTH EAST"):
        "NORTH-EAST DELHI",

    ("NCT OF DELHI", "EAST"):
        "EAST DELHI",

    ("NCT OF DELHI", "CENTRAL"):
        "CENTRAL DELHI",

    ("NCT OF DELHI", "WEST"):
        "WEST DELHI",

    ("NCT OF DELHI", "SOUTH WEST"):
        "SOUTH-WEST DELHI",

    ("NCT OF DELHI", "SOUTH"):
        "SOUTH DELHI",

    # --------------------------------------------------------
    # RAJASTHAN
    # --------------------------------------------------------

    ("RAJASTHAN", "JHUNJHUNUN"):
        "JHUNJHUNU",

    ("RAJASTHAN", "DHAULPUR"):
        "DHOLPUR",

    # --------------------------------------------------------
    # UTTAR PRADESH
    # --------------------------------------------------------

    ("UTTAR PRADESH", "JYOTIBA PHULE NAGAR"):
        "AMROHA",

    ("UTTAR PRADESH", "MAHAMAYA NAGAR"):
        "HATHRAS",

    ("UTTAR PRADESH", "ALLAHABAD"):
        "PRAYAGRAJ",

    ("UTTAR PRADESH", "FAIZABAD"):
        "AYODHYA",

    ("UTTAR PRADESH", "MAHRAJGANJ"):
        "MAHARAJGANJ",

    ("UTTAR PRADESH", "KANSHIRAM NAGAR"):
        "KASGANJ",

    ("UTTAR PRADESH", "SHRAWASTI"):
        "SHRAVASTI",

    ("UTTAR PRADESH", "KUSHINAGAR"):
        "KUSHI NAGAR",

    ("UTTAR PRADESH", "RAE BARELI"):
        "RAI BARELI",

    ("UTTAR PRADESH", "KANNAUJ"):
        "KANAUJ",

    ("UTTAR PRADESH", "SIDDHARTHNAGAR"):
        "SIDHARTHANAGAR",

    ("UTTAR PRADESH", "SANT RAVIDAS NAGAR (BHADOHI)"):
        "SANT RAVIDAS NAGAR",

    # --------------------------------------------------------
    # BIHAR
    # --------------------------------------------------------

    ("BIHAR", "PASHCHIM CHAMPARAN"):
        "PASCHIMI CHAMPARAN",

    ("BIHAR", "PURBA CHAMPARAN"):
        "PURBI CHAMPARAN",

    ("BIHAR", "KAIMUR (BHABUA)"):
        "KAIMUR",

    # --------------------------------------------------------
    # SIKKIM
    # --------------------------------------------------------

    ("SIKKIM", "NORTH DISTRICT"):
        "MANGAN",

    ("SIKKIM", "WEST DISTRICT"):
        "GYALSHING",

    ("SIKKIM", "SOUTH DISTRICT"):
        "NAMCHI",

    ("SIKKIM", "EAST DISTRICT"):
        "GANGTOK",

    # --------------------------------------------------------
    # ARUNACHAL PRADESH
    # --------------------------------------------------------

    ("ARUNACHAL PRADESH", "PAPUM PARE"):
        "PAPUMPARE",

    ("ARUNACHAL PRADESH", "CHANGLANG"):
        "CHUNGLANG",

    # --------------------------------------------------------
    # MANIPUR
    # --------------------------------------------------------

    ("MANIPUR", "BISHNUPUR"):
        "BISHENPUR",

    # --------------------------------------------------------
    # MIZORAM
    # --------------------------------------------------------

    ("MIZORAM", "SAIHA"):
        "SIAHA",


    # --------------------------------------------------------
    # MEGHALAYA
    # --------------------------------------------------------

    ("MEGHALAYA", "RIBHOI"):
        "RI BHOI",

    ("MEGHALAYA", "JAINTIA HILLS"):
        "WEST JAINTIA HILLS",

    # --------------------------------------------------------
    # WEST BENGAL
    # --------------------------------------------------------

    ("WEST BENGAL", "BARDDHAMAN"):
        "PURBA BARDHAMAN",

    ("WEST BENGAL", "NORTH TWENTY FOUR PARGANAS"):
        "NORTH 24 PARGANAS",

    ("WEST BENGAL", "SOUTH TWENTY FOUR PARGANAS"):
        "SOUTH 24 PARGANAS",

    # --------------------------------------------------------
    # JHARKHAND
    # --------------------------------------------------------

    ("JHARKHAND", "KODARMA"):
        "KODERMA",

    ("JHARKHAND", "SAHIBGANJ"):
        "SAHEBGANJ",

    ("JHARKHAND", "HAZARIBAGH"):
        "HAZARIBAG",

    ("JHARKHAND", "LOHARDAGA"):
        "LOHARDAGGA",

    ("JHARKHAND", "PALAMU"):
        "PALAMAU",

    ("JHARKHAND", "PASHCHIMI SINGHBHUM"):
        "PASCHIMI SINGHBHUM",

    ("JHARKHAND", "SARAIKELA-KHARSAWAN"):
        "SERAIKELA-KHARSAWAN",

    # --------------------------------------------------------
    # ODISHA
    # --------------------------------------------------------

    ("ODISHA", "DEBAGARH"):
        "DEOGARH",

    ("ODISHA", "KENDUJHAR"):
        "KEONJHAR",

    ("ODISHA", "JAGATSINGHAPUR"):
        "JAGATSINGHPUR",

    ("ODISHA", "JAJAPUR"):
        "JAJPUR",

    ("ODISHA", "BAUDH"):
        "BOUDH",

    ("ODISHA", "SUBARNAPUR"):
        "SONEPUR",

    ("ODISHA", "KHORDHA"):
        "KHURDA",

    ("ODISHA", "NUAPADA"):
        "NAWAPARA",

    ("ODISHA", "NABARANGAPUR"):
        "NAWRANGPUR",

    # --------------------------------------------------------
    # CHHATTISGARH
    # --------------------------------------------------------

    ("CHHATTISGARH", "JANJGIR - CHAMPA"):
        "JANJGIR-CHAMPA",

    # --------------------------------------------------------
    # MADHYA PRADESH
    # --------------------------------------------------------

    ("MADHYA PRADESH", "HOSHANGABAD"):
        "NARMADAPURAM",

    ("MADHYA PRADESH", "KHARGONE (WEST NIMAR)"):
        "WEST NIMAR",

    ("MADHYA PRADESH", "KHANDWA (EAST NIMAR)"):
        "EAST NIMAR",

    # --------------------------------------------------------
    # GUJARAT
    # --------------------------------------------------------

    ("GUJARAT", "AHMADABAD"):
        "AHMEDABAD",

    ("GUJARAT", "THE DANGS"):
        "DANGS",

    # --------------------------------------------------------
    # DADRA & NAGAR HAVELI
    # --------------------------------------------------------

    ("DADRA & NAGAR HAVELI", "DADRA & NAGAR HAVELI"):
        "DADRA&NAGAR HAVELI",

    # --------------------------------------------------------
    # MAHARASHTRA
    # --------------------------------------------------------

    ("MAHARASHTRA", "BULDANA"):
        "BULDHANA",

    ("MAHARASHTRA", "GONDIYA"):
        "GONDIA",

    ("MAHARASHTRA", "RAIGARH"):
        "RAIGAD",

    ("MAHARASHTRA", "OSMANABAD"):
        "DHARASHIV",

    ("MAHARASHTRA", "AURANGABAD"):
        "CHHATRAPATI SAMBHAJINAGAR",

    ("MAHARASHTRA", "NASHIK"):
        "NASIK",

    ("MAHARASHTRA", "AHMADNAGAR"):
        "AHILYANAGAR",

    # --------------------------------------------------------
    # ANDHRA PRADESH
    # --------------------------------------------------------

    ("ANDHRA PRADESH", "ANANTAPUR"):
        "ANANTHAPURAMU",

    ("ANDHRA PRADESH", "RANGAREDDY"):
        "RANGAREDDI",

    # --------------------------------------------------------
    # KARNATAKA
    # --------------------------------------------------------

    ("KARNATAKA", "BELGAUM"):
        "BELAGAVI",

    ("KARNATAKA", "BIJAPUR"):
        "VIJAYAPURA",

    ("KARNATAKA", "BELLARY"):
        "BALLARI",

    ("KARNATAKA", "SHIMOGA"):
        "SHIVAMOGGA",

    ("KARNATAKA", "CHIKMAGALUR"):
        "CHIKKAMAGALURU",

    ("KARNATAKA", "TUMKUR"):
        "TUMAKURU",

    ("KARNATAKA", "MYSORE"):
        "MYSURU",

    ("KARNATAKA", "GULBARGA"):
        "KALABURAGI",

    ("KARNATAKA", "BAGALKOT"):
        "BAGALKOTE",

    ("KARNATAKA", "BANGALORE RURAL"):
        "BENGALURU RURAL",

    ("KARNATAKA", "UTTARA KANNADA"):
        "UTTAR KANNAD",

    ("KARNATAKA", "DAVANAGERE"):
        "DAVANGERE",

    ("KARNATAKA", "UDUPI"):
        "UDIPI",

    ("KARNATAKA", "BANGALORE"):
        "BENGALURU URBAN",

    ("KARNATAKA", "DAKSHINA KANNADA"):
        "DAKSHIN KANNAD",

    ("KARNATAKA", "RAMANAGARA"):
        "BENGALURU SOUTH",

    # --------------------------------------------------------
    # KERALA
    # --------------------------------------------------------

    ("KERALA", "ALAPPUZHA"):
        "ALAPUZHA",

    # --------------------------------------------------------
    # TAMIL NADU
    # --------------------------------------------------------

    ("TAMIL NADU", "THE NILGIRIS"):
        "NILGIRIS",

    ("TAMIL NADU", "KANNIYAKUMARI"):
        "KANYAKUMARI",

    ("TAMIL NADU", "VILUPPURAM"):
        "VILLUPURAM",

    ("TAMIL NADU", "TIRUCHIRAPPALLI"):
        "TIRUCHIRAPALLI",

    ("TAMIL NADU", "THOOTHUKKUDI"):
        "TOOTHUKUDI",

    ("TAMIL NADU", "TIRUNELVELI"):
        "TIRUNELVALI",

    # --------------------------------------------------------
    # ANDAMAN & NICOBAR
    # --------------------------------------------------------

    ("ANDAMAN & NICOBAR ISLANDS", "NICOBARS"):
        "NICOBAR",

    ("ANDAMAN & NICOBAR ISLANDS", "NORTH & MIDDLE ANDAMAN"):
        "NORTH AND MIDDLE ANDAMAN",

    # --------------------------------------------------------
    # PUDUCHERRY
    # --------------------------------------------------------

    ("PUDUCHERRY", "PUDUCHERRY"):
        "PUDUCHERRY",

    ("PUDUCHERRY", "KARAIKAL"):
        "KARAIKAL",

    ("PUDUCHERRY", "MAHE"):
        "MAHE",

    ("PUDUCHERRY", "YANAM"):
        "YANAM",
}

# ============================================================
# FINAL DISTRICT NAME ALIASES
# ============================================================
# These are Census 2011 district names that have a different
# spelling/name in the current RBI dataset.
#
# IMPORTANT:
# These are explicit mappings only.
# Do NOT use fuzzy matching to automatically assign districts.

additional_district_mapping = {

    # ---------------- J&K / LADAKH ----------------
    ("JAMMU & KASHMIR", "LEH(LADAKH)"): "LEH",
    ("JAMMU & KASHMIR", "KARGIL"): "KARGIL",
    ("JAMMU & KASHMIR", "PUNCH"): "POONCH",
    ("JAMMU & KASHMIR", "BARAMULA"): "BARAMULLA",
    ("JAMMU & KASHMIR", "BANDIPORE"): "BANDIPORA",
    ("JAMMU & KASHMIR", "SHUPIYAN"): "SHOPIAN",

    # ---------------- HIMACHAL PRADESH ----------------
    ("HIMACHAL PRADESH", "KULLU"): "KULU",

    # ---------------- PUNJAB ----------------
    ("PUNJAB", "FIROZPUR"): "FEROZPUR",

    # ---------------- UTTARAKHAND ----------------
    ("UTTARAKHAND", "UTTARKASHI"): "UTTAR KASHI",
    ("UTTARAKHAND", "DEHRADUN"): "DEHRA DUN",
    ("UTTARAKHAND", "HARDWAR"): "HARIDWAR",

    # ---------------- HARYANA ----------------
    ("HARYANA", "GURGAON"): "GURUGRAM",
    ("HARYANA", "MEWAT"): "NUH",

    # ---------------- DELHI ----------------
    ("NCT OF DELHI", "NORTH WEST"): "NORTH-WEST DELHI",
    ("NCT OF DELHI", "NORTH"): "NORTH DELHI",
    ("NCT OF DELHI", "NORTH EAST"): "NORTH-EAST DELHI",
    ("NCT OF DELHI", "EAST"): "EAST DELHI",
    ("NCT OF DELHI", "CENTRAL"): "CENTRAL DELHI",
    ("NCT OF DELHI", "WEST"): "WEST DELHI",
    ("NCT OF DELHI", "SOUTH WEST"): "SOUTH-WEST DELHI",
    ("NCT OF DELHI", "SOUTH"): "SOUTH DELHI",

    # ---------------- RAJASTHAN ----------------
    ("RAJASTHAN", "JHUNJHUNUN"): "JHUNJHUNU",
    ("RAJASTHAN", "DHAULPUR"): "DHOLPUR",

    # ---------------- UTTAR PRADESH ----------------
    ("UTTAR PRADESH", "JYOTIBA PHULE NAGAR"): "AMROHA",
    ("UTTAR PRADESH", "MAHAMAYA NAGAR"): "HATHRAS",
    ("UTTAR PRADESH", "RAE BARELI"): "RAI BARELI",
    ("UTTAR PRADESH", "KANNAUJ"): "KANAUJ",
    ("UTTAR PRADESH", "ALLAHABAD"): "PRAYAGRAJ",
    ("UTTAR PRADESH", "FAIZABAD"): "AYODHYA",
    ("UTTAR PRADESH", "SHRAWASTI"): "SHRAVASTI",
    ("UTTAR PRADESH", "SIDDHARTHNAGAR"): "SIDHARTHANAGAR",
    ("UTTAR PRADESH", "MAHRAJGANJ"): "MAHARAJGANJ",
    ("UTTAR PRADESH", "KUSHINAGAR"): "KUSHI NAGAR",
    ("UTTAR PRADESH", "SANT RAVIDAS NAGAR (BHADOHI)"): "SANT RAVIDAS NAGAR",
    ("UTTAR PRADESH", "KANSHIRAM NAGAR"): "KASGANJ",

    # ---------------- BIHAR ----------------
    ("BIHAR", "PASHCHIM CHAMPARAN"): "PASCHIMI CHAMPARAN",
    ("BIHAR", "PURBA CHAMPARAN"): "PURBI CHAMPARAN",
    ("BIHAR", "KAIMUR (BHABUA)"): "KAIMUR",

    # ---------------- SIKKIM ----------------
    ("SIKKIM", "NORTH DISTRICT"): "MANGAN",
    ("SIKKIM", "WEST DISTRICT"): "GYALSHING",
    ("SIKKIM", "SOUTH DISTRICT"): "NAMCHI",
    ("SIKKIM", "EAST DISTRICT"): "GANGTOK",

    # ---------------- ARUNACHAL PRADESH ----------------
    ("ARUNACHAL PRADESH", "PAPUM PARE"): "PAPUMPARE",
    ("ARUNACHAL PRADESH", "CHANGLANG"): "CHUNGLANG",

    # ---------------- MANIPUR ----------------
    ("MANIPUR", "BISHNUPUR"): "BISHENPUR",

    # ---------------- MIZORAM ----------------
    ("MIZORAM", "SAIHA"): "SIAHA",

    # ---------------- MEGHALAYA ----------------
    ("MEGHALAYA", "RIBHOI"): "RI BHOI",

    # ---------------- ASSAM ----------------
    ("ASSAM", "KAMRUP METROPOLITAN"): "KAMRUP METROPOLITAN",

    # ---------------- WEST BENGAL ----------------
    ("WEST BENGAL", "BARDDHAMAN"): "PURBA BARDHAMAN",
    ("WEST BENGAL", "NORTH TWENTY FOUR PARGANAS"): "NORTH 24 PARGANAS",
    ("WEST BENGAL", "SOUTH TWENTY FOUR PARGANAS"): "SOUTH 24 PARGANAS",

    # ---------------- JHARKHAND ----------------
    ("JHARKHAND", "KODARMA"): "KODERMA",
    ("JHARKHAND", "SAHIBGANJ"): "SAHEBGANJ",
    ("JHARKHAND", "LOHARDAGA"): "LOHARDAGGA",
    ("JHARKHAND", "PALAMU"): "PALAMAU",
    ("JHARKHAND", "HAZARIBAGH"): "HAZARIBAG",
    ("JHARKHAND", "PASHCHIMI SINGHBHUM"): "PASCHIMI SINGHBHUM",
    ("JHARKHAND", "SARAIKELA-KHARSAWAN"): "SERAIKELA-KHARSAWAN",

    # ---------------- ODISHA ----------------
    ("ODISHA", "DEBAGARH"): "DEOGARH",
    ("ODISHA", "KENDUJHAR"): "KEONJHAR",
    ("ODISHA", "JAGATSINGHAPUR"): "JAGATSINGHPUR",
    ("ODISHA", "JAJAPUR"): "JAJPUR",
    ("ODISHA", "KHORDHA"): "KHURDA",
    ("ODISHA", "BAUDH"): "BOUDH",
    ("ODISHA", "SUBARNAPUR"): "SONEPUR",
    ("ODISHA", "NUAPADA"): "NAWAPARA",
    ("ODISHA", "NABARANGAPUR"): "NAWRANGPUR",

    # ---------------- CHHATTISGARH ----------------
    ("CHHATTISGARH", "JANJGIR - CHAMPA"): "JANJGIR-CHAMPA",

    # ---------------- MADHYA PRADESH ----------------
    ("MADHYA PRADESH", "KHARGONE (WEST NIMAR)"): "WEST NIMAR",
    ("MADHYA PRADESH", "HOSHANGABAD"): "NARMADAPURAM",
    ("MADHYA PRADESH", "KHANDWA (EAST NIMAR)"): "EAST NIMAR",

    # ---------------- GUJARAT ----------------
    ("GUJARAT", "AHMADABAD"): "AHMEDABAD",
    ("GUJARAT", "THE DANGS"): "DANGS",

    # ---------------- DAMAN & DIU ----------------
    ("DAMAN & DIU", "DIU"): "DIU",
    ("DAMAN & DIU", "DAMAN"): "DAMAN",

    # ---------------- DADRA & NAGAR HAVELI ----------------
    ("DADRA & NAGAR HAVELI", "DADRA & NAGAR HAVELI"): "DADRA&NAGAR HAVELI",

    # ---------------- MAHARASHTRA ----------------
    ("MAHARASHTRA", "BULDANA"): "BULDHANA",
    ("MAHARASHTRA", "GONDIYA"): "GONDIA",
    ("MAHARASHTRA", "AURANGABAD"): "CHHATRAPATI SAMBHAJINAGAR",
    ("MAHARASHTRA", "NASHIK"): "NASIK",
    ("MAHARASHTRA", "RAIGARH"): "RAIGAD",
    ("MAHARASHTRA", "AHMADNAGAR"): "AHILYANAGAR",
    ("MAHARASHTRA", "OSMANABAD"): "DHARASHIV",

    # ---------------- KARNATAKA ----------------
    ("KARNATAKA", "BELGAUM"): "BELAGAVI",
    ("KARNATAKA", "BAGALKOT"): "BAGALKOTE",
    ("KARNATAKA", "BIJAPUR"): "VIJAYAPURA",
    ("KARNATAKA", "UTTARA KANNADA"): "UTTAR KANNAD",
    ("KARNATAKA", "BELLARY"): "BALLARI",
    ("KARNATAKA", "DAVANAGERE"): "DAVANGERE",
    ("KARNATAKA", "SHIMOGA"): "SHIVAMOGGA",
    ("KARNATAKA", "UDUPI"): "UDIPI",
    ("KARNATAKA", "CHIKMAGALUR"): "CHIKKAMAGALURU",
    ("KARNATAKA", "TUMKUR"): "TUMAKURU",
    ("KARNATAKA", "BANGALORE"): "BENGALURU URBAN",
    ("KARNATAKA", "DAKSHINA KANNADA"): "DAKSHIN KANNAD",
    ("KARNATAKA", "MYSORE"): "MYSURU",
    ("KARNATAKA", "GULBARGA"): "KALABURAGI",
    ("KARNATAKA", "BANGALORE RURAL"): "BENGALURU RURAL",
    ("KARNATAKA", "RAMANAGARA"): "BENGALURU SOUTH",

    # ---------------- KERALA ----------------
    ("KERALA", "ALAPPUZHA"): "ALAPUZHA",

    # ---------------- TAMIL NADU ----------------
    ("TAMIL NADU", "VILUPPURAM"): "VILLUPURAM",
    ("TAMIL NADU", "THE NILGIRIS"): "NILGIRIS",
    ("TAMIL NADU", "TIRUCHIRAPPALLI"): "TIRUCHIRAPALLI",
    ("TAMIL NADU", "THOOTHUKKUDI"): "TOOTHUKUDI",
    ("TAMIL NADU", "TIRUNELVELI"): "TIRUNELVALI",
    ("TAMIL NADU", "KANNIYAKUMARI"): "KANYAKUMARI",

    # ---------------- ANDAMAN & NICOBAR ----------------
    ("ANDAMAN & NICOBAR ISLANDS", "NICOBARS"): "NICOBAR",
    ("ANDAMAN & NICOBAR ISLANDS", "NORTH & MIDDLE ANDAMAN"):
        "NORTH AND MIDDLE ANDAMAN",
}


# Add the new aliases to the existing mapping.
district_name_mapping.update(additional_district_mapping)

districts["District_Match"] = districts.apply(
    lambda row: district_name_mapping.get(
        (
            row["State"],
            row["District"]
        ),
        row["District"]
    ),
    axis=1
)


# ============================================================
# 8. IMPORTANT:
#    MAP CURRENT RBI DISTRICTS BACK TO 2011 CENSUS DISTRICTS
# ============================================================

print("\n" + "=" * 70)
print("7. POST-2011 DISTRICT SPLIT CORRECTION")
print("=" * 70)



rbi_to_census_2011 = {

    # ========================================================
    # TELANGANA
    # ========================================================
    ("TELANGANA", "HYDERABAD"):
    ("ANDHRA PRADESH", "HYDERABAD"),
    # 2011 ADILABAD
    ("TELANGANA", "ADILABAD"):
        ("ANDHRA PRADESH", "ADILABAD"),

    ("TELANGANA", "KOMARAM BHEEM ASIFABAD"):
        ("ANDHRA PRADESH", "ADILABAD"),

    ("TELANGANA", "MANCHERIAL"):
        ("ANDHRA PRADESH", "ADILABAD"),

    ("TELANGANA", "NIRMAL"):
        ("ANDHRA PRADESH", "ADILABAD"),

    # 2011 NIZAMABAD
    ("TELANGANA", "NIZAMABAD"):
        ("ANDHRA PRADESH", "NIZAMABAD"),

    ("TELANGANA", "KAMAREDDY"):
        ("ANDHRA PRADESH", "NIZAMABAD"),

    # 2011 KARIMNAGAR
    ("TELANGANA", "KARIMNAGAR"):
        ("ANDHRA PRADESH", "KARIMNAGAR"),

    ("TELANGANA", "JAGTIAL"):
        ("ANDHRA PRADESH", "KARIMNAGAR"),

    ("TELANGANA", "PEDDAPALLI"):
        ("ANDHRA PRADESH", "KARIMNAGAR"),

    ("TELANGANA", "RAJANNA SIRCILLA"):
        ("ANDHRA PRADESH", "KARIMNAGAR"),

    # 2011 MEDAK
    ("TELANGANA", "MEDAK"):
        ("ANDHRA PRADESH", "MEDAK"),

    ("TELANGANA", "SANGAREDDY"):
        ("ANDHRA PRADESH", "MEDAK"),

    ("TELANGANA", "SIDDIPET"):
        ("ANDHRA PRADESH", "MEDAK"),

    # 2011 RANGAREDDY
    ("TELANGANA", "RANGAREDDY"):
        ("ANDHRA PRADESH", "RANGAREDDY"),

    ("TELANGANA", "RANGAREDDI"):
        ("ANDHRA PRADESH", "RANGAREDDY"),

    ("TELANGANA", "VIKARABAD"):
        ("ANDHRA PRADESH", "RANGAREDDY"),

    ("TELANGANA", "MEDCHAL-MALKAJGIRI"):
        ("ANDHRA PRADESH", "RANGAREDDY"),

    ("TELANGANA", "MEDCHAL MALKAJGIRI"):
        ("ANDHRA PRADESH", "RANGAREDDY"),

    # 2011 MAHBUBNAGAR
    ("TELANGANA", "MAHBUBNAGAR"):
        ("ANDHRA PRADESH", "MAHBUBNAGAR"),

    ("TELANGANA", "MAHABUBNAGAR"):
        ("ANDHRA PRADESH", "MAHBUBNAGAR"),

    ("TELANGANA", "JOGULAMBA GADWAL"):
        ("ANDHRA PRADESH", "MAHBUBNAGAR"),

    ("TELANGANA", "WANAPARTHY"):
        ("ANDHRA PRADESH", "MAHBUBNAGAR"),

    ("TELANGANA", "NAGARKURNOOL"):
        ("ANDHRA PRADESH", "MAHBUBNAGAR"),

    # 2011 NALGONDA
    ("TELANGANA", "NALGONDA"):
        ("ANDHRA PRADESH", "NALGONDA"),

    ("TELANGANA", "SURYAPET"):
        ("ANDHRA PRADESH", "NALGONDA"),

    ("TELANGANA", "YADADRI BHUVANAGIRI"):
        ("ANDHRA PRADESH", "NALGONDA"),

    # 2011 WARANGAL
    ("TELANGANA", "WARANGAL"):
        ("ANDHRA PRADESH", "WARANGAL"),

    ("TELANGANA", "HANAMKONDA"):
        ("ANDHRA PRADESH", "WARANGAL"),

    ("TELANGANA", "JANGAON"):
        ("ANDHRA PRADESH", "WARANGAL"),

    ("TELANGANA", "JAYASHANKAR BHUPALAPALLY"):
        ("ANDHRA PRADESH", "WARANGAL"),

    ("TELANGANA", "MAHABUBABAD"):
        ("ANDHRA PRADESH", "WARANGAL"),

    # 2011 KHAMMAM
    ("TELANGANA", "KHAMMAM"):
        ("ANDHRA PRADESH", "KHAMMAM"),

    ("TELANGANA", "BHADRADRI KOTHAGUDEM"):
        ("ANDHRA PRADESH", "KHAMMAM"),

        # --------------------------------------------------------
    # ACTUAL RBI NAME VARIATIONS
    # --------------------------------------------------------

    ("TELANGANA", "KOMRAM BHEEM (ASIFABAD)"):
        ("ANDHRA PRADESH", "ADILABAD"),

    ("TELANGANA", "HANUMAKONDA"):
        ("ANDHRA PRADESH", "WARANGAL"),

    ("TELANGANA", "JAGITIAL"):
        ("ANDHRA PRADESH", "KARIMNAGAR"),

    ("TELANGANA", "RAJANNA(SIRCILLA)"):
        ("ANDHRA PRADESH", "KARIMNAGAR"),

    ("TELANGANA", "JOGULAMBA (GADWAL)"):
        ("ANDHRA PRADESH", "MAHBUBNAGAR"),

    ("TELANGANA", "BHADRADRI (KOTHAGUDEM)"):
        ("ANDHRA PRADESH", "KHAMMAM"),
    # ========================================================
    # ANDHRA PRADESH
    # ========================================================

    # 2011 SRIKAKULAM
    ("ANDHRA PRADESH", "SRIKAKULAM"):
        ("ANDHRA PRADESH", "SRIKAKULAM"),

    # 2011 VIZIANAGARAM
    ("ANDHRA PRADESH", "VIZIANAGARAM"):
        ("ANDHRA PRADESH", "VIZIANAGARAM"),

    ("ANDHRA PRADESH", "PARVATHIPURAM MANYAM"):
        ("ANDHRA PRADESH", "VIZIANAGARAM"),

    # 2011 VISAKHAPATNAM
    ("ANDHRA PRADESH", "VISAKHAPATNAM"):
        ("ANDHRA PRADESH", "VISAKHAPATNAM"),

    ("ANDHRA PRADESH", "ANAKAPALLI"):
        ("ANDHRA PRADESH", "VISAKHAPATNAM"),

    ("ANDHRA PRADESH", "ALLURI SITHARAMA RAJU"):
        ("ANDHRA PRADESH", "VISAKHAPATNAM"),

    # 2011 EAST GODAVARI
    ("ANDHRA PRADESH", "EAST GODAVARI"):
        ("ANDHRA PRADESH", "EAST GODAVARI"),

    ("ANDHRA PRADESH", "KAKINADA"):
        ("ANDHRA PRADESH", "EAST GODAVARI"),

    ("ANDHRA PRADESH", "KONA SEEMA"):
        ("ANDHRA PRADESH", "EAST GODAVARI"),

    # 2011 WEST GODAVARI
    ("ANDHRA PRADESH", "WEST GODAVARI"):
        ("ANDHRA PRADESH", "WEST GODAVARI"),

    ("ANDHRA PRADESH", "ELURU"):
        ("ANDHRA PRADESH", "WEST GODAVARI"),

    # 2011 KRISHNA
    ("ANDHRA PRADESH", "KRISHNA"):
        ("ANDHRA PRADESH", "KRISHNA"),

    ("ANDHRA PRADESH", "NTR"):
        ("ANDHRA PRADESH", "KRISHNA"),

    # 2011 GUNTUR
    ("ANDHRA PRADESH", "GUNTUR"):
        ("ANDHRA PRADESH", "GUNTUR"),

    ("ANDHRA PRADESH", "BAPATLA"):
        ("ANDHRA PRADESH", "GUNTUR"),

    ("ANDHRA PRADESH", "PALNADU"):
        ("ANDHRA PRADESH", "GUNTUR"),

    # 2011 PRAKASAM
    ("ANDHRA PRADESH", "PRAKASAM"):
        ("ANDHRA PRADESH", "PRAKASAM"),

    # 2011 SRI POTTI SRIRAMULU NELLORE
    ("ANDHRA PRADESH", "SRI POTTI SRIRAMULU NELLORE"):
        ("ANDHRA PRADESH", "SRI POTTI SRIRAMULU NELLORE"),

    ("ANDHRA PRADESH", "NELLORE"):
        ("ANDHRA PRADESH", "SRI POTTI SRIRAMULU NELLORE"),

    ("ANDHRA PRADESH", "TIRUPATI"):
        ("ANDHRA PRADESH", "SRI POTTI SRIRAMULU NELLORE"),

    # 2011 CHITTOOR
    ("ANDHRA PRADESH", "CHITTOOR"):
        ("ANDHRA PRADESH", "CHITTOOR"),

    ("ANDHRA PRADESH", "ANNAMAYYA"):
        ("ANDHRA PRADESH", "CHITTOOR"),

    # 2011 KADAPA
    ("ANDHRA PRADESH", "Y.S.R. KADAPA"):
        ("ANDHRA PRADESH", "Y.S.R. KADAPA"),

    ("ANDHRA PRADESH", "YSR KADAPA"):
        ("ANDHRA PRADESH", "Y.S.R. KADAPA"),

    ("ANDHRA PRADESH", "KADAPA"):
        ("ANDHRA PRADESH", "Y.S.R. KADAPA"),

    # 2011 KURNOOL
    ("ANDHRA PRADESH", "KURNOOL"):
        ("ANDHRA PRADESH", "KURNOOL"),

    ("ANDHRA PRADESH", "NANDYAL"):
        ("ANDHRA PRADESH", "KURNOOL"),

    # 2011 ANANTAPUR
    ("ANDHRA PRADESH", "ANANTHAPURAMU"):
        ("ANDHRA PRADESH", "ANANTAPUR"),

    ("ANDHRA PRADESH", "SRI SATHYA SAI"):
        ("ANDHRA PRADESH", "ANANTAPUR"),


    # ========================================================
    # ASSAM
    # ========================================================

    # 2011 KAMRUP
    ("ASSAM", "KAMRUP"):
        ("ASSAM", "KAMRUP"),

    ("ASSAM", "KAMRUP METROPOLITAN"):
    ("ASSAM", "KAMRUP METROPOLITAN"),

    # 2011 DARRANG
    ("ASSAM", "DARRANG"):
        ("ASSAM", "DARRANG"),

    ("ASSAM", "TAMULPUR"):
        ("ASSAM", "DARRANG"),

    # 2011 SONITPUR
    ("ASSAM", "SONITPUR"):
        ("ASSAM", "SONITPUR"),

    ("ASSAM", "BISWANATH"):
        ("ASSAM", "SONITPUR"),

    # 2011 LAKHIMPUR
    ("ASSAM", "LAKHIMPUR"):
        ("ASSAM", "LAKHIMPUR"),

    # 2011 NAGAON
    ("ASSAM", "NAGAON"):
        ("ASSAM", "NAGAON"),

    ("ASSAM", "HOJAI"):
        ("ASSAM", "NAGAON"),

    # 2011 GOLAGHAT
    ("ASSAM", "GOLAGHAT"):
        ("ASSAM", "GOLAGHAT"),

    # 2011 JORHAT
    ("ASSAM", "JORHAT"):
        ("ASSAM", "JORHAT"),

    # 2011 SIVASAGAR
    ("ASSAM", "SIVASAGAR"):
        ("ASSAM", "SIVASAGAR"),

    ("ASSAM", "SIBSAGAR"):
        ("ASSAM", "SIVASAGAR"),

    # 2011 DIBRUGARH
    ("ASSAM", "DIBRUGARH"):
        ("ASSAM", "DIBRUGARH"),

    # 2011 TINSUKIA
    ("ASSAM", "TINSUKIA"):
        ("ASSAM", "TINSUKIA"),

    # 2011 CACHAR
    ("ASSAM", "CACHAR"):
        ("ASSAM", "CACHAR"),

    # 2011 KARIMGANJ
    ("ASSAM", "KARIMGANJ"):
        ("ASSAM", "KARIMGANJ"),

    ("ASSAM", "SRIBHUMI"):
        ("ASSAM", "KARIMGANJ"),

    # 2011 HAILAKANDI
    ("ASSAM", "HAILAKANDI"):
        ("ASSAM", "HAILAKANDI"),


    # ========================================================
    # CHHATTISGARH
    # ========================================================

    # 2011 SURGUJA
    ("CHHATTISGARH", "SURGUJA"):
        ("CHHATTISGARH", "SURGUJA"),

    ("CHHATTISGARH", "BALRAMPUR"):
        ("CHHATTISGARH", "SURGUJA"),

    ("CHHATTISGARH", "SURAJPUR"):
        ("CHHATTISGARH", "SURGUJA"),

    # 2011 KORIYA
    ("CHHATTISGARH", "KOREA"):
        ("CHHATTISGARH", "KORIYA"),

    ("CHHATTISGARH", "KORIYA"):
        ("CHHATTISGARH", "KORIYA"),

    ("CHHATTISGARH", "MANENDRAGARH CHIRMIRI BHARATPUR"):
        ("CHHATTISGARH", "KORIYA"),

    # 2011 BILASPUR
    ("CHHATTISGARH", "BILASPUR"):
        ("CHHATTISGARH", "BILASPUR"),

    ("CHHATTISGARH", "GAURELA PENDRA MARWAHI"):
        ("CHHATTISGARH", "BILASPUR"),

    # 2011 JANJGIR-CHAMPA
    ("CHHATTISGARH", "JANJGIR-CHAMPA"):
        ("CHHATTISGARH", "JANJGIR - CHAMPA"),

    ("CHHATTISGARH", "SAKTI"):
        ("CHHATTISGARH", "JANJGIR - CHAMPA"),

    # 2011 RAIGARH
    ("CHHATTISGARH", "RAIGARH"):
        ("CHHATTISGARH", "RAIGARH"),

    ("CHHATTISGARH", "SARANGARH-BILAIGARH"):
        ("CHHATTISGARH", "RAIGARH"),

    # 2011 KORBA
    ("CHHATTISGARH", "KORBA"):
        ("CHHATTISGARH", "KORBA"),

    # 2011 RAIPUR
    ("CHHATTISGARH", "RAIPUR"):
        ("CHHATTISGARH", "RAIPUR"),

    ("CHHATTISGARH", "BALODA BAZAR"):
        ("CHHATTISGARH", "RAIPUR"),

    # 2011 MAHASAMUND
    ("CHHATTISGARH", "MAHASAMUND"):
        ("CHHATTISGARH", "MAHASAMUND"),

    # 2011 DHAMTARI
    ("CHHATTISGARH", "DHAMTARI"):
        ("CHHATTISGARH", "DHAMTARI"),

    # 2011 DURG
    ("CHHATTISGARH", "DURG"):
        ("CHHATTISGARH", "DURG"),

    ("CHHATTISGARH", "BALOD"):
        ("CHHATTISGARH", "DURG"),

    ("CHHATTISGARH", "BEMETARA"):
        ("CHHATTISGARH", "DURG"),

    # 2011 RAJNANDGAON
    ("CHHATTISGARH", "RAJNANDGAON"):
        ("CHHATTISGARH", "RAJNANDGAON"),

    ("CHHATTISGARH", "KHAIRAGARH CHHUIKHADAN GANDAI"):
        ("CHHATTISGARH", "RAJNANDGAON"),

    # 2011 KANKER
    ("CHHATTISGARH", "KANKER"):
        ("CHHATTISGARH", "KANKER"),

    # 2011 BASTAR
    ("CHHATTISGARH", "BASTAR"):
        ("CHHATTISGARH", "BASTAR"),

    ("CHHATTISGARH", "KONDAGAON"):
        ("CHHATTISGARH", "BASTAR"),

    # 2011 DANTEWADA
    ("CHHATTISGARH", "DANTEWADA"):
        ("CHHATTISGARH", "DANTEWADA"),

    ("CHHATTISGARH", "SUKMA"):
        ("CHHATTISGARH", "DANTEWADA"),

    # 2011 BIJAPUR
    ("CHHATTISGARH", "BIJAPUR"):
        ("CHHATTISGARH", "BIJAPUR"),
}



# ============================================================
# 9. APPLY RBI -> 2011 PARENT MAPPING
# ============================================================

# Auto-build a fallback reverse-lookup from the columns you already
# computed correctly (State_Match/District_Match). This handles every
# non-split rename (Belgaum->Belagavi, Leh(Ladakh)->Leh, etc.) in one
# shot, without needing to hand-list them again.
fallback_reverse_lookup = {
    (row["State_Match"], row["District_Match"]): (row["State"], row["District"])
    for _, row in districts.iterrows()
}

split_records = []

for _, row in bank_counts.iterrows():

    key = (row["State"], row["District"])

    if key in rbi_to_census_2011:
        census_parent = rbi_to_census_2011[key]
    elif key in fallback_reverse_lookup:
        census_parent = fallback_reverse_lookup[key]
    else:
        census_parent = (row["State"], row["District"])

    split_records.append(
        {
            "RBI_State": row["State"],
            "RBI_District": row["District"],
            "Banking_Outlets": row["Banking_Outlets"],
            "Census_2011_State": census_parent[0],
            "Census_2011_District": census_parent[1]
        }
    )

rbi_to_2011_df = pd.DataFrame(split_records)
# ============================================================
# 9A. FINAL RBI -> CENSUS NAME STANDARDIZATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL RBI -> CENSUS NAME STANDARDIZATION")
print("=" * 70)


# Create Census state-district pairs
census_pairs = set(
    zip(
        districts["State"],
        districts["District"]
    )
)


# First check direct matches
rbi_to_2011_df["Direct_Census_Match"] = rbi_to_2011_df.apply(
    lambda row: (
        row["Census_2011_State"],
        row["Census_2011_District"]
    ) in census_pairs,
    axis=1
)


print("Directly matched RBI district groups:",
      rbi_to_2011_df["Direct_Census_Match"].sum())

print("District groups needing name mapping:",
      (~rbi_to_2011_df["Direct_Census_Match"]).sum())

# ============================================================
# 9B. FINAL TRUE UNMAPPED RBI OUTLET AUDIT
# ============================================================

print("\n" + "=" * 70)
print("FINAL TRUE UNMAPPED RBI OUTLET AUDIT")
print("=" * 70)


# Create a copy for audit
rbi_audit = rbi_to_2011_df.copy()


# Apply Census district name mapping
def find_census_district_match(row):

    state = row["Census_2011_State"]
    district = row["Census_2011_District"]

    # Direct match
    if (state, district) in census_pairs:
        return district

    # Try reverse lookup from district_name_mapping
    for (census_state, census_district), mapped_name in district_name_mapping.items():

        if census_state == state and mapped_name == district:
            return census_district

    return None


rbi_audit["Final_Census_District"] = rbi_audit.apply(
    find_census_district_match,
    axis=1
)


# Check final match
rbi_audit["Final_Match"] = rbi_audit["Final_Census_District"].notna()


# Summary
total_outlets = rbi_audit["Banking_Outlets"].sum()

matched_outlets = rbi_audit.loc[
    rbi_audit["Final_Match"],
    "Banking_Outlets"
].sum()

unmatched_outlets = rbi_audit.loc[
    ~rbi_audit["Final_Match"],
    "Banking_Outlets"
].sum()


print("\nFINAL AUDIT RESULTS")

print("Total RBI outlets:", total_outlets)
print("Matched RBI outlets:", matched_outlets)
print("Truly unmatched RBI outlets:", unmatched_outlets)

print("\nMatched district groups:",
      rbi_audit["Final_Match"].sum())

print("Truly unmatched district groups:",
      (~rbi_audit["Final_Match"]).sum())

# ============================================================
# 10. AGGREGATE RBI OUTLETS TO 2011 CENSUS DISTRICTS
# ============================================================

rbi_2011_counts = (
    rbi_to_2011_df
    .groupby(
        ["Census_2011_State", "Census_2011_District"],
        as_index=False
    )["Banking_Outlets"]
    .sum()
)

print("\nNumber of 2011 district-level banking records:",
      len(rbi_2011_counts))


# Save mapping
rbi_to_2011_df.to_csv(
    "dataa/processed/district_split_mapping.csv",
    index=False
)

print("\nRBI -> Census 2011 mapping saved:")
print("dataa/processed/district_split_mapping.csv")



# ============================================================
# TRUE UNMATCHED RBI DISTRICTS
# ============================================================

true_unmatched = rbi_audit[
    ~rbi_audit["Final_Match"]
][
    [
        "RBI_State",
        "RBI_District",
        "Census_2011_State",
        "Census_2011_District",
        "Banking_Outlets"
    ]
].sort_values(
    "Banking_Outlets",
    ascending=False
)


print("\n--- TRUE UNMATCHED RBI DISTRICTS ---")

if len(true_unmatched) == 0:

    print("NONE - ALL RBI OUTLETS SUCCESSFULLY MAP TO CENSUS 2011 DISTRICTS!")

else:

    print(true_unmatched.to_string(index=False))


# Save audit
true_unmatched.to_csv(
    "dataa/processed/true_unmatched_rbi_districts.csv",
    index=False
)

print(
    "\nTrue unmatched RBI audit saved:"
)

print(
    "dataa/processed/true_unmatched_rbi_districts.csv"
)
# ============================================================
# RBI OUTLET AUDIT - FIND WHERE OUTLETS ARE LOST
# ============================================================

print("\n" + "=" * 70)
print("RBI OUTLET AUDIT")
print("=" * 70)

print("\n1. Original RBI dataframe rows:")
print(len(bank_df))

print("\n2. Total outlets in bank_counts:")
print(bank_counts["Banking_Outlets"].sum())

print("\n3. Total outlets after RBI -> Census mapping:")
print(rbi_to_2011_df["Banking_Outlets"].sum())

print("\n4. Number of rows in rbi_to_2011_df:")
print(len(rbi_to_2011_df))

print("\nDifference calculations:")

original_rows = len(bank_df)

after_bank_count = bank_counts["Banking_Outlets"].sum()

after_mapping = rbi_to_2011_df["Banking_Outlets"].sum()

print("Original RBI rows:", original_rows)
print("After bank_counts:", after_bank_count)
print("After parent mapping:", after_mapping)

print("Lost before bank_counts:", original_rows - after_bank_count)
print("Lost during parent mapping:", after_bank_count - after_mapping)

# ============================================================
# RBI TO CENSUS MATCH AUDIT
# ============================================================

print("\n" + "=" * 70)
print("RBI TO CENSUS MATCH AUDIT")
print("=" * 70)

# Aggregate RBI mapped data to Census 2011 district level
rbi_2011_counts = (
    rbi_to_2011_df
    .groupby(
        ["Census_2011_State", "Census_2011_District"],
        as_index=False
    )["Banking_Outlets"]
    .sum()
)

print("\nTotal RBI outlets after parent aggregation:")
print(rbi_2011_counts["Banking_Outlets"].sum())

# Create Census district pairs
census_pairs = set(
    zip(
        districts["State"],
        districts["District"]
    )
)

# Find RBI district groups that do not exist in Census
unmapped_rbi = rbi_2011_counts[
    ~rbi_2011_counts.apply(
        lambda row: (
            row["Census_2011_State"],
            row["Census_2011_District"]
        ) in census_pairs,
        axis=1
    )
]

print("\nRBI outlets belonging to districts not found in Census:")
print(unmapped_rbi["Banking_Outlets"].sum())

print("\nNumber of unmatched RBI district groups:")
print(len(unmapped_rbi))

print("\nUnmatched RBI district groups:")
print(
    unmapped_rbi
    .sort_values("Banking_Outlets", ascending=False)
    .to_string(index=False)
)

# Save audit file
unmapped_rbi.to_csv(
    "dataa/processed/unmapped_rbi_districts_audit.csv",
    index=False
)

print(
    "\nAudit file saved: "
    "dataa/processed/unmapped_rbi_districts_audit.csv"
)
# ============================================================
# VALIDATE RBI OUTLET COUNT CONSERVATION
# ============================================================

print("\n" + "=" * 70)
print("RBI OUTLET COUNT CONSERVATION CHECK")
print("=" * 70)

original_rbi_outlets = len(full_bank)

bank_counts_total = bank_counts["Banking_Outlets"].sum()

mapped_parent_total = rbi_to_2011_df["Banking_Outlets"].sum()

print("Original RBI rows:", original_rbi_outlets)

print(
    "Banking outlets after district counting/Puducherry correction:",
    bank_counts_total
)

print(
    "Banking outlets after RBI -> Census 2011 parent mapping:",
    mapped_parent_total
)

print(
    "Difference from original RBI rows:",
    original_rbi_outlets - mapped_parent_total
)

# ============================================================
# 10. AGGREGATE RBI OUTLETS TO 2011 DISTRICT BOUNDARIES
# ============================================================

bank_counts_2011 = (
    rbi_to_2011_df
    .groupby(
        [
            "Census_2011_State",
            "Census_2011_District"
        ]
    )["Banking_Outlets"]
    .sum()
    .reset_index()
)

bank_counts_2011 = bank_counts_2011.rename(
    columns={
        "Census_2011_State": "State",
        "Census_2011_District": "District"
    }
)

print(
    "\nNumber of 2011 district-level banking records:",
    len(bank_counts_2011)
)

rbi_2011_counts = rbi_2011_counts.rename(
    columns={
        "Census_2011_State": "State",
        "Census_2011_District": "District"
    }
)

# ============================================================
# 11. MERGE CENSUS + RBI DATA
# ============================================================

district_analysis = districts.merge(
    rbi_2011_counts,
    left_on=["State", "District"],
    right_on=["State", "District"],
    how="left"
)

district_analysis["Banking_Outlets"] = (
    district_analysis["Banking_Outlets"]
    .fillna(0)
    .astype(int)
)

district_analysis["Population_per_Bank"] = (
    district_analysis["Population"] /
    district_analysis["Banking_Outlets"].replace(0, pd.NA)
)
# ============================================================
# 11. SAVE SPLIT MAPPING FOR TRANSPARENCY
# ============================================================

rbi_to_2011_df.to_csv(
    SPLIT_OUTPUT,
    index=False
)

print("\nRBI -> Census 2011 mapping saved:")
print(SPLIT_OUTPUT)

# ============================================================
# FIX REMAINING DISTRICT NAME MATCHES
# ============================================================

district_name_mapping.update({

    # ASSAM
    ("ASSAM", "SIVASAGAR"): "SIVASAGAR",
    ("ASSAM", "KARIMGANJ"): "KARIMGANJ",

    # ANDHRA PRADESH 2011 DISTRICTS
    ("ANDHRA PRADESH", "ADILABAD"): "ADILABAD",
    ("ANDHRA PRADESH", "NIZAMABAD"): "NIZAMABAD",
    ("ANDHRA PRADESH", "KARIMNAGAR"): "KARIMNAGAR",
    ("ANDHRA PRADESH", "MEDAK"): "MEDAK",
    ("ANDHRA PRADESH", "RANGAREDDY"): "RANGAREDDY",
    ("ANDHRA PRADESH", "MAHBUBNAGAR"): "MAHBUBNAGAR",
    ("ANDHRA PRADESH", "NALGONDA"): "NALGONDA",
    ("ANDHRA PRADESH", "WARANGAL"): "WARANGAL",
    ("ANDHRA PRADESH", "KHAMMAM"): "KHAMMAM",
    ("ANDHRA PRADESH", "ANANTAPUR"): "ANANTAPUR",
})
# ============================================================
# 12. FINAL CENSUS 2011 DISTRICT MATCH
# ============================================================

print("\n" + "=" * 70)
print("12. FINAL CENSUS 2011 DISTRICT MATCH")
print("=" * 70)

# rbi_to_2011_df has already converted current RBI districts
# to their Census 2011 parent districts.
#
# Therefore bank_counts_2011 is already in the
# Census 2011 naming system.
#
# No additional district-name mapping is required here.

print("\nCensus 2011 districts:", len(districts))

print(
    "RBI 2011 district groups:",
    len(bank_counts_2011)
)


# ============================================================
# 13. MERGE CENSUS 2011 + RBI DATA
# ============================================================

print("\n" + "=" * 70)
print("13. MERGING CENSUS 2011 + RBI BANKING DATA")
print("=" * 70)

district_analysis = districts.merge(
    bank_counts_2011,
    on=[
        "State",
        "District"
    ],
    how="left"
)


# Fill districts with no RBI outlets with zero

district_analysis["Banking_Outlets"] = (
    district_analysis["Banking_Outlets"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# 14. POPULATION PER BANKING OUTLET
# ============================================================

district_analysis["Population_per_Bank"] = (
    district_analysis["Population"] /
    district_analysis["Banking_Outlets"].replace(
        0,
        pd.NA
    )
)


print("\nMerge completed successfully.")

print(
    "Total Census 2011 districts:",
    len(district_analysis)
)

print(
    "Total banking outlets in merged data:",
    district_analysis["Banking_Outlets"].sum()
)

# ============================================================
# 15. MERGE VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("9. MERGE VALIDATION")
print("=" * 70)

total = len(district_analysis)

matched = (
    district_analysis["Banking_Outlets"] > 0
).sum()

unmatched_count = (
    district_analysis["Banking_Outlets"] == 0
).sum()

print("Total Census 2011 districts:", total)
print("Districts with banking data:", matched)
print("Districts with NO banking outlets:", unmatched_count)

print(
    "Check total:",
    matched + unmatched_count
)


# ============================================================
# 16. SHOW UNMATCHED DISTRICTS
# ============================================================

unmatched = district_analysis[
    district_analysis["Banking_Outlets"] == 0
].copy()

print("\n--- REMAINING UNMATCHED DISTRICTS ---")

if len(unmatched) > 0:

    print(
        unmatched[
            [
                "State",
                "District",
                "State_Match",
                "District_Match",
                "Population"
            ]
        ].to_string(index=False)
    )

else:

    print("NONE - ALL CENSUS DISTRICTS HAVE RBI DATA!")


print(
    "\nRemaining unmatched:",
    len(unmatched)
)


# ============================================================
# 17. FUZZY MATCH SUGGESTIONS
# ============================================================

print("\n" + "=" * 70)
print("10. FUZZY MATCH SUGGESTIONS")
print("=" * 70)

if len(unmatched) > 0:

    for _, row in unmatched.iterrows():

        state = row["State_Match"]

        candidates = bank_counts_2011.loc[
            bank_counts_2011["State"] == state,
            "District"
        ].unique()

        search_name = row["District_Match"]

        close = difflib.get_close_matches(
            search_name,
            candidates,
            n=5,
            cutoff=0.45
        )

        print(
            f'{row["State"]:25s} | '
            f'{row["District"]:30s} | '
            f'tried={search_name:30s} -> {close}'
        )

else:

    print(
        "No unmatched districts."
    )


# ============================================================
# 18. SAVE UNMATCHED DISTRICTS
# ============================================================

unmatched[
    [
        "State",
        "District",
        "State_Match",
        "District_Match",
        "Population"
    ]
].to_csv(
    UNMATCHED_OUTPUT,
    index=False
)

print(
    "\nUnmatched file saved:",
    UNMATCHED_OUTPUT
)


# ============================================================
# 19. SAVE BASIC DISTRICT ANALYSIS
# ============================================================

district_analysis[
    [
        "State",
        "District",
        "Population",
        "Banking_Outlets",
        "Population_per_Bank"
    ]
].to_csv(
    FINAL_OUTPUT,
    index=False
)

print(
    "\nBasic district analysis saved:",
    FINAL_OUTPUT
)


# ============================================================
# 20. BANKING ACCESS RANK
# ============================================================

analysis_df = district_analysis.copy()

analysis_df["Banking_Access_Rank"] = (
    analysis_df["Population_per_Bank"]
    .rank(
        method="min",
        ascending=False
    )
)


# ============================================================
# 21. BANKING ACCESS CATEGORY
# ============================================================

q25 = analysis_df[
    "Population_per_Bank"
].quantile(0.25)

q50 = analysis_df[
    "Population_per_Bank"
].quantile(0.50)

q75 = analysis_df[
    "Population_per_Bank"
].quantile(0.75)


def classify_access(x):

    if pd.isna(x):
        return "No Banking Data"

    if x <= q25:
        return "Lower Population per Bank"

    elif x <= q50:
        return "Moderate Population per Bank"

    elif x <= q75:
        return "High Population per Bank"

    else:
        return "Very High Population per Bank"


analysis_df[
    "Banking_Access_Category"
] = (
    analysis_df[
        "Population_per_Bank"
    ].apply(classify_access)
)


print("\n--- BANKING ACCESS CATEGORY SUMMARY ---")

print(
    analysis_df[
        "Banking_Access_Category"
    ].value_counts()
)

# ============================================================
# 22. BANKING OUTLET GAP ANALYSIS
# ============================================================

print("\n" + "=" * 70)
print("11. BANKING OUTLET GAP ANALYSIS")
print("=" * 70)

# Calculate benchmark from the FINAL district data
benchmark_population_per_bank = (
    analysis_df["Population"].sum() /
    analysis_df["Banking_Outlets"].sum()
)

print(
    "\nBenchmark Population per Bank:",
    round(benchmark_population_per_bank, 2)
)

# Expected banking outlets
analysis_df["Expected_Banking_Outlets"] = (
    analysis_df["Population"] /
    benchmark_population_per_bank
)

# Banking outlet gap
analysis_df["Banking_Outlet_Gap"] = (
    analysis_df["Expected_Banking_Outlets"] -
    analysis_df["Banking_Outlets"]
)

# Round only for final display
analysis_df["Expected_Banking_Outlets"] = (
    analysis_df["Expected_Banking_Outlets"].round(2)
)

analysis_df["Banking_Outlet_Gap"] = (
    analysis_df["Banking_Outlet_Gap"].round(2)
)


# ============================================================
# 23. BANKING GAP PRIORITY
# ============================================================

positive_gaps = analysis_df.loc[
    analysis_df["Banking_Outlet_Gap"] > 0,
    "Banking_Outlet_Gap"
]

if len(positive_gaps) > 0:

    gap_q25 = positive_gaps.quantile(0.25)
    gap_q50 = positive_gaps.quantile(0.50)
    gap_q75 = positive_gaps.quantile(0.75)

else:

    gap_q25 = 0
    gap_q50 = 0
    gap_q75 = 0


def classify_gap(gap):

    if gap <= 0:
        return "No Gap"

    elif gap <= gap_q25:
        return "Low Priority"

    elif gap <= gap_q50:
        return "Moderate Priority"

    elif gap <= gap_q75:
        return "High Priority"

    else:
        return "Very High Priority"


analysis_df["Banking_Gap_Priority"] = (
    analysis_df["Banking_Outlet_Gap"]
    .apply(classify_gap)
)


# ============================================================
# 24. TOP 20 BANKING GAP DISTRICTS
# ============================================================

print("\n--- TOP 20 DISTRICTS BY BANKING OUTLET GAP ---")

gap_df = analysis_df.sort_values(
    "Banking_Outlet_Gap",
    ascending=False
)

print(
    gap_df[
        [
            "State",
            "District",
            "Population",
            "Banking_Outlets",
            "Expected_Banking_Outlets",
            "Banking_Outlet_Gap",
            "Banking_Gap_Priority"
        ]
    ]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# 25. TOP 20 BY POPULATION PER BANK
# ============================================================

analysis_df = analysis_df.sort_values(
    "Population_per_Bank",
    ascending=False
)

print("\n--- TOP 20 DISTRICTS BY POPULATION PER BANK ---")

print(
    analysis_df[
        [
            "State",
            "District",
            "Population",
            "Banking_Outlets",
            "Population_per_Bank",
            "Banking_Access_Rank",
            "Banking_Access_Category"
        ]
    ]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# 26. STATE-WISE SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("12. STATE-WISE SUMMARY")
print("=" * 70)

state_summary = (
    analysis_df
    .groupby("State")
    .agg(
        Districts=("District", "count"),
        Total_Population=("Population", "sum"),
        Total_Banking_Outlets=(
            "Banking_Outlets",
            "sum"
        ),
        Average_Population_per_Bank=(
            "Population_per_Bank",
            "mean"
        )
    )
    .reset_index()
)


state_summary[
    "Population_per_Bank_State"
] = (
    state_summary[
        "Total_Population"
    ]
    /
    state_summary[
        "Total_Banking_Outlets"
    ].replace(0, pd.NA)
)


state_summary = state_summary.sort_values(
    "Population_per_Bank_State",
    ascending=False
)


print(
    state_summary
    .head(20)
    .to_string(index=False)
)


# Save state summary
state_summary.to_csv(
    STATE_OUTPUT,
    index=False
)

print(
    "\nState summary saved:",
    STATE_OUTPUT
)


# ============================================================
# 27. SAVE FINAL GAP ANALYSIS
# ============================================================

analysis_df.to_csv(
    GAP_OUTPUT,
    index=False
)

print(
    "\nFinal banking gap analysis saved:",
    GAP_OUTPUT
)


# ============================================================
# 28. FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("13. FINAL DATA VALIDATION")
print("=" * 70)

final_df = pd.read_csv(
    GAP_OUTPUT
)

print(
    "\nRows:",
    len(final_df)
)

print(
    "Columns:",
    len(final_df.columns)
)

print("\nColumn names:")
print(
    final_df.columns.tolist()
)


# Duplicate check
duplicates = final_df.duplicated(
    subset=[
        "State",
        "District"
    ]
).sum()

print(
    "\nDuplicate State-District records:",
    duplicates
)


# Missing values
print("\nMissing values:")

print(
    final_df[
        [
            "State",
            "District",
            "Population",
            "Banking_Outlets"
        ]
    ].isnull().sum()
)


# Zero outlets
zero_outlets = (
    final_df[
        "Banking_Outlets"
    ] == 0
).sum()

print(
    "\nDistricts with 0 banking outlets:",
    zero_outlets
)


# Negative values
print(
    "Negative population values:",
    (
        final_df[
            "Population"
        ] < 0
    ).sum()
)

print(
    "Negative banking outlet values:",
    (
        final_df[
            "Banking_Outlets"
        ] < 0
    ).sum()
)


# Missing population per bank
print(
    "\nMissing Population_per_Bank:",
    final_df[
        "Population_per_Bank"
    ].isnull().sum()
)


# ============================================================
# 29. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FINAL PROJECT SUMMARY")
print("=" * 70)

print(
    "\nTotal Census 2011 districts:",
    len(final_df)
)

print(
    "Matched districts:",
    (
        final_df[
            "Banking_Outlets"
        ] > 0
    ).sum()
)

print(
    "Unmatched districts:",
    (
        final_df[
            "Banking_Outlets"
        ] == 0
    ).sum()
)

print(
    "Duplicate districts:",
    duplicates
)

print(
    "\nCensus population year: 2011"
)

print(
    "RBI banking outlet data: current RBI dataset"
)

print(
    "\nFiles created:"
)

print(
    "1.",
    CENSUS_OUTPUT
)

print(
    "2.",
    FINAL_OUTPUT
)

print(
    "3.",
    GAP_OUTPUT
)

print(
    "4.",
    STATE_OUTPUT
)

print(
    "5.",
    UNMATCHED_OUTPUT
)

print(
    "6.",
    SPLIT_OUTPUT
)

print("\n" + "=" * 70)
print("PROJECT DATA PROCESSING COMPLETED")
print("=" * 70)

# ==============================================================
# 14. FINAL ANALYSIS CHECK + CALCULATION VERIFICATION
# ==============================================================

print("\n" + "=" * 70)
print("14. FINAL ANALYSIS CHECK")
print("=" * 70)

# Load final gap analysis
final_df = pd.read_csv(
    "dataa/processed/district_banking_gap_analysis.csv"
)

print("\nFinal file shape:")
print(final_df.shape)

print("\nFinal columns:")
print(final_df.columns.tolist())

# --------------------------------------------------------------
# 1. TOTALS
# --------------------------------------------------------------

total_population = final_df["Population"].sum()
total_outlets = final_df["Banking_Outlets"].sum()

print("\nTotal banking outlets:")
print(total_outlets)

print("\nTotal population:")
print(total_population)

# --------------------------------------------------------------
# 2. INDEPENDENTLY CALCULATE BENCHMARK
# --------------------------------------------------------------

calculated_benchmark = total_population / total_outlets

print("\nCalculated Benchmark Population per Bank:")
print(round(calculated_benchmark, 2))

# --------------------------------------------------------------
# 3. CHECK EXPECTED BANKING OUTLETS
# --------------------------------------------------------------

final_df["Expected_Check"] = (
    final_df["Population"] / calculated_benchmark
)

final_df["Expected_Difference"] = (
    final_df["Expected_Banking_Outlets"]
    - final_df["Expected_Check"]
)

max_expected_difference = (
    final_df["Expected_Difference"]
    .abs()
    .max()
)

print("\nMaximum difference in Expected Banking Outlets:")
print(max_expected_difference)

# --------------------------------------------------------------
# 4. CHECK BANKING GAP
# --------------------------------------------------------------

final_df["Gap_Check"] = (
    final_df["Expected_Check"]
    - final_df["Banking_Outlets"]
)

gap_difference = (
    final_df["Banking_Outlet_Gap"]
    - final_df["Gap_Check"]
)

max_gap_difference = gap_difference.abs().max()

print("\nMaximum difference in Banking Gap:")
print(max_gap_difference)

# --------------------------------------------------------------
# 5. CALCULATION RESULT
# --------------------------------------------------------------

if (
    max_expected_difference < 0.01
    and
    max_gap_difference < 0.01
):
    print("\nCALCULATION CHECK: PASSED")
    print("Benchmark, Expected Banking Outlets and Banking Gap are correct.")
else:
    print("\nCALCULATION CHECK: FAILED")
    print("There is a calculation difference that needs investigation.")

# --------------------------------------------------------------
# 6. PRIORITY COUNTS
# --------------------------------------------------------------

print("\nBanking gap priority counts:")
print(final_df["Banking_Gap_Priority"].value_counts())

# --------------------------------------------------------------
# 7. TOP 10 DISTRICTS BY BANKING GAP
# --------------------------------------------------------------

print("\n--- TOP 10 DISTRICTS BY BANKING GAP ---")

top_gap = final_df.sort_values(
    "Banking_Outlet_Gap",
    ascending=False
)[[
    "State",
    "District",
    "Population",
    "Banking_Outlets",
    "Expected_Banking_Outlets",
    "Banking_Outlet_Gap",
    "Banking_Gap_Priority"
]].head(10)

print(top_gap.to_string(index=False))

# --------------------------------------------------------------
# 8. TOP 10 DISTRICTS BY POPULATION PER BANK
# --------------------------------------------------------------

print("\n--- TOP 10 DISTRICTS BY POPULATION PER BANK ---")

top_population_per_bank = final_df.sort_values(
    "Population_per_Bank",
    ascending=False
)[[
    "State",
    "District",
    "Population",
    "Banking_Outlets",
    "Population_per_Bank",
    "Banking_Access_Category"
]].head(10)

print(top_population_per_bank.to_string(index=False))

# --------------------------------------------------------------
# 9. REMOVE TEMPORARY CHECK COLUMNS
# --------------------------------------------------------------

final_df.drop(
    columns=[
        "Expected_Check",
        "Expected_Difference",
        "Gap_Check"
    ],
    inplace=True
)

print("\nFINAL ANALYSIS CHECK COMPLETED")

# ============================================================
# 15. FINAL RBI OUTLET CONSERVATION CHECK
# ============================================================

print("\n" + "=" * 70)
print("15. FINAL RBI OUTLET CONSERVATION CHECK")
print("=" * 70)

# Total RBI outlets after district counting
rbi_total = bank_counts["Banking_Outlets"].sum()

# Total outlets included in final 640 Census districts
final_total = final_df["Banking_Outlets"].sum()

# Difference
excluded_outlets = rbi_total - final_total

print("\nRBI outlets after district counting:", rbi_total)
print("Outlets included in final 640 districts:", final_total)
print("Outlets not included in final 640 districts:", excluded_outlets)

print("\nPercentage of RBI outlets included:")
print(round((final_total / rbi_total) * 100, 2), "%")

print("\nPercentage of RBI outlets not included:")
print(round((excluded_outlets / rbi_total) * 100, 2), "%")



# ============================================================
# 16. IDENTIFY EXCLUDED RBI OUTLETS - CORRECTED
# ============================================================

print("\n" + "=" * 70)
print("16. IDENTIFYING EXCLUDED RBI OUTLETS")
print("=" * 70)

# ------------------------------------------------------------
# Use the ORIGINAL Census 2011 State-District pairs
# ------------------------------------------------------------

census_pairs = set(
    zip(
        districts["State"],
        districts["District"]
    )
)

# ------------------------------------------------------------
# Aggregate RBI outlets by Census 2011 district
# ------------------------------------------------------------

rbi_2011_audit = (
    rbi_to_2011_df
    .groupby(
        [
            "Census_2011_State",
            "Census_2011_District"
        ],
        as_index=False
    )["Banking_Outlets"]
    .sum()
)

# ------------------------------------------------------------
# Identify RBI district groups NOT belonging to the
# final 640 Census 2011 districts
# ------------------------------------------------------------

excluded_groups = rbi_2011_audit[
    ~rbi_2011_audit.apply(
        lambda row: (
            row["Census_2011_State"],
            row["Census_2011_District"]
        ) in census_pairs,
        axis=1
    )
].copy()

# ------------------------------------------------------------
# Calculate excluded outlets
# ------------------------------------------------------------

excluded_outlets_section16 = (
    excluded_groups["Banking_Outlets"].sum()
)

# ------------------------------------------------------------
# Expected excluded outlets from Section 15
# ------------------------------------------------------------

expected_excluded_outlets = (
    rbi_total - final_total
)

difference = (
    excluded_outlets_section16 -
    expected_excluded_outlets
)

# ------------------------------------------------------------
# Print results
# ------------------------------------------------------------

print("\nExcluded RBI district groups:")
print(len(excluded_groups))

print("\nExcluded banking outlets:")
print(excluded_outlets_section16)

print("\nExpected excluded outlets from Section 15:")
print(expected_excluded_outlets)

print("\nDifference between Section 15 and Section 16:")
print(difference)

# ------------------------------------------------------------
# Final check
# ------------------------------------------------------------

if difference == 0:

    print("\nEXCLUSION CHECK: PASSED")
    print(
        "Section 15 and Section 16 have the same "
        "excluded outlet total."
    )

else:

    print("\nEXCLUSION CHECK: FAILED")
    print(
        "Section 15 and Section 16 do not have "
        "the same excluded outlet total."
    )

# ------------------------------------------------------------
# TOP EXCLUDED DISTRICTS
# ------------------------------------------------------------

print("\n--- TOP EXCLUDED DISTRICTS ---")

if len(excluded_groups) > 0:

    print(
        excluded_groups
        .sort_values(
            "Banking_Outlets",
            ascending=False
        )
        .head(30)
        .to_string(index=False)
    )

else:

    print(
        "NONE - ALL RBI DISTRICT GROUPS BELONG "
        "TO THE 640 CENSUS DISTRICTS!"
    )

# ------------------------------------------------------------
# Save excluded district audit
# ------------------------------------------------------------

excluded_groups.to_csv(
    "dataa/processed/excluded_rbi_districts.csv",
    index=False
)

print(
    "\nExcluded district audit saved:"
)

print(
    "dataa/processed/excluded_rbi_districts.csv"
)
