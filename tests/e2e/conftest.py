"""
Pytest fixtures for Tier 1 Family Law E2E Tests.

This file provides realistic family law document fixtures for testing
the 15 new Tier 1 patterns added to family_law.yaml.

Pattern Groups:
1. Jurisdiction (5 entities): HOME_STATE, EMERGENCY_JURISDICTION,
   EXCLUSIVE_CONTINUING_JURISDICTION, SIGNIFICANT_CONNECTION, FOREIGN_CUSTODY_ORDER
2. Procedural (5 entities): DISSOLUTION_PETITION, TEMPORARY_ORDER, FINAL_DECREE,
   MODIFICATION_PETITION, GUARDIAN_AD_LITEM_APPOINTMENT
3. Property (2 entities): COMMUNITY_PROPERTY, SEPARATE_PROPERTY
4. Child Protection (3 entities): CHILD_ABUSE_REPORT, DEPENDENCY_ACTION, PROTECTIVE_CUSTODY
"""

import pytest
from typing import Dict, List


# ============================================================================
# GROUP 1: JURISDICTION FIXTURES (UCCJEA)
# ============================================================================

@pytest.fixture
def uccjea_jurisdiction_text() -> str:
    """
    UCCJEA jurisdiction declaration covering all 5 jurisdiction entities.
    Tests: HOME_STATE, EMERGENCY_JURISDICTION, EXCLUSIVE_CONTINUING_JURISDICTION,
           SIGNIFICANT_CONNECTION, FOREIGN_CUSTODY_ORDER
    """
    return """
DECLARATION RE: JURISDICTION UNDER THE UCCJEA

I, Jennifer Martinez, declare under penalty of perjury:

1. WASHINGTON HOME STATE JURISDICTION:
   Washington is the child's home state under the Uniform Child Custody Jurisdiction
   and Enforcement Act (UCCJEA), RCW 26.27.021. The child, Emma Martinez (DOB:
   March 15, 2018), has lived in Washington with me continuously for the past
   eight years. Washington has home state jurisdiction over this custody matter.

2. CALIFORNIA FOREIGN CUSTODY ORDER:
   In 2020, a California court issued a custody order registered in Washington
   under RCW 26.27.441. This foreign custody order from California Superior Court
   (Case No. FL-2020-12345) granted me primary physical custody. The out-of-state
   order was properly registered with King County Superior Court on June 1, 2020.

3. EXCLUSIVE CONTINUING JURISDICTION:
   Washington retains exclusive continuing jurisdiction over this custody matter
   pursuant to RCW 26.27.211. Both the child and I continue to reside in Washington.
   The continuing exclusive jurisdiction established when the original parenting
   plan was entered remains in effect.

4. SIGNIFICANT CONNECTION JURISDICTION:
   Even if Washington were not the home state, the child has significant connections
   to Washington under RCW 26.27.201. The child attends school in Seattle, receives
   medical care from Seattle Children's Hospital, and substantial evidence exists
   regarding her care, protection, and personal relationships in this state. The
   child and parent have significant connections to Washington.

5. EMERGENCY JURISDICTION PROVISION:
   Should emergency jurisdiction be necessary under RCW 26.27.231, Washington courts
   have authority to exercise emergency jurisdiction due to concerns about the child's
   safety. Emergency protective custody jurisdiction would apply if there were
   imminent harm to the child requiring immediate intervention.

I declare under penalty of perjury under the laws of the State of Washington
that the foregoing is true and correct.

Dated: October 15, 2024
_____________________
Jennifer Martinez
"""


@pytest.fixture
def home_state_simple() -> str:
    """Simple HOME_STATE test case."""
    return "California is the child's home state under UCCJEA."


@pytest.fixture
def emergency_jurisdiction_simple() -> str:
    """Simple EMERGENCY_JURISDICTION test case."""
    return "The court exercised emergency jurisdiction due to imminent harm to the child."


@pytest.fixture
def exclusive_continuing_jurisdiction_simple() -> str:
    """Simple EXCLUSIVE_CONTINUING_JURISDICTION test case."""
    return "Washington retains exclusive continuing jurisdiction over the custody matters."


@pytest.fixture
def significant_connection_simple() -> str:
    """Simple SIGNIFICANT_CONNECTION test case."""
    return "The child has significant connections to Oregon based on substantial evidence."


@pytest.fixture
def foreign_custody_order_simple() -> str:
    """Simple FOREIGN_CUSTODY_ORDER test case."""
    return "A foreign custody order from Nevada was registered in Washington pursuant to RCW 26.27.441."


# ============================================================================
# GROUP 2: PROCEDURAL DOCUMENT FIXTURES
# ============================================================================

