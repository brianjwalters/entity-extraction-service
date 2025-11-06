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


# ============================================================================
# TIER 2 (PHASE 2) CONFIGURATION
# ============================================================================

@pytest.fixture
def extraction_config_regex() -> Dict:
    """
    Configuration for entity extraction tests using regex mode.
    Phase 2 uses regex for high-performance pattern matching.
    """
    return {
        "base_url": "http://localhost:8007",
        "extraction_mode": "regex",  # Use regex mode for Phase 2 patterns
        "timeout": 60,
        "confidence_threshold": 0.88,  # Slightly lower threshold for regex patterns
        "retry_attempts": 3,
        "retry_delay": 2.0
    }


@pytest.fixture
def tier2_entity_types() -> List[str]:
    """
    Complete list of 25 Tier 2 family law entity types (Phase 2).
    """
    return [
        # Procedural Documents Ext (4)
        "RESTRAINING_ORDER",
        "RELOCATION_NOTICE",
        "MAINTENANCE_ORDER",
        "PROPERTY_DISPOSITION",
        # Child Support Calculation (5)
        "BASIC_SUPPORT_OBLIGATION",
        "SUPPORT_DEVIATION",
        "RESIDENTIAL_CREDIT",
        "IMPUTED_INCOME",
        "INCOME_DEDUCTION_ORDER",
        # Support Enforcement (4)
        "WAGE_ASSIGNMENT_ORDER",
        "CONTEMPT_ACTION",
        "CHILD_SUPPORT_LIEN",
        "SUPPORT_ARREARS",
        # Jurisdiction Concepts Ext (3)
        "SIGNIFICANT_CONNECTION",
        "EXCLUSIVE_CONTINUING_JURISDICTION",
        "FOREIGN_CUSTODY_ORDER",
        # Parentage Proceedings (4)
        "PARENTAGE_ACTION",
        "PATERNITY_ACKNOWLEDGMENT",
        "GENETIC_TESTING_ORDER",
        "ADJUDICATION_OF_PARENTAGE",
        # Adoption Proceedings (4)
        "ADOPTION_PETITION",
        "RELINQUISHMENT_PETITION",
        "HOME_STUDY_REPORT",
        "OPEN_ADOPTION_AGREEMENT",
        # Child Protection Ext (1)
        "MANDATORY_REPORTER"
    ]


@pytest.fixture
def performance_targets_tier2() -> Dict[str, float]:
    """
    Performance targets for Tier 2 patterns.
    Based on Phase 2 optimization: 2.898ms avg execution, 0.929 confidence.
    """
    return {
        "max_processing_time_ms": 15,  # <15ms per pattern target
        "min_confidence": 0.88,  # ≥0.88 confidence for regex patterns
        "min_accuracy": 0.93  # ≥93% extraction accuracy
    }


# ============================================================================
# TIER 2 SIMPLE FIXTURES (25 FIXTURES - ONE PER ENTITY TYPE)
# ============================================================================

# Group 1: Procedural Documents Ext (4 fixtures)

@pytest.fixture
def restraining_order_simple() -> str:
    """Simple RESTRAINING_ORDER test case."""
    return "The court entered a restraining order preventing sale of the marital home during dissolution proceedings."


@pytest.fixture
def relocation_notice_simple() -> str:
    """Simple RELOCATION_NOTICE test case."""
    return "Mother filed a 60-day relocation notice under RCW 26.09.405 for intended move to California."


@pytest.fixture
def maintenance_order_simple() -> str:
    """Simple MAINTENANCE_ORDER test case."""
    return "Spousal maintenance of $2,500 per month awarded for duration of 36 months."


@pytest.fixture
def property_disposition_simple() -> str:
    """Simple PROPERTY_DISPOSITION test case."""
    return "The court ordered a just and equitable distribution of community property in a 60/40 split."


# Group 2: Child Support Calculation (5 fixtures)

@pytest.fixture
def basic_support_simple() -> str:
    """Simple BASIC_SUPPORT_OBLIGATION test case."""
    return "The basic support obligation is $1,245 per month according to the economic table."


@pytest.fixture
def support_deviation_simple() -> str:
    """Simple SUPPORT_DEVIATION test case."""
    return "A deviation from standard calculation is justified due to extraordinary medical expenses."


