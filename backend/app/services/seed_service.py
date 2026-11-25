import json
import math
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.line import ProductionLine
from app.models.parameter import Parameter, ParameterSpecification
from app.models.sand_batch import SandBatch
from app.models.sand_test import SandTestRecord, SandTestValue
from app.models.rejection import CastingProduct, DefectCategory, RejectionRecord
from app.models.complaint import CustomerComplaint
from app.models.investigation import RootCauseInvestigation
from app.models.alert import QualityAlert
from app.models.audit import AuditLog
from app.services.audit_service import append_audit_event


def seed_demo_supplemental_records(db: Session) -> None:
    """
    Populates SandBatch and RootCauseInvestigation tables if empty in demo mode,
    without modifying or resetting existing records.
    """
    if not settings.is_demo_enabled():
        return

    now = datetime.now(timezone.utc)
    if db.query(SandBatch).count() == 0:
        op = db.query(User).filter(User.username == "operator").first()
        op_id = op.id if op else None
        batches = []
        for l_idx, line_code in enumerate(["D1", "D2", "D3", "D4"]):
            for b_idx in range(3):
                ts = now - timedelta(hours=b_idx * 2 + l_idx)
                batches.append(
                    SandBatch(
                        batch_number=f"BAT-{line_code}-{ts.strftime('%Y%m%d')}-{80 - b_idx:03d}",
                        line_code=line_code,
                        muller_id="Muller-A (Simpson 2G)" if b_idx % 2 == 0 else "Muller-B (Eirich R19)",
                        batch_weight_kg=2000.0,
                        bentonite_addition_kg=25.0 + b_idx * 0.5,
                        coal_dust_addition_kg=12.0 + (0.2 if b_idx == 1 else 0.0),
                        new_sand_addition_kg=100.0,
                        return_sand_kg=1863.0,
                        water_addition_liters=34.0 + (4.5 if line_code == "D2" and b_idx == 0 else b_idx * 0.3),
                        cycle_time_seconds=120 + b_idx * 2,
                        operator_id=op_id,
                        timestamp=ts,
                        notes="Initial demo muller batch feed",
                    )
                )
        db.add_all(batches)
        db.commit()

    if db.query(RootCauseInvestigation).count() == 0:
        qe = db.query(User).filter(User.username == "quality_engineer").first()
        moisture = db.query(Parameter).filter(Parameter.code == "MOISTURE").first()
        porosity = db.query(DefectCategory).filter(DefectCategory.code == "POROSITY").first()
        whys = [
            "Why 1: Why did porosity reject rate increase? -> Excessive steam bubbles trapped during mold filling.",
            "Why 2: Why was excess steam generated? -> Green sand moisture content exceeded 4.0% (USL is 3.7%).",
            "Why 3: Why was sand moisture over 4.0%? -> Automated water dosing valve at Muller #2 remained open 8 seconds too long.",
            "Why 4: Why did the valve stay open? -> Optical moisture sensor lens was coated in bentonite dust, misreading return sand as dry.",
            "Why 5 (Root Cause): Why was the lens coated? -> Scheduled bi-weekly air purge jet cleaning maintenance was skipped during shift transition.",
        ]
        fishbone = {
            "man": "Skipped maintenance log; Operator did not manually cross-verify moisture on Moisture Teller balance.",
            "machine": "Muller-2 automated water solenoid valve stuck; air purge nozzle pressure low (1.8 bar vs 4.0 bar).",
            "material": "Incoming bentonite shipment had higher fines percentage; return sand temperature elevated to 42 C.",
            "method": "Mulling cycle completed before full water absorption; fast-track cycle was enabled.",
            "measurement": "Optical moisture probe calibrated 45 days ago; baseline drift of +0.35% detected.",
            "environment": "High ambient air relative humidity (88%) in the sand preparation hall.",
        }
        inv = RootCauseInvestigation(
            title="Line D2 Porosity Spike Investigation (Moisture Excursion)",
            investigation_number="RCA-D2-2026-001",
            line_code="D2",
            parameter_id=moisture.id if moisture else None,
            defect_category_id=porosity.id if porosity else None,
            lag_hours=12,
            correlation_stat=0.68,
            p_value=0.002,
            five_why_analysis=json.dumps(whys),
            fishbone_factors=json.dumps(fishbone),
            findings="Time-lagged correlation (12h) flagged strong association between moisture excursions >3.8% and porosity scrap.",
            conclusion="Implemented daily automated sensor air-purge check at shift handover and PLC moisture interlock above 3.70%.",
            status="VALIDATED",
            version=1,
            investigator_id=qe.id if qe else None,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        )
        db.add(inv)
        db.commit()