@pytest.fixture
def dissolution_petition_text() -> str:
    """
    Complete dissolution petition covering all 5 procedural entities.
    Tests: DISSOLUTION_PETITION, TEMPORARY_ORDER, FINAL_DECREE,
           MODIFICATION_PETITION, GUARDIAN_AD_LITEM_APPOINTMENT
    """
    return """
SUPERIOR COURT OF WASHINGTON FOR KING COUNTY

In re the Marriage of:

JENNIFER MARTINEZ,
    Petitioner,                     No. 24-3-12345-6 SEA
and
                                    PETITION FOR DISSOLUTION OF MARRIAGE
MICHAEL MARTINEZ,                   WITH CHILDREN
    Respondent.

I. PETITION FOR DISSOLUTION

The petitioner files this petition for dissolution of marriage pursuant to
RCW 26.09.020. The parties were married on June 15, 2015, and have one minor
child, Emma Martinez, born March 15, 2018 (age 6). The dissolution petition
was filed on March 1, 2024.

II. TEMPORARY ORDERS REQUESTED

Petitioner requests temporary orders pending dissolution pursuant to RCW 26.09.060.
The temporary order shall include provisions for temporary custody, parenting time,
child support, and use of the family home. An interim order is necessary to maintain
stability for the child during the pendency of this case. Petitioner seeks entry of
pendente lite orders for immediate relief.

III. FINAL DECREE ANTICIPATED

Upon completion of proceedings, petitioner seeks entry of a final decree of dissolution
pursuant to RCW 26.09.070. The final decree should enter on or after the mandatory
90-day waiting period and address all issues regarding custody, support, and property
division. The decree of dissolution will terminate the marriage and establish permanent
parenting arrangements.

IV. GUARDIAN AD LITEM APPOINTMENT

Due to disputes regarding the child's best interests, petitioner requests that the
court appoint a guardian ad litem pursuant to RCW 26.09.110. The GAL appointed should
investigate the custody issues and make recommendations to the court. A guardian ad litem
appointment is necessary to ensure the child's voice is heard in these proceedings.

V. POTENTIAL FUTURE MODIFICATION

Petitioner acknowledges that either party may file a petition to modify the parenting
plan or support orders pursuant to RCW 26.09.170 if substantial changes in circumstances
occur. A modification petition would require showing of changed circumstances and that
modification serves the child's best interests.

Dated: March 1, 2024

_____________________________
Jennifer Martinez, Petitioner
"""


@pytest.fixture
def dissolution_petition_simple() -> str:
    """Simple DISSOLUTION_PETITION test case."""
    return "Petitioner filed a petition for dissolution of marriage on March 15, 2024."


@pytest.fixture
def temporary_order_simple() -> str:
    """Simple TEMPORARY_ORDER test case."""
    return "The court entered temporary orders regarding child custody and support pending final dissolution."


@pytest.fixture
def final_decree_simple() -> str:
    """Simple FINAL_DECREE test case."""
    return "The final decree of dissolution was entered by the court on June 30, 2024."


@pytest.fixture
def modification_petition_simple() -> str:
    """Simple MODIFICATION_PETITION test case."""
    return "Father filed a petition to modify the parenting plan due to changed circumstances."


@pytest.fixture
def guardian_ad_litem_simple() -> str:
    """Simple GUARDIAN_AD_LITEM test case."""
    return "A guardian ad litem was appointed to represent the children's interests in the custody dispute."


# ============================================================================
# GROUP 3: PROPERTY DIVISION FIXTURES
# ============================================================================

@pytest.fixture
def property_division_text() -> str:
    """
    Property characterization declaration covering both property entities.
    Tests: COMMUNITY_PROPERTY, SEPARATE_PROPERTY
    """
    return """
DECLARATION RE: PROPERTY CHARACTERIZATION

I, Jennifer Martinez, declare regarding the characterization of marital property:

I. COMMUNITY PROPERTY

All earnings during marriage are community property pursuant to RCW 26.16.030.
This includes:

1. Marital Home: The family residence at 123 Main Street, Seattle, WA 98101,
   purchased during the marriage in 2016, is community property. The community
   estate includes this real property acquired with earnings during marriage.

2. Retirement Accounts: My 401(k) contributions from 2015-2024 are community property.
   All pension and retirement benefits earned during marriage constitute part of the
   community estate to be divided.

3. Vehicles: The 2020 Honda Accord purchased during marriage with marital earnings
   is community property subject to division.

4. Joint Bank Accounts: All funds in our joint checking and savings accounts accumulated
   during marriage are community property. The community estate includes approximately
   $45,000 in liquid assets.

II. SEPARATE PROPERTY

Property acquired before marriage remains separate pursuant to RCW 26.16.010:

1. Pre-Marital Assets: I owned a condominium before marriage (purchased in 2010).
   This property acquired before marriage is separate property and should remain
   with me. Separate property is not subject to division.

2. Inheritance: I received a $50,000 inheritance from my grandmother in 2020.
   Property acquired by gift or inheritance is separate property under Washington law.
   This inheritance remains separate and should not be divided.

3. Personal Injury Settlement: I received a $30,000 settlement for personal injuries
   sustained in 2022. This separate property award should remain with me as it
   compensates for personal suffering.

I request that the court properly characterize all marital property as community
or separate and divide the community estate equitably pursuant to RCW 26.09.080.

Dated: March 15, 2024

_____________________________
Jennifer Martinez
"""