@pytest.fixture
def residential_credit_simple() -> str:
    """Simple RESIDENTIAL_CREDIT test case."""
    return "The non-custodial parent shall receive a residential credit of 35% for overnight parenting time."


@pytest.fixture
def imputed_income_simple() -> str:
    """Simple IMPUTED_INCOME test case."""
    return "Income is imputed at minimum wage due to voluntary unemployment without justification."


@pytest.fixture
def income_deduction_simple() -> str:
    """Simple INCOME_DEDUCTION_ORDER test case."""
    return "An income withholding order will be served on the employer for automatic deduction."


# Group 3: Support Enforcement (4 fixtures)

@pytest.fixture
def wage_assignment_simple() -> str:
    """Simple WAGE_ASSIGNMENT_ORDER test case."""
    return "Mandatory wage assignment ordered for all child support payments effective immediately."


@pytest.fixture
def contempt_action_simple() -> str:
    """Simple CONTEMPT_ACTION test case."""
    return "Show cause hearing scheduled for contempt action based on willful non-payment of support."


@pytest.fixture
def child_support_lien_simple() -> str:
    """Simple CHILD_SUPPORT_LIEN test case."""
    return "A child support lien of $35,000 was recorded against the real property for arrears."


@pytest.fixture
def support_arrears_simple() -> str:
    """Simple SUPPORT_ARREARS test case."""
    return "Support arrears totaling $45,000 have accumulated since 2019 plus statutory interest."


# Group 4: Jurisdiction Concepts Ext (3 fixtures)

@pytest.fixture
def significant_connection_ext_simple() -> str:
    """Simple SIGNIFICANT_CONNECTION test case."""
    return "The child has significant connections to Washington based on substantial evidence of care and education."


@pytest.fixture
def exclusive_continuing_ext_simple() -> str:
    """Simple EXCLUSIVE_CONTINUING_JURISDICTION test case."""
    return "Washington retains exclusive continuing jurisdiction over the custody matters under UCCJEA."


@pytest.fixture
def foreign_order_registration_simple() -> str:
    """Simple FOREIGN_CUSTODY_ORDER registration test case."""
    return "The Nevada custody order was registered in Washington pursuant to RCW 26.27.301."


# Group 5: Parentage Proceedings (4 fixtures)

@pytest.fixture
def parentage_action_simple() -> str:
    """Simple PARENTAGE_ACTION test case."""
    return "A parentage action was filed under RCW 26.26A.400 to establish legal father-child relationship."


@pytest.fixture
def paternity_acknowledgment_simple() -> str:
    """Simple PATERNITY_ACKNOWLEDGMENT test case."""
    return "Voluntary acknowledgment of parentage was executed at birth and filed with vital statistics."


@pytest.fixture
def genetic_testing_simple() -> str:
    """Simple GENETIC_TESTING_ORDER test case."""
    return "The court ordered genetic testing to determine paternity with 99.99% probability of match."


@pytest.fixture
def adjudication_parentage_simple() -> str:
    """Simple ADJUDICATION_OF_PARENTAGE test case."""
    return "Parentage was adjudicated by court order based on genetic test results establishing paternity."


# Group 6: Adoption Proceedings (4 fixtures)

@pytest.fixture
def adoption_petition_simple() -> str:
    """Simple ADOPTION_PETITION test case."""
    return "Stepparent adoption petition was filed with juvenile court under RCW 26.33.020."


@pytest.fixture
def relinquishment_petition_simple() -> str:
    """Simple RELINQUISHMENT_PETITION test case."""
    return "Voluntary relinquishment of parental rights was approved for adoption plan under RCW 26.33.080."


@pytest.fixture
def home_study_simple() -> str:
    """Simple HOME_STUDY_REPORT test case."""
    return "The preplacement home study was completed by licensed agency and recommends approval of adoption."


@pytest.fixture
def open_adoption_simple() -> str:
    """Simple OPEN_ADOPTION_AGREEMENT test case."""
    return "An open adoption agreement allows quarterly supervised visits with birth parents under RCW 26.33.295."


# Group 7: Child Protection Ext (1 fixture)