def seed_foundry_data(db: Session, force: bool = False):
    """
    Populates realistic demo data for lines D1, D2, D3, D4 ONLY when demo mode is enabled.
    Refuses execution in production environments.
    """
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("Demo seeding is strictly forbidden in production environment.")
    if not settings.is_demo_enabled() and not force:
        return

    existing_user = db.query(User).first()
    if existing_user and not force:
        seed_demo_supplemental_records(db)
        return

    # Clear existing if force (demo/test only)
    if force:
        db.query(AuditLog).delete()
        db.query(QualityAlert).delete()
        db.query(RootCauseInvestigation).delete()
        db.query(CustomerComplaint).delete()
        db.query(RejectionRecord).delete()
        db.query(SandTestValue).delete()
        db.query(SandTestRecord).delete()
        db.query(SandBatch).delete()
        db.query(ParameterSpecification).delete()
        db.query(Parameter).delete()
        db.query(DefectCategory).delete()
        db.query(CastingProduct).delete()
        db.query(ProductionLine).delete()
        db.query(User).delete()
        db.commit()

    print("Seeding Foundry Quality 4.0 data...")

    # 1. Users
    users = [
        User(username="operator", email="operator@foundry4.com", full_name="Ramesh Kumar (Shop Floor Op)", role="operator", hashed_password=hash_password("operator123")),
        User(username="quality_engineer", email="qe@foundry4.com", full_name="Dr. Priya Sundaram (Quality Lead)", role="quality_engineer", hashed_password=hash_password("quality123")),
        User(username="supervisor", email="supervisor@foundry4.com", full_name="Anand Verma (Shift Incharge)", role="supervisor", hashed_password=hash_password("super123")),
        User(username="admin", email="admin@foundry4.com", full_name="S. Natarajan (Plant Quality Head)", role="quality_manager", hashed_password=hash_password("admin123")),
    ]
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)
    admin_id = users[3].id
    qe_id = users[1].id
    op_id = users[0].id

    # 2. Production Lines
    lines = [
        ProductionLine(code="D1", name="Disamatic Line D1 (Automotive Engine Block)", description="High pressure vertical flaskless molding line (Disamatic 2013 MK5)", capacity_tph=55.0),
        ProductionLine(code="D2", name="Disamatic Line D2 (Transmission Housings)", description="High pressure horizontal flaskless molding line (Disa 2110)", capacity_tph=45.0),
        ProductionLine(code="D3", name="Disamatic Line D3 (Hydraulic Pump & Valves)", description="Automatic green sand molding line (Disa Match 24/28)", capacity_tph=40.0),
        ProductionLine(code="D4", name="Disamatic Line D4 (General Commercial Castings)", description="High volume flaskless vertical molding line (Disa 2130)", capacity_tph=50.0),
    ]
    db.add_all(lines)
    db.commit()

    # 3. Parameters
    parameters = [
        # Physical Parameters (Hourly)
        Parameter(
            code="MOISTURE", name="Moisture Content", category="PHYSICAL", unit="%", frequency="HOURLY",
            target_value=3.40, lsl=3.10, usl=3.70, lcl_historical=3.15, ucl_historical=3.65,
            testing_method="Moisture Teller (Infrared halogen drying balance)", data_validation_min=1.0, data_validation_max=6.0,
            description="Crucial for sand plasticity and mold hardness. High moisture causes porosity and gas defects."
        ),
        Parameter(
            code="COMPACT", name="Compactability", category="PHYSICAL", unit="%", frequency="HOURLY",
            target_value=42.0, lsl=38.0, usl=46.0, lcl_historical=39.0, ucl_historical=45.0,
            testing_method="Pneumatic compactability cylinder (Three-ram squeeze)", data_validation_min=20.0, data_validation_max=65.0,
            description="Indicator of temper water required. Influences sand flowability and mold consistency."
        ),
        Parameter(
            code="GCS", name="Green Compression Strength", category="PHYSICAL", unit="N/cm²", frequency="HOURLY",
            target_value=16.5, lsl=14.5, usl=18.5, lcl_historical=14.8, ucl_historical=18.2,
            testing_method="Universal Sand Strength Machine (0-20 N/cm² load cell)", data_validation_min=8.0, data_validation_max=25.0,
            description="Resistance of green sand mold against metal static head and handling stress."
        ),
        Parameter(
            code="PERM", name="Permeability", category="PHYSICAL", unit="Perm No.", frequency="HOURLY",
            target_value=135.0, lsl=115.0, usl=160.0, lcl_historical=118.0, ucl_historical=155.0,
            testing_method="Electric Permmeter (2000 cm³ air displacement through standard AFS specimen)", data_validation_min=50.0, data_validation_max=250.0,
            description="Measures gas venting capability of the sand mold. Low permeability causes blowholes."
        ),
        Parameter(
            code="SHEAR", name="Green Shear Strength", category="PHYSICAL", unit="N/cm²", frequency="HOURLY",
            target_value=4.20, lsl=3.50, usl=5.00, lcl_historical=3.60, ucl_historical=4.80,
            testing_method="Shear head assembly on Universal Sand Tester", data_validation_min=1.5, data_validation_max=8.0,
            description="Determines mold ability to withstand stripping and parting line shear forces."
        ),
        Parameter(
            code="HARDNESS", name="Mold Hardness", category="PHYSICAL", unit="B-Scale", frequency="HOURLY",
            target_value=88.0, lsl=82.0, usl=93.0, lcl_historical=84.0, ucl_historical=92.0,
            testing_method="Spring-loaded indentation hardness tester (Dietert B scale)", data_validation_min=60.0, data_validation_max=100.0,
            description="Density and compaction rigidity of mold surface. Low hardness promotes sand erosion."
        ),
        Parameter(
            code="ACTIVE_CLAY", name="Active Clay (Methylene Blue)", category="PHYSICAL", unit="%", frequency="HOURLY",
            target_value=7.20, lsl=6.50, usl=8.00, lcl_historical=6.60, ucl_historical=7.80,
            testing_method="Methylene Blue titration (MB value determination)", data_validation_min=4.0, data_validation_max=12.0,
            description="Percentage of effective sodium/calcium bentonite available to bind sand grains."
        ),
        Parameter(
            code="TOTAL_CLAY", name="Total Clay (AFS Clay)", category="PHYSICAL", unit="%", frequency="HOURLY",
            target_value=9.80, lsl=8.80, usl=11.00, lcl_historical=9.00, ucl_historical=10.60,
            testing_method="AFS sedimentation wash siphon method", data_validation_min=5.0, data_validation_max=16.0,
            description="Sum of active bonding clay and thermally deactivated dead clay."
        ),
        Parameter(
            code="LOI", name="Loss on Ignition", category="PHYSICAL", unit="%", frequency="HOURLY",
            target_value=4.00, lsl=3.40, usl=4.80, lcl_historical=3.50, ucl_historical=4.60,
            testing_method="Muffle furnace combustion at 950°C for 2 hours", data_validation_min=1.5, data_validation_max=8.0,
            description="Measures volatile carbonaceous lustrous carbon additives."
        ),
        Parameter(
            code="GFN", name="Grain Fineness Number", category="PHYSICAL", unit="AFS GFN", frequency="HOURLY",
            target_value=52.0, lsl=48.0, usl=56.0, lcl_historical=49.0, ucl_historical=55.0,
            testing_method="Ro-Tap sieve shaker with 11 standard ASTM/AFS sieves", data_validation_min=35.0, data_validation_max=75.0,
            description="Average grain distribution size of the silica base sand."
        ),
        Parameter(
            code="WET_TENSILE", name="Wet Tensile Strength", category="PHYSICAL", unit="N/cm²", frequency="HOURLY",
            target_value=0.28, lsl=0.22, usl=0.35, lcl_historical=0.23, ucl_historical=0.34,
            testing_method="Tensile test at condensation condensation zone", data_validation_min=0.10, data_validation_max=0.60,
            description="Crucial for preventing scabs and rat-tails in ductile iron casting."
        ),
        Parameter(
            code="SAND_TEMP", name="Return Sand Temperature", category="PHYSICAL", unit="°C", frequency="HOURLY",
            target_value=32.0, lsl=25.0, usl=40.0, lcl_historical=26.0, ucl_historical=38.0,
            testing_method="Online infrared pyrometer and penetration probe", data_validation_min=15.0, data_validation_max=65.0,
            description="Sand temperature entering muller. Temperatures > 40°C cause rapid moisture evaporation."
        ),
        # Chemical Parameters (Shift-wise)
        Parameter(
            code="VOLATILE", name="Volatile Matter", category="CHEMICAL", unit="%", frequency="SHIFT",
            target_value=2.40, lsl=1.80, usl=3.00, lcl_historical=1.90, ucl_historical=2.85,
            testing_method="Volatile matter crucibles at 900°C for 7 minutes", data_validation_min=0.5, data_validation_max=5.0,
            description="Gas generating constituents from coal dust / lustrous carbon."
        ),
        Parameter(
            code="DEAD_CLAY", name="Dead Clay Content", category="CHEMICAL", unit="%", frequency="SHIFT",
            target_value=2.60, lsl=1.80, usl=3.40, lcl_historical=1.90, ucl_historical=3.20,
            testing_method="Differential computation: Total Clay minus Active Clay", data_validation_min=0.5, data_validation_max=6.0,
            description="Burnt clay without bonding capacity. Elevates water demand and reduces permeability."
        ),
        Parameter(
            code="BENTONITE", name="Bentonite Addition Rate", category="CHEMICAL", unit="%", frequency="SHIFT",
            target_value=0.65, lsl=0.45, usl=0.85, lcl_historical=0.48, ucl_historical=0.82,
            testing_method="Batch addition load cell scale audit", data_validation_min=0.1, data_validation_max=2.0,
            description="Fresh active bentonite replenishment rate per muller cycle."
        )
    ]
    db.add_all(parameters)
    db.commit()
    for p in parameters:
        db.refresh(p)
        # Add initial revision record
        rev = ParameterSpecification(
            parameter_id=p.id,
            revision_number=1,
            target_value=p.target_value,
            lsl=p.lsl,
            usl=p.usl,
            change_reason="Initial baseline release for Quality 4.0 foundry lines D1-D4",
            approved_by_id=admin_id
        )
        db.add(rev)
    db.commit()

    # 4. Casting Products
    products = [
        CastingProduct(part_number="TM-V6-ENG", part_name="V6 Engine Cylinder Block", customer_name="TurboMotors India Ltd", material_grade="EN-GJS-500-7", weight_kg=42.5),
        CastingProduct(part_number="APX-GB-45", part_name="Commercial Gearbox Housing", customer_name="Apex Transmission Systems", material_grade="EN-GJL-250", weight_kg=34.0),
        CastingProduct(part_number="FLD-PMP-12", part_name="High-Pressure Pump Casing", customer_name="FluidTech Hydraulics", material_grade="EN-GJS-600-3", weight_kg=16.8),
        CastingProduct(part_number="FSV-VLV-80", part_name="Flanged Control Valve Body", customer_name="FlowServe Industrial", material_grade="EN-GJS-400-18LT", weight_kg=22.4),
        CastingProduct(part_number="BRM-CAL-F2", part_name="Front Brake Caliper Bracket", customer_name="BremboAuto Systems", material_grade="EN-GJS-500-7", weight_kg=8.5),
    ]
    db.add_all(products)
    db.commit()
    for prod in products:
        db.refresh(prod)

    # 5. Defect Categories
    defects = [
        DefectCategory(code="POROSITY", name="Gas Porosity / Pinholes", description="Microscopic spherical voids caused by trapped steam or volatile gas", potential_sand_causes="High moisture, low permeability, high volatile coal dust"),
        DefectCategory(code="BLOWHOLE", name="Blowholes", description="Large rounded internal or surface cavities from gas evolution", potential_sand_causes="Very high moisture, insufficient mold venting, low permeability"),
        DefectCategory(code="SAND_INCLUSION", name="Sand Wash & Inclusions", description="Displaced sand grains embedded in casting surface or interior", potential_sand_causes="Low green compression strength, low mold hardness, brittle sand"),
        DefectCategory(code="SCABBING", name="Expansion Scabs & Rat-tails", description="Rough projection of metal separated by a thin layer of sand", potential_sand_causes="Low wet tensile strength, high dead clay, high mold expansion"),
        DefectCategory(code="MISMATCH", name="Mold Mismatch / Shift", description="Displacement between cope and drag parting line", potential_sand_causes="Guide pin wear, mold distortion, uneven sand pack"),
        DefectCategory(code="COLD_SHUT", name="Cold Shut / Misrun", description="Discontinuity from two metal streams failing to fuse", potential_sand_causes="Low pouring temperature, excessive sand mold chilling"),
        DefectCategory(code="SHRINKAGE", name="Shrinkage Cavity", description="Void caused by volumetric contraction during solidification", potential_sand_causes="Mold wall movement due to low mold hardness"),
        DefectCategory(code="SURFACE_DEFECT", name="Surface Roughness / Burn-in", description="Metal penetration into sand grain interstices", potential_sand_causes="Coarse sand (low GFN), low lustrous carbon, poor compaction"),
    ]
    db.add_all(defects)
    db.commit()
    for d in defects:
        db.refresh(d)

    # 6. Generate 30 Days of Hourly & Shift Sand Tests across D1, D2, D3, D4
    # Real-world behavior:
    # D1: Stable
    # D2: Process drift on Days 12-14 (Moisture surge to 3.8-4.2% causing Porosity surge)
    # D3: Low permeability on Days 20-22 (Permeability drops to 105-112 causing Blowholes)
    # D4: Stable commercial production
    base_date = datetime.now(timezone.utc) - timedelta(days=29)

    param_map = {p.code: p for p in parameters}
    prod_map = {p.part_number: p for p in products}
    defect_map = {d.code: d for d in defects}

    sand_records_to_create = []
    sand_values_to_create = []

    print("Generating 30 days of hourly and shift sand test series...")

    # We generate tests for every 3 hours across 30 days for each line (8 tests/day * 30 days = 240 records/line = 960 total)
    for day in range(30):
        current_day_date = base_date + timedelta(days=day)
        date_str = current_day_date.strftime("%Y-%m-%d")

        for line_code in ["D1", "D2", "D3", "D4"]:
            for hour in [2, 5, 8, 11, 14, 17, 20, 23]:
                shift_num = 1 if 6 <= hour < 14 else (2 if 14 <= hour < 22 else 3)
                test_time = current_day_date.replace(hour=hour, minute=15, second=0)

                test_num = f"ST-{line_code}-{date_str.replace('-','')}-H{hour:02d}"
                batch_no = f"BAT-{line_code}-{date_str.replace('-','')}-S{shift_num}"

                record = SandTestRecord(
                    test_number=test_num,
                    line_code=line_code,
                    test_type="HOURLY_PHYSICAL",
                    test_date=date_str,
                    shift=shift_num,
                    test_hour=hour,
                    timestamp=test_time,
                    batch_number=batch_no,
                    operator_id=op_id,
                    status="CONFORMING",
                    notes="Hourly sand control sample"
                )
                db.add(record)
                db.flush()

                # Generate realistic parameter values
                record_status = "CONFORMING"

                for p_code in ["MOISTURE", "COMPACT", "GCS", "PERM", "SHEAR", "HARDNESS", "ACTIVE_CLAY", "TOTAL_CLAY", "LOI", "GFN", "WET_TENSILE", "SAND_TEMP"]:
                    p = param_map[p_code]
                    base_val = p.target_value
                    
                    # Add pseudo-random deterministic variation using sine waves
                    seed_factor = (day * 31 + hour * 7 + ord(line_code[1]) * 13) % 100
                    noise = (math.sin(seed_factor) * 0.4 + math.cos(seed_factor * 1.5) * 0.3)

                    # Normal standard deviations
                    sigma_approx = (p.usl - p.lsl) / 6.0
                    val = base_val + noise * sigma_approx

                    # Introduce realistic anomalies:
                    # Line D2: Days 12-14 has a water dosing valve failure -> moisture drift
                    if line_code == "D2" and 12 <= day <= 14:
                        if p_code == "MOISTURE":
                            val = 3.85 + (day - 12) * 0.12 + abs(noise) * 0.15  # Out of spec high (3.85 - 4.15)
                        elif p_code == "COMPACT":
                            val = 46.5 + abs(noise) * 2.0  # Compactability jumps
                        elif p_code == "GCS":
                            val = 13.8 - abs(noise) * 0.6  # Strength drops

                    # Line D3: Days 20-22 has fine sand contamination -> Permeability drops
                    if line_code == "D3" and 20 <= day <= 22:
                        if p_code == "PERM":
                            val = 110.0 - (day - 20) * 3.5 - abs(noise) * 4.0  # Permeability drops < 115
                        elif p_code == "GFN":
                            val = 58.5 + abs(noise) * 1.5  # Sand becomes too fine

                    val = round(val, 2)
                    
                    # Status check
                    v_status = "OK"
                    if p.usl is not None and val > p.usl:
                        v_status = "OUT_OF_SPEC"
                        record_status = "OUT_OF_SPEC"
                    elif p.lsl is not None and val < p.lsl:
                        v_status = "OUT_OF_SPEC"
                        record_status = "OUT_OF_SPEC"
                    elif (p.usl is not None and val > (p.usl - 0.15 * (p.usl - p.lsl))) or \
                         (p.lsl is not None and val < (p.lsl + 0.15 * (p.usl - p.lsl))):
                        v_status = "WARNING"
                        if record_status == "CONFORMING":
                            record_status = "WARNING"

                    v = SandTestValue(
                        record_id=record.id,
                        parameter_id=p.id,
                        measured_value=val,
                        unit=p.unit,
                        specification_revision=1,
                        status=v_status
                    )
                    db.add(v)

                record.status = record_status

            # Shift-wise chemical test once a day for each shift
            for s_num in [1, 2]:
                chem_test_num = f"ST-CHEM-{line_code}-{date_str.replace('-','')}-S{s_num}"
                chem_record = SandTestRecord(
                    test_number=chem_test_num,
                    line_code=line_code,
                    test_type="SHIFT_CHEMICAL",
                    test_date=date_str,
                    shift=s_num,
                    test_hour=s_num * 8,
                    timestamp=current_day_date.replace(hour=s_num*8, minute=30, second=0),
                    operator_id=op_id,
                    status="CONFORMING",
                    notes="Shift laboratory composite chemical analysis"
                )
                db.add(chem_record)
                db.flush()

                for chem_code in ["VOLATILE", "DEAD_CLAY", "BENTONITE"]:
                    cp = param_map[chem_code]
                    c_seed = (day * 17 + s_num * 11 + ord(line_code[1])) % 50
                    c_noise = math.sin(c_seed) * 0.3
                    c_val = round(cp.target_value + c_noise * ((cp.usl - cp.lsl) / 6.0), 2)
                    cv_status = "OK"
                    if c_val > cp.usl or c_val < cp.lsl:
                        cv_status = "OUT_OF_SPEC"
                    db.add(SandTestValue(
                        record_id=chem_record.id,
                        parameter_id=cp.id,
                        measured_value=c_val,
                        unit=cp.unit,
                        specification_revision=1,
                        status=cv_status
                    ))

    db.commit()

    # 7. Generate Rejection Records linked to Shifts & Defect Categories
    print("Generating casting rejection records...")
    rejections = []
    
    # Product line mappings
    line_products = {
        "D1": [products[0], products[4]],  # Engine Block & Caliper
        "D2": [products[1]],               # Gearbox Housing
        "D3": [products[2]],               # Pump Casing
        "D4": [products[3]],               # Valve Body
    }

    rej_counter = 1000
    for day in range(30):
        current_day_date = base_date + timedelta(days=day)
        date_str = current_day_date.strftime("%Y-%m-%d")

        for line_code in ["D1", "D2", "D3", "D4"]:
            for shift_num in [1, 2]:
                prods = line_products[line_code]
                for prod in prods:
                    rej_counter += 1
                    rej_num = f"REJ-{line_code}-{date_str.replace('-','')}-{rej_counter}"
                    inspected = 400 + (day * 5) % 150
                    
                    # Base defect rates
                    # Normal scrap is 1.5% to 2.8%
                    scrap_rate = 1.8 + math.sin(day * 0.5 + shift_num) * 0.6
                    defect_cat = defect_map["SAND_INCLUSION"]

                    # Induce realistic defect correlation:
                    # Line D2: When moisture was high on days 12-14, rejections on days 13-15 (lag window) surge for POROSITY
                    if line_code == "D2" and 13 <= day <= 15:
                        scrap_rate = 5.6 + (day - 12) * 1.2
                        defect_cat = defect_map["POROSITY"]
                        root_cause = "Candidate root cause: Excessive mold moisture and high compactability causing steam entrapment during mold filling."

                    # Line D3: When permeability dropped on days 20-22, rejections surge for BLOWHOLE
                    elif line_code == "D3" and 21 <= day <= 23:
                        scrap_rate = 4.8 + (day - 20) * 0.9
                        defect_cat = defect_map["BLOWHOLE"]
                        root_cause = "Candidate root cause: Inadequate mold venting due to fine sand buildup (low permeability)."
                    else:
                        root_cause = "Normal process variation within allowable casting acceptance threshold."

                    rejected_qty = max(2, int(round((scrap_rate / 100.0) * inspected)))
                    actual_rate = round((rejected_qty / inspected) * 100.0, 2)

                    rej_time = current_day_date.replace(hour=shift_num * 10, minute=0, second=0)

                    rejection = RejectionRecord(
                        rejection_number=rej_num,
                        production_date=date_str,
                        line_code=line_code,
                        shift=shift_num,
                        product_id=prod.id,
                        defect_category_id=defect_cat.id,
                        rejected_qty=rejected_qty,
                        inspected_qty=inspected,
                        rejection_rate=actual_rate,
                        batch_number=f"BAT-{line_code}-{date_str.replace('-','')}-S{shift_num}",
                        detection_stage="Shotblast Inspection" if actual_rate > 3.0 else "Visual Shakeout",
                        severity="CRITICAL" if actual_rate > 4.5 else ("MAJOR" if actual_rate > 2.5 else "MINOR"),
                        root_cause_candidate=root_cause,
                        responsible_person="Quality Inspection Team B",
                        status="INVESTIGATING" if actual_rate > 3.5 else "RECORDED",
                        timestamp=rej_time
                    )
                    db.add(rejection)

    db.commit()

    # 8. Customer Complaints & 8D CAPA
    print("Generating customer complaints and CAPA records...")
    complaints = [
        CustomerComplaint(
            complaint_number="CMP-2026-081",
            customer_name="TurboMotors India Ltd",
            received_date=(datetime.now(timezone.utc) - timedelta(days=12)).strftime("%Y-%m-%d"),
            product_id=products[0].id,
            defect_category_id=defect_map["POROSITY"].id,
            batch_number="BAT-D1-RECENT",
            line_code="D1",
            affected_qty=14,
            severity="HIGH",
            description="Sub-surface gas porosity unveiled during finish face-milling of engine deck surface. Caused cutter tool chatter and pressure test leakage.",
            d1_team="P. Sundaram (Quality Lead), A. Verma (Foundry Incharge), S. Ghosh (Tooling Eng)",
            d2_problem="Finish face-milling revealed spherical porosity clusters on top deck of Cylinder Block V6.",
            d3_containment="100% sonic inspection applied to warehouse stock of 420 blocks. 14 suspect blocks quarantined.",
            d4_root_cause="Correlation analysis confirmed moisture excursion to 3.78% combined with delayed core venting.",
            d5_corrective_action="Calibrated automated sand muller water moisture sensor. Added extra vent relief plugs to core box.",
            d6_validation="Zero porosity observed across next 3 production batches (N=1,200 blocks leak tested OK).",
            d7_preventive_action="Integrated real-time automated SPC alert directly into muller PLC moisture bypass loop.",
            d8_closure="Formal 8D report signed by TurboMotors Supplier Quality Assurance.",
            responsible_person="Dr. Priya Sundaram",
            due_date=(datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d"),
            status="CAPA_PENDING"
        ),
        CustomerComplaint(
            complaint_number="CMP-2026-085",
            customer_name="Apex Transmission Systems",
            received_date=(datetime.now(timezone.utc) - timedelta(days=8)).strftime("%Y-%m-%d"),
            product_id=products[1].id,
            defect_category_id=defect_map["SAND_INCLUSION"].id,
            batch_number="BAT-D2-RECENT",
            line_code="D2",
            affected_qty=28,
            severity="CRITICAL",
            description="Sand particle inclusions trapped inside oil gallery passage of transmission casing.",
            d1_team="M. Karthik (Machining Lead), R. Kumar (Molding Lead)",
            d2_problem="Foreign silica sand grains dislodged during CNC bore machining.",
            d3_containment="High pressure endoscopic flush and boroscope inspection of all dispatch lots.",
            d4_root_cause="Green compression strength dropped below 14.5 N/cm² due to deficient bentonite active clay.",
            d5_corrective_action="Increased bentonite dosing by 0.15% per batch. Raised muller cycle time to 135 seconds.",
            d6_validation="Lab tests confirmed GCS increased to stable 16.8 N/cm².",
            d7_preventive_action="Set mandatory automated lockout on muller discharge gate if cycle time < 120s.",
            d8_closure="Pending customer re-audit next week.",
            responsible_person="Anand Verma",
            due_date=(datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d"),
            status="UNDER_INVESTIGATION"
        )
    ]
    db.add_all(complaints)
    db.commit()

    # 9. Quality Alerts
    print("Generating active and historical alerts...")
    alerts = [
        QualityAlert(
            alert_code="ALT-D2-MOIST-CRIT",
            line_code="D2",
            parameter_id=param_map["MOISTURE"].id,
            alert_type="SPEC_VIOLATION",
            severity="CRITICAL",
            description="Moisture Content on Line D2 exceeded Upper Specification Limit (USL 3.70%). Measured 4.05%. Immediate sand adjustment required.",
            status="OPEN",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
        ),
        QualityAlert(
            alert_code="ALT-D3-PERM-RULE1",
            line_code="D3",
            parameter_id=param_map["PERM"].id,
            alert_type="SPC_RULE_VIOLATION",
            severity="WARNING",
            description="Rule 1 Violation: Permeability on Line D3 (108.0 Perm No.) dropped below Lower Control Limit (LCL 118.0).",
            nelson_rule_triggered="Rule 1: Beyond 3 Sigma",
            status="ACKNOWLEDGED",
            acknowledged_by_id=qe_id,
            acknowledged_at=datetime.now(timezone.utc) - timedelta(hours=5),
            resolution_notes="Checked exhaust bag filters. Increased new sand addition by 25 kg/batch.",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=6)
        ),
        QualityAlert(
            alert_code="ALT-D1-COMPACT-RULE2",
            line_code="D1",
            parameter_id=param_map["COMPACT"].id,
            alert_type="SPC_RULE_VIOLATION",
            severity="WARNING",
            description="Rule 2 Violation: Nine consecutive compactability measurements above center line on Line D1.",
            nelson_rule_triggered="Rule 2: Nine Points on Same Side",
            status="RESOLVED",
            acknowledged_by_id=qe_id,
            acknowledged_at=datetime.now(timezone.utc) - timedelta(days=1),
            resolved_by_id=admin_id,
            resolved_at=datetime.now(timezone.utc) - timedelta(hours=18),
            resolution_notes="Returned muller moisture setpoint from 3.55% to 3.40%. Process centered.",
            timestamp=datetime.now(timezone.utc) - timedelta(days=1, hours=2)
        )
    ]
    db.add_all(alerts)
    db.commit()

    # 10. Audit Log Initial Records (hash-chained)
    print("Writing initial IATF audit trail entries...")
    admin_user = users[3]
    qe_user = users[1]
    append_audit_event(
        db,
        admin_user,
        "CREATE",
        "System",
        "SYS-INIT",
        new_value={"version": settings.VERSION, "lines": ["D1", "D2", "D3", "D4"], "compliance": "IATF 16949 / ISO 9001"},
        reason="Initial installation and deployment of PS-010 Quality 4.0 Platform",
        commit=True,
    )
    append_audit_event(
        db,
        admin_user,
        "CREATE",
        "ParameterSpecification",
        "REV-1",
        new_value={"revision": 1, "approved_parameters": 15, "lines": ["D1", "D2", "D3", "D4"]},
        reason="Approved baseline specifications for green sand physical & chemical testing",
        commit=True,
    )
    append_audit_event(
        db,
        qe_user,
        "ACKNOWLEDGE",
        "QualityAlert",
        "ALT-D3-PERM-RULE1",
        new_value={"status": "ACKNOWLEDGED"},
        reason="Investigated baghouse filter differential pressure and sand fines buildup",
        commit=True,
    )

    seed_demo_supplemental_records(db)
    print("Seeding completed successfully! PS-010 database populated with realistic Quality 4.0 foundry dataset.")