@pytest.fixture
def community_property_simple() -> str:
    """Simple COMMUNITY_PROPERTY test case."""
    return "All earnings during marriage are community property to be divided between the spouses."


@pytest.fixture
def separate_property_simple() -> str:
    """Simple SEPARATE_PROPERTY test case."""
    return "The property acquired before marriage is separate property and not subject to division."


# ============================================================================
# GROUP 4: CHILD PROTECTION FIXTURES
# ============================================================================

@pytest.fixture
def cps_report_text() -> str:
    """
    CPS investigation report covering all 3 child protection entities.
    Tests: CHILD_ABUSE_REPORT, DEPENDENCY_ACTION, PROTECTIVE_CUSTODY
    """
    return """
CHILD PROTECTIVE SERVICES INVESTIGATION REPORT

Case Number: CPS-2024-9876
Date: October 20, 2024
County: King County, Washington

I. CHILD ABUSE REPORT

On October 15, 2024, a CPS report was filed regarding allegations of physical abuse
and neglect of minor child Emma Martinez (DOB: 3/15/2018, age 6) pursuant to
RCW 26.44.030. The abuse report was submitted by Emma's teacher at Lincoln Elementary
School after observing suspicious bruising on the child's arms and face.

Child protective services report filed: The mandatory reporter observed the following:
- Multiple bruises in various stages of healing on child's arms
- Bruising on left cheek consistent with handprint
- Child appeared fearful and withdrawn
- Child stated "Daddy gets really mad sometimes"

CPS investigated the abuse allegations and conducted interviews with the child,
parents, and collateral witnesses.

II. DEPENDENCY ACTION FILED

Based on the investigation findings, on October 18, 2024, the State filed a
dependency petition in King County Juvenile Court pursuant to RCW 26.44.050.
The dependency action alleges that Emma Martinez is a dependent child within
the meaning of RCW 13.34.030 due to physical abuse and that her health, safety,
and welfare will be endangered if returned to her father's custody.

The juvenile court dependency proceeding is scheduled for shelter care hearing
on October 25, 2024. The dependency petition alleges abuse or neglect requiring
juvenile court intervention.

III. EMERGENCY PROTECTIVE CUSTODY

On October 15, 2024, CPS placed Emma in emergency protective custody pursuant
to RCW 26.44.056. The child was taken into protective custody due to imminent
risk of harm if she remained in father's care. Emergency protective custody was
authorized by the court on an ex parte basis.

The child taken into custody currently resides with maternal grandmother pending
the shelter care hearing. CPS protective custody will remain in effect until the
juvenile court determines appropriate placement.

IV. ONGOING SAFETY PLANNING

Child protective services continues to monitor this case and coordinate services.
Additional assessments are being conducted, including:
- Forensic medical examination
- Forensic interview at Seattle Children's Hospital
- Home studies of potential placement options
- Referrals for therapeutic services for the child

Report prepared by: Sarah Johnson, CPS Investigator
License Number: SW-12345
Date: October 20, 2024
"""


@pytest.fixture
def child_abuse_report_simple() -> str:
    """Simple CHILD_ABUSE_REPORT test case."""
    return "A CPS report was filed regarding allegations of physical abuse of the minor child."


@pytest.fixture
def dependency_action_simple() -> str:
    """Simple DEPENDENCY_ACTION test case."""
    return "The State filed a dependency action in juvenile court alleging abuse and neglect."


@pytest.fixture
def protective_custody_simple() -> str:
    """Simple PROTECTIVE_CUSTODY test case."""
    return "The child was taken into emergency protective custody due to safety concerns."


# ============================================================================
# COMBINED MULTI-ENTITY FIXTURES
# ============================================================================