@pytest.fixture
def mandatory_reporter_simple() -> str:
    """Simple MANDATORY_REPORTER test case."""
    return "The teacher as mandatory reporter failed to report suspected abuse to CPS within 48 hours."


# ============================================================================
# TIER 2 PATTERN GROUP FIXTURES (7 FIXTURES)
# ============================================================================

@pytest.fixture
def procedural_documents_ext_text() -> str:
    """
    Document containing all procedural_documents_ext entities.
    Contains: RESTRAINING_ORDER, RELOCATION_NOTICE, MAINTENANCE_ORDER, PROPERTY_DISPOSITION
    """
    return """
SUPERIOR COURT OF WASHINGTON FOR KING COUNTY

In re the Marriage of Sarah and Michael Johnson

Case No. 24-3-56789-1 SEA

TEMPORARY RESTRAINING ORDER AND FINDINGS

I. RESTRAINING ORDER PROVISIONS

The court hereby enters a temporary restraining order preventing either party from:
(1) Disposing of, transferring, or encumbering community property
(2) Withdrawing funds from joint accounts exceeding $500
(3) Canceling insurance policies
(4) Relocating the minor children outside King County

This restraining order shall remain in effect pending final disposition.

II. RELOCATION NOTICE REQUIREMENT

Petitioner is advised that any intended relocation with the minor children requires
a 60-day relocation notice pursuant to RCW 26.09.405. The notice of intended relocation
must specify the new address and be served on the other parent. Failure to provide
proper relocation notice may result in sanctions.

III. SPOUSAL MAINTENANCE ORDER

The court awards temporary spousal maintenance in the amount of $2,500 per month
payable on the first of each month. Maintenance shall continue pendente lite until
entry of final decree. The maintenance order is based on the parties' financial
declarations and disparity in earning capacity.

IV. PROPERTY DISPOSITION

Upon final hearing, the court shall make a just and equitable distribution of all
community property accumulated during the marriage. The equitable distribution shall
consider the nature, extent, and duration of the marriage, each party's economic
circumstances, and all relevant factors under RCW 26.09.080.

DATED this 15th day of March, 2024.

_______________________________
Hon. Jennifer Martinez, Judge
"""


@pytest.fixture
def child_support_calculation_text() -> str:
    """
    Document containing all child_support_calculation entities.
    Contains: BASIC_SUPPORT_OBLIGATION, SUPPORT_DEVIATION, RESIDENTIAL_CREDIT,
             IMPUTED_INCOME, INCOME_DEDUCTION_ORDER
    """
    return """
CHILD SUPPORT WORKSHEET AND ORDER

I. BASIC SUPPORT OBLIGATION

The basic support obligation is calculated as follows:
- Combined monthly net income: $8,500
- Number of children: 2
- Economic table amount: $1,567 per month
- Basic support obligation per economic table: $1,567

II. SUPPORT DEVIATION

The court finds that a support deviation from standard calculation is warranted.
Deviation factors justifying departure from presumptive amount include:
- Child has extraordinary medical needs requiring $450/month therapy
- Travel costs for long-distance parenting time exceed $200/month
- Deviation amount: $250 reduction from standard calculation

III. RESIDENTIAL CREDIT

Father exercises overnight parenting time 142 nights per year (38.9%).
The residential credit for time with non-custodial parent is calculated:
- Percentage of residential time: 39%
- Credit applied to reduce support obligation by 35%
- Residential schedule credit: $547 monthly

IV. IMPUTED INCOME

Mother is voluntarily underemployed working part-time despite earning capacity.
Income shall be imputed based on full-time employment at earning capacity of $55,000
annually. Evidence establishes Mother capable of full-time work but chooses part-time
without adequate justification. Imputed income: $4,583 monthly.

V. INCOME WITHHOLDING ORDER

An income withholding order shall be served on Father's employer immediately.
The employer shall withhold $1,200 per month from wages and remit to Washington
State Support Registry. The income deduction order is mandatory under RCW 26.19.035
and cannot be waived by agreement of the parties.

ORDERED this 20th day of April, 2024.

_______________________________
Commissioner James Rodriguez
"""


@pytest.fixture
def support_enforcement_text() -> str:
    """
    Document containing all support_enforcement entities.
    Contains: WAGE_ASSIGNMENT_ORDER, CONTEMPT_ACTION, CHILD_SUPPORT_LIEN, SUPPORT_ARREARS
    """
    return """
DIVISION OF CHILD SUPPORT - ENFORCEMENT ACTION

Case Number: CS-2024-8765
Obligor: Michael Johnson
Obligee: Sarah Johnson

I. WAGE ASSIGNMENT ORDER

A mandatory wage assignment order has been issued pursuant to RCW 26.18.070.
The assignment of wages requires the employer to withhold $1,500 per month from
all wages, salary, and commissions. The wage garnishment order was served on
ABC Corporation on March 1, 2024. This mandatory wage assignment cannot be waived.

II. CONTEMPT ACTION INITIATED

Show cause hearing scheduled for April 15, 2024 for contempt of court. Obligor
has willfully failed to pay court-ordered child support for 8 consecutive months.
The contempt motion alleges willful violation of support order and seeks finding
of contempt. Penalties may include incarceration up to 6 months and attorney fees.

III. CHILD SUPPORT LIEN RECORDED

A child support lien in the amount of $35,000 was recorded against real property
at 123 Main Street, Seattle, WA 98101 on February 15, 2024. The support lien
secures payment of arrears and will remain on property until paid in full. The
lien on real property was perfected by filing with King County Auditor under
RCW 26.18.055.

IV. SUPPORT ARREARS STATEMENT

Current support arrears total $45,000 as of April 1, 2024. This back support
accumulated from January 2019 through March 2024. The delinquent support amount
includes:
- Unpaid monthly support: $42,000
- Statutory interest at 12% per annum: $3,000
- Total past-due support owed: $45,000

Payment plan available. Contact DCS for arrangements.
"""


@pytest.fixture
def jurisdiction_concepts_ext_text() -> str:
    """
    Document containing all jurisdiction_concepts_ext entities.
    Contains: SIGNIFICANT_CONNECTION, EXCLUSIVE_CONTINUING_JURISDICTION, FOREIGN_CUSTODY_ORDER
    """
    return """
DECLARATION RE: JURISDICTION UNDER UCCJEA

I, Maria Garcia, declare under penalty of perjury:

I. SIGNIFICANT CONNECTION JURISDICTION

Even if Washington is not the child's home state, this state has jurisdiction based
on significant connections to Washington. The child has lived in Washington for
18 months and has substantial evidence of connections including:
- Enrolled at Lincoln Elementary School in Seattle
- Receives ongoing medical care at Seattle Children's Hospital
- Participates in soccer league and piano lessons in Seattle
- Extended family (grandparents, aunts, uncles) reside in Washington
- Child's pediatrician, dentist, therapist all located in Washington

The child and one parent have significant connections to this state with substantial
evidence concerning the child's care, protection, training, and personal relationships.

II. EXCLUSIVE CONTINUING JURISDICTION RETAINED

Washington retains exclusive continuing jurisdiction over custody matters pursuant
to RCW 26.27.211. The original parenting plan was entered in King County Superior
Court in 2020. Washington continuing jurisdiction is maintained because:
- Both parents continue to reside in Washington
- Child has not permanently relocated from Washington
- Court that issued original order retains exclusive jurisdiction
- No other state has home state jurisdiction

The state of original jurisdiction retains authority to modify its orders.

III. FOREIGN CUSTODY ORDER REGISTRATION

In 2021, a California Superior Court custody order was issued granting Mother
primary custody. That California order was registered in Washington under RCW 26.27.301
on June 15, 2021. The foreign custody order from California is now enforceable
in Washington as if originally entered here. The out-of-state order registration
was properly completed with King County Superior Court.

Dated: March 20, 2024

_______________________________
Maria Garcia
"""