@pytest.fixture
def multi_entity_jurisdiction() -> str:
    """
    Document containing multiple jurisdiction entities for integration testing.
    Contains: HOME_STATE, SIGNIFICANT_CONNECTION, EXCLUSIVE_CONTINUING_JURISDICTION
    """
    return """
JURISDICTION ANALYSIS

1. Washington is the child's home state under UCCJEA, as the child has resided
   here continuously for six years.

2. Even if not the home state, the child has significant connections to Washington
   based on school enrollment, medical care, and substantial evidence of the child's
   care and protection in this state.

3. Washington retains exclusive continuing jurisdiction over the custody matters
   pursuant to the original parenting plan entered in 2018.
"""


@pytest.fixture
def multi_entity_procedural() -> str:
    """
    Document containing multiple procedural entities for integration testing.
    Contains: DISSOLUTION_PETITION, TEMPORARY_ORDER, GUARDIAN_AD_LITEM
    """
    return """
PROCEDURAL HISTORY

1. Petitioner filed a petition for dissolution on January 15, 2024.

2. The court entered temporary orders on February 1, 2024, establishing interim
   custody arrangements and support pendente lite.

3. Given the custody disputes, the court appointed a guardian ad litem on
   February 15, 2024 to investigate and make recommendations regarding the
   children's best interests.
"""


@pytest.fixture
def multi_entity_protection() -> str:
    """
    Document containing multiple child protection entities for integration testing.
    Contains: CHILD_ABUSE_REPORT, DEPENDENCY_ACTION, PROTECTIVE_CUSTODY
    """
    return """
CHILD PROTECTION PROCEEDINGS

1. On March 1, 2024, CPS report was filed alleging neglect and physical abuse.

2. On March 3, 2024, the State filed a dependency action in juvenile court.

3. The child was taken into protective custody on an emergency basis pending
   the shelter care hearing scheduled for March 5, 2024.
"""


# ============================================================================
# EXPECTED ENTITY COUNTS (FOR VALIDATION)
# ============================================================================

@pytest.fixture
def expected_entity_counts() -> Dict[str, int]:
    """
    Expected entity counts for each fixture.
    Used for validation in integration tests.
    """
    return {
        # Jurisdiction fixtures
        "uccjea_jurisdiction_text": {
            "HOME_STATE": 2,
            "EMERGENCY_JURISDICTION": 2,
            "EXCLUSIVE_CONTINUING_JURISDICTION": 2,
            "SIGNIFICANT_CONNECTION": 2,
            "FOREIGN_CUSTODY_ORDER": 2
        },
        # Procedural fixtures
        "dissolution_petition_text": {
            "DISSOLUTION_PETITION": 2,
            "TEMPORARY_ORDER": 3,
            "FINAL_DECREE": 3,
            "MODIFICATION_PETITION": 2,
            "GUARDIAN_AD_LITEM": 3
        },
        # Property fixtures
        "property_division_text": {
            "COMMUNITY_PROPERTY": 7,
            "SEPARATE_PROPERTY": 6
        },
        # Child protection fixtures
        "cps_report_text": {
            "CHILD_ABUSE_REPORT": 3,
            "DEPENDENCY_ACTION": 3,
            "PROTECTIVE_CUSTODY": 4
        }
    }


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

@pytest.fixture
def extraction_config() -> Dict:
    """
    Configuration for entity extraction tests.
    """
    return {
        "base_url": "http://localhost:8007",
        "extraction_mode": "ai",  # Use AI mode with vLLM Instruct (Port 8080)
        "timeout": 60,
        "confidence_threshold": 0.90,  # High confidence required for Tier 1
        "retry_attempts": 3,
        "retry_delay": 2.0
    }


@pytest.fixture
def tier1_entity_types() -> List[str]:
    """
    Complete list of 15 Tier 1 family law entity types.
    """
    return [
        # Jurisdiction (5)
        "HOME_STATE",
        "EMERGENCY_JURISDICTION",
        "EXCLUSIVE_CONTINUING_JURISDICTION",
        "SIGNIFICANT_CONNECTION",
        "FOREIGN_CUSTODY_ORDER",
        # Procedural (5)
        "DISSOLUTION_PETITION",
        "TEMPORARY_ORDER",
        "FINAL_DECREE",
        "MODIFICATION_PETITION",
        "GUARDIAN_AD_LITEM",
        # Property (2)
        "COMMUNITY_PROPERTY",
        "SEPARATE_PROPERTY",
        # Child Protection (3)
        "CHILD_ABUSE_REPORT",
        "DEPENDENCY_ACTION",
        "PROTECTIVE_CUSTODY"
    ]


@pytest.fixture
def performance_targets() -> Dict[str, float]:
    """
    Performance targets for Tier 1 patterns.
    Based on family_law.yaml performance_target specifications.
    """
    return {
        "max_processing_time_ms": 50,  # <50ms per document per user requirement
        "min_confidence": 0.90,  # ≥0.90 confidence for critical entities
        "min_accuracy": 0.95  # ≥95% extraction accuracy
    }