@pytest.fixture
def parentage_proceedings_text() -> str:
    """
    Document containing all parentage_proceedings entities.
    Contains: PARENTAGE_ACTION, PATERNITY_ACKNOWLEDGMENT, GENETIC_TESTING_ORDER,
             ADJUDICATION_OF_PARENTAGE
    """
    return """
KING COUNTY SUPERIOR COURT

State of Washington v. John Doe
Case No. 24-2-12345-7 SEA

FINDINGS AND ORDER RE: PARENTAGE

I. PARENTAGE ACTION BACKGROUND

This parentage action was filed on January 15, 2024 under RCW 26.26A.400 to establish
the legal parent-child relationship between alleged father John Doe and minor child
Emma Smith, born May 10, 2023. The action to establish parentage was initiated by
the State on behalf of Mother seeking establishment of paternity and child support.

II. PATERNITY ACKNOWLEDGMENT HISTORY

No voluntary acknowledgment of parentage was executed at the time of birth. Mother
states that alleged father refused to sign acknowledgment of parentage at the hospital.
Had a paternity affidavit been signed, it would have established legal parentage
without need for court proceedings.

III. GENETIC TESTING ORDERED

On February 1, 2024, the court ordered genetic testing pursuant to RCW 26.26A.310.
DNA testing was performed by Labcorp on February 15, 2024. The genetic test results
showed:
- Probability of paternity: 99.99%
- Combined paternity index: 2,847,592
- Genetic marker analysis confirms biological relationship

Based on court ordered testing, genetic evidence establishes John Doe as biological father.

IV. ADJUDICATION OF PARENTAGE

Based on genetic testing results and evidence presented, the court makes the following
findings and adjudication of parentage:

1. John Doe is the biological father of Emma Smith
2. Parentage is adjudicated and established by this order
3. John Doe's name shall be added to birth certificate
4. John Doe has all rights and responsibilities of legal parent
5. Child support obligation is established effective March 1, 2024

This order adjudicates parentage under RCW 26.26A.405 and establishes John Doe
as the legal father with full parental rights and obligations.

ORDERED this 15th day of March, 2024.

_______________________________
Hon. Patricia Wong
Superior Court Judge
"""


@pytest.fixture
def adoption_proceedings_text() -> str:
    """
    Document containing all adoption_proceedings entities.
    Contains: ADOPTION_PETITION, RELINQUISHMENT_PETITION, HOME_STUDY_REPORT,
             OPEN_ADOPTION_AGREEMENT
    """
    return """
KING COUNTY SUPERIOR COURT - JUVENILE DIVISION

In re the Adoption of Baby Girl Smith
Case No. 24-7-00123-4 SEA

ADOPTION DECREE AND FINDINGS

I. ADOPTION PETITION

An adoption petition was filed on January 10, 2024 by Jennifer and David Martinez
pursuant to RCW 26.33.020. The petition to adopt seeks termination of birth parents'
rights and establishment of petitioners as legal parents. The stepparent adoption
petition was properly verified and includes all required documentation.

II. RELINQUISHMENT OF PARENTAL RIGHTS

On December 15, 2023, birth mother executed a voluntary relinquishment of parental
rights before notary public. The relinquishment petition was approved by court on
January 5, 2024 after waiting period under RCW 26.33.080. Birth mother understood
the permanent and irrevocable nature of parental rights relinquishment. Birth father's
rights were previously terminated by separate order.

III. HOME STUDY REPORT

A preplacement home study was completed by ABC Family Services on November 20, 2023.
The home study report recommended approval of adoption placement and found:
- Adoptive parents financially and emotionally stable
- Home environment safe and appropriate for child
- Background checks cleared with no concerns
- References unanimously support adoption

The agency home study meets all requirements under RCW 26.33.180.

IV. OPEN ADOPTION AGREEMENT

The parties have agreed to an open adoption agreement pursuant to RCW 26.33.295
allowing post-adoption contact between birth mother and child. The agreed order
for ongoing contact includes:
- Four visits per year supervised by adoptive parents
- Exchange of photos and letters twice per year
- Birth mother may attend child's school events
- Contact may be modified by mutual agreement

This open adoption agreement preserves important connections while protecting
child's best interests.

V. ADOPTION DECREE

The court finds adoption is in the best interests of the child and ORDERS:
1. Adoption petition is GRANTED
2. Birth parents' rights terminated
3. Jennifer and David Martinez are legal parents
4. Child's name changed to Emma Rose Martinez
5. New birth certificate shall be issued

ORDERED this 1st day of March, 2024.

_______________________________
Hon. Lisa Chen
Superior Court Judge
"""


@pytest.fixture
def child_protection_ext_text() -> str:
    """
    Document containing child_protection_ext entity.
    Contains: MANDATORY_REPORTER
    """
    return """
KING COUNTY SUPERIOR COURT - JUVENILE DIVISION

State of Washington v. John Smith
Case No. 24-7-45678-9 SEA

FINDINGS RE: MANDATORY REPORTER VIOLATION

I. FACTUAL BACKGROUND

Defendant John Smith was employed as a teacher at Lincoln Elementary School.
On March 1, 2024, Mr. Smith observed a student with suspicious bruises on arms
and face consistent with physical abuse. The student told Mr. Smith that "Daddy
gets really mad and hits me."

II. MANDATORY REPORTER DUTY

Under RCW 26.44.030, teachers are mandatory reporters required to report suspected
child abuse or neglect immediately to CPS or law enforcement. The duty to report
arises when a mandatory reporter has reasonable cause to believe abuse occurred.
A teacher as mandatory reporter must report within 48 hours of first suspicion.

III. FAILURE TO REPORT

Despite clear indicators of abuse, Mr. Smith failed to report to CPS for 10 days.
This failure to report as mandatory reporter violated RCW 26.44.030. Mr. Smith
stated he "didn't want to get involved" and "thought the bruises might be from sports."

A healthcare provider must report immediately, not wait for confirmation. The
required to report standard is "reasonable cause to believe," not proof beyond
reasonable doubt.

IV. FINDINGS

The court finds:
1. John Smith was a mandatory reporter under RCW 26.44.030
2. Mr. Smith had reasonable cause to believe child abuse occurred
3. Mr. Smith willfully failed to fulfill duty to report suspected abuse
4. The delay in reporting placed the child at continued risk of harm

This violation of mandatory reporter obligations is subject to criminal penalties
under RCW 26.44.080.

ORDERED this 25th day of March, 2024.

_______________________________
Hon. Michael Torres
Superior Court Judge
"""


# ============================================================================
# TIER 2 INTEGRATION TEST FIXTURES (5 FIXTURES)
# ============================================================================

@pytest.fixture
def support_calculation_document() -> str:
    """
    Document for support calculation integration test.
    Contains: BASIC_SUPPORT_OBLIGATION, SUPPORT_DEVIATION, RESIDENTIAL_CREDIT,
             IMPUTED_INCOME, INCOME_DEDUCTION_ORDER
    """
    return """
CHILD SUPPORT ORDER

The basic support obligation is $1,245 per month per the economic table for combined
income of $7,500. A deviation from the standard calculation is justified due to
extraordinary medical expenses of $450 monthly for child's therapy. Father shall
receive a residential credit of 35% for overnight parenting time (140 nights per year).

Mother is voluntarily underemployed. Income is imputed at her earning capacity of
$45,000 annually based on work history and available positions. An income withholding
order shall be served on Father's employer requiring automatic wage deduction of
$1,100 per month.
"""


@pytest.fixture
def enforcement_action_document() -> str:
    """
    Document for enforcement action integration test.
    Contains: WAGE_ASSIGNMENT_ORDER, CONTEMPT_ACTION, CHILD_SUPPORT_LIEN, SUPPORT_ARREARS
    """
    return """
SUPPORT ENFORCEMENT ACTION

A mandatory wage assignment was ordered under RCW 26.18.070 requiring employer
to withhold support from wages. Show cause hearing scheduled for contempt action
due to non-payment of child support for 6 months. A child support lien in the
amount of $28,000 was recorded against property at 456 Oak Street. Support arrears
total $35,000 including back support from 2020-2024 plus statutory interest.
"""


@pytest.fixture
def jurisdiction_motion_document() -> str:
    """
    Document for jurisdiction motion integration test.
    Contains: SIGNIFICANT_CONNECTION, EXCLUSIVE_CONTINUING_JURISDICTION, FOREIGN_CUSTODY_ORDER
    """
    return """
JURISDICTION DECLARATION

The child has significant connections to Washington with substantial evidence of
care, education, and medical treatment in this state. Washington retains exclusive
continuing jurisdiction over custody matters under the original 2020 parenting plan.
A Nevada custody order was registered in Washington on May 1, 2023 pursuant to RCW 26.27.301.
"""


@pytest.fixture
def parentage_petition_document() -> str:
    """
    Document for parentage petition integration test.
    Contains: PARENTAGE_ACTION, PATERNITY_ACKNOWLEDGMENT, GENETIC_TESTING_ORDER,
             ADJUDICATION_OF_PARENTAGE
    """
    return """
PARENTAGE PROCEEDINGS

A parentage action was filed under RCW 26.26A.400 to establish father-child relationship.
No voluntary acknowledgment of parentage was executed at birth. The court ordered
genetic testing which showed 99.99% probability of paternity. Parentage was adjudicated
by court order establishing legal parent-child relationship and support obligations.
"""


@pytest.fixture
def adoption_case_document() -> str:
    """
    Document for adoption case integration test.
    Contains: ADOPTION_PETITION, RELINQUISHMENT_PETITION, HOME_STUDY_REPORT,
             OPEN_ADOPTION_AGREEMENT
    """
    return """
ADOPTION PROCEEDINGS

The adoption petition was filed by stepparent under RCW 26.33.020 seeking to adopt
minor child. Birth father executed voluntary relinquishment of parental rights which
was approved by court. The preplacement home study was completed by licensed agency
and recommends approval. An open adoption agreement allows quarterly visits with
birth mother under RCW 26.33.295.
"""


@pytest.fixture
def phase2_full_document() -> str:
    """
    Comprehensive document containing all 25 Phase 2 entity types for E2E testing.
    """
    return """
SUPERIOR COURT OF WASHINGTON FOR KING COUNTY

In re the Marriage of Sarah Martinez and Michael Johnson

Case No. 24-3-98765-4 SEA

COMPREHENSIVE DISSOLUTION AND SUPPORT ORDER

I. RESTRAINING ORDER AND PROCEDURAL MATTERS

The court enters a temporary restraining order preventing disposal of community
property pending final dissolution. Mother filed a 60-day relocation notice for
intended move to California under RCW 26.09.405. Spousal maintenance of $2,200
monthly is awarded for 24 months. A just and equitable distribution of property
shall be made considering all factors under RCW 26.09.080.

II. CHILD SUPPORT CALCULATION

The basic support obligation is $1,567 per month according to the economic table.
A deviation from standard calculation is warranted due to special needs totaling
$380 monthly. Father receives a residential credit of 38% for 138 overnight visits
annually. Mother's income is imputed at $50,000 based on earning capacity despite
voluntary underemployment. An income withholding order shall be served on Father's
employer immediately under RCW 26.19.035.

III. SUPPORT ENFORCEMENT

Mandatory wage assignment ordered under RCW 26.18.070 for all support obligations.
Show cause hearing scheduled for contempt action for non-payment of six months support.
A child support lien of $32,000 is recorded against property at 789 Pine Street.
Support arrears total $38,000 accumulated from January 2021 through present including
delinquent support and interest.

IV. JURISDICTION

The child has significant connections to Washington with substantial evidence of
care, schooling, and medical treatment. Washington retains exclusive continuing
jurisdiction under the 2021 parenting plan per RCW 26.27.211. A California custody
order was registered in Washington on March 15, 2023 under RCW 26.27.301.

V. PARENTAGE ESTABLISHMENT

Before marriage, a parentage action was filed to establish John Doe as legal father.
No voluntary acknowledgment of parentage was signed at hospital. The court ordered
genetic testing showing 99.99% probability. Parentage was adjudicated by order dated
February 10, 2020 establishing legal parent-child relationship.

VI. ADOPTION HISTORY

Mother's current spouse filed stepparent adoption petition under RCW 26.33.020 to
adopt child from prior relationship. Birth father executed voluntary relinquishment
of parental rights approved January 5, 2024. The preplacement home study by ABC
Services recommends approval. An open adoption agreement permits semi-annual visits
with birth father per RCW 26.33.295.

VII. CHILD PROTECTION CONCERNS

School teacher as mandatory reporter failed to report suspected abuse observed on
March 1, 2024. Under RCW 26.44.030, teachers are mandatory reporters required to
report immediately. The duty to report suspected abuse cannot be delegated or ignored.

ORDERED this 15th day of April, 2024.

_______________________________
Hon. Jennifer Martinez, Judge
Superior Court of Washington
"""
