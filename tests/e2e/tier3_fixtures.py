"""
Pytest fixtures for Tier 3 (Phase 3) Family Law E2E Tests.

This file provides realistic family law document fixtures for testing
the 43 new Tier 3 patterns added in Phase 3 family law expansion.

Pattern Groups (9 groups, 43 patterns):
1. dissolution_separation_ext (6 entities): LEGAL_SEPARATION, INVALIDITY_DECLARATION,
   SEPARATION_CONTRACT, RESIDENTIAL_TIME, RETIREMENT_BENEFIT_DIVISION, SAFE_EXCHANGE
2. child_support_calculation_ext (6 entities): POSTSECONDARY_SUPPORT,
   TAX_EXEMPTION_ALLOCATION, STANDARD_OF_LIVING, EXTRAORDINARY_EXPENSE,
   DAYCARE_EXPENSE, SUPPORT_WORKSHEET
3. jurisdiction_concepts_detail (5 entities): INCONVENIENT_FORUM, JURISDICTION_DECLINED,
   REGISTRATION_OF_ORDER, UCCJEA_NOTICE, TEMPORARY_EMERGENCY_CUSTODY
4. parentage_proceedings_ext (6 entities): PRESUMPTION_OF_PARENTAGE,
   RESCISSION_OF_ACKNOWLEDGMENT, CHALLENGE_TO_PARENTAGE, ASSISTED_REPRODUCTION,
   SURROGACY_AGREEMENT, GENETIC_TEST_RESULTS
5. adoption_proceedings_ext (6 entities): PREPLACEMENT_REPORT, SIBLING_CONTACT_ORDER,
   SEALED_ADOPTION_RECORD, STEPPARENT_ADOPTION, AGENCY_PLACEMENT, INDEPENDENT_ADOPTION
6. child_protection_detail (6 entities): FAMILY_ASSESSMENT_RESPONSE,
   MULTIDISCIPLINARY_TEAM, OUT_OF_HOME_PLACEMENT, REUNIFICATION_SERVICES,
   SAFETY_PLAN, CHILD_FORENSIC_INTERVIEW
7. dissolution_procedures_additional (2 entities): MANDATORY_PARENTING_SEMINAR,
   ATTORNEY_FEES_AWARD
8. support_modification_review (3 entities): SUPPORT_MODIFICATION_REQUEST,
   SUBSTANTIAL_CHANGE_OF_CIRCUMSTANCES, AUTOMATIC_SUPPORT_ADJUSTMENT
9. parenting_plan_dispute_resolution (3 entities): PARENTING_COORDINATOR,
   MEDIATION_REQUIREMENT, COUNSELING_REQUIREMENT
"""

import pytest
from typing import Dict, List


# ============================================================================
# GROUP 1: DISSOLUTION & SEPARATION EXTENSIONS (6 FIXTURES)
# ============================================================================

@pytest.fixture
def legal_separation_simple() -> str:
    """Simple LEGAL_SEPARATION test case."""
    return "The court entered a decree of legal separation on July 15, 2024."


@pytest.fixture
def invalidity_declaration_simple() -> str:
    """Simple INVALIDITY_DECLARATION test case."""
    return "Petition for declaration of invalidity of marriage was granted due to fraud."


@pytest.fixture
def separation_contract_simple() -> str:
    """Simple SEPARATION_CONTRACT test case."""
    return "The parties executed a separation contract dividing all community assets."


@pytest.fixture
def residential_time_simple() -> str:
    """Simple RESIDENTIAL_TIME test case."""
    return "The child shall have substantially equal residential time with both parents."


@pytest.fixture
def retirement_benefit_division_simple() -> str:
    """Simple RETIREMENT_BENEFIT_DIVISION test case."""
    return "The 401(k) retirement benefits shall be divided 50/50 pursuant to QDRO."


@pytest.fixture
def safe_exchange_simple() -> str:
    """Simple SAFE_EXCHANGE test case."""
    return "Child exchanges shall occur at the designated safe exchange center."


@pytest.fixture
def dissolution_separation_document() -> str:
    """
    Comprehensive dissolution/separation document with all 6 dissolution_separation_ext entities.
    Tests: LEGAL_SEPARATION, INVALIDITY_DECLARATION, SEPARATION_CONTRACT,
           RESIDENTIAL_TIME, RETIREMENT_BENEFIT_DIVISION, SAFE_EXCHANGE
    """
    return """
SUPERIOR COURT OF WASHINGTON FOR SPOKANE COUNTY

In re the Marriage of Thompson

Case No. 24-3-45678-1 SPO

ORDER ON LEGAL SEPARATION AND PROPERTY DIVISION

I. LEGAL SEPARATION DECREE

The court GRANTS the petition for legal separation filed by Petitioner on March 1, 2024.
A decree of legal separation is entered rather than dissolution, allowing the parties to
maintain marital status for religious and insurance reasons under RCW 26.09.030. This
legal separation entered by the court permits the parties to live apart with defined
property rights and parenting arrangements.

Respondent's alternative claim for declaration of invalidity of marriage is DENIED.
The marriage is valid under Washington law and does not meet the statutory grounds for
invalidity of marriage under RCW 26.09.040. No fraud, duress, or incapacity exists to
warrant an annulment or void marriage declaration.

II. SEPARATION CONTRACT APPROVED

The parties' separation contract dated February 15, 2024 is hereby approved and
incorporated into this order. The property settlement agreement divides all community
and separate property equitably and is fair under RCW 26.09.070. The marital settlement
agreement addresses all financial matters and the separation agreement is hereby adopted
by the court.

III. PARENTING PLAN - RESIDENTIAL TIME

The child, Emma Thompson (DOB: 5/10/2018), shall have substantially equal residential
time with both parents per the attached parenting plan. The residential schedule
alternates weekly with exchanges on Sundays at 5:00 PM. Mother shall have majority
of residential time during the school year (60%), while Father has increased residential
time during summer months. The residential time allocation supports the child's best
interests under RCW 26.09.002.

IV. RETIREMENT BENEFIT DIVISION

Husband's 401(k) retirement account valued at $287,000 shall be divided equally between
the parties. A qualified domestic relations order (QDRO) shall be entered to effectuate
the retirement benefit division per RCW 26.09.138. Wife's IRA of $143,000 shall remain
her separate property. The pension division requires QDRO approval by plan administrator.

V. SAFE CHILD EXCHANGES

Due to past conflict between the parties, all child exchanges shall occur at the
designated safe exchange center located at Spokane Police Department East Precinct.
Supervised exchanges at this neutral location are required to ensure child safety.
Parents shall use safe exchange facilities for all transitions. Exchanges in public
place at police station parking lot are mandatory until further order.

ORDERED this 15th day of November, 2024.

_______________________________
Hon. Patricia Williams, Judge
"""


# ============================================================================
# GROUP 2: CHILD SUPPORT CALCULATION EXTENSIONS (6 FIXTURES)
# ============================================================================

@pytest.fixture
def postsecondary_support_simple() -> str:
    """Simple POSTSECONDARY_SUPPORT test case."""
    return "Father shall contribute $15,000 annually toward postsecondary educational support."


@pytest.fixture
def tax_exemption_allocation_simple() -> str:
    """Simple TAX_EXEMPTION_ALLOCATION test case."""
    return "Mother is awarded the tax exemption for claiming child as dependent in odd years."


@pytest.fixture
def standard_of_living_simple() -> str:
    """Simple STANDARD_OF_LIVING test case."""
    return "The child was accustomed to an upper-middle-class standard of living during marriage."


@pytest.fixture
def extraordinary_expense_simple() -> str:
    """Simple EXTRAORDINARY_EXPENSE test case."""
    return "Child's orthodontic costs of $6,000 constitute an extraordinary expense."


@pytest.fixture
def daycare_expense_simple() -> str:
    """Simple DAYCARE_EXPENSE test case."""
    return "Work-related daycare costs of $1,200 per month are included in the support calculation."


@pytest.fixture
def support_worksheet_simple() -> str:
    """Simple SUPPORT_WORKSHEET test case."""
    return "The completed child support worksheet shows a basic obligation of $1,567 monthly."


@pytest.fixture
def child_support_extended_document() -> str:
    """
    Comprehensive child support document with all 6 child_support_calculation_ext entities.
    Tests: POSTSECONDARY_SUPPORT, TAX_EXEMPTION_ALLOCATION, STANDARD_OF_LIVING,
           EXTRAORDINARY_EXPENSE, DAYCARE_EXPENSE, SUPPORT_WORKSHEET
    """
    return """
CHILD SUPPORT ORDER - EXTENDED CALCULATION

I. BASIC SUPPORT WORKSHEET

The child support worksheet (WS-01 form) has been completed by both parties showing
combined monthly net income of $12,450. The support calculation worksheet demonstrates
a basic support obligation of $2,134 per month according to the economic table worksheet.
The completed worksheet is filed as Exhibit A and addresses all components under RCW 26.19.050.

II. POSTSECONDARY EDUCATIONAL SUPPORT

Father shall contribute to postsecondary educational support for college expenses when
the children reach age 18. University costs including tuition, room and board, books,
and fees shall be shared 60% Father and 40% Mother up to in-state public university
rates. Tuition support contribution limited to $18,000 per child annually. Educational
expenses beyond high school are addressed per RCW 26.19.090.

III. TAX EXEMPTION ALLOCATION

Mother is awarded the tax exemption for claiming both children as dependents for IRS
purposes in even-numbered years. Father may claim the children for dependency exemption
in odd-numbered years. Parents shall alternate tax exemption annually and execute
IRS Form 8332 as required. The tax exemption allocation is subject to compliance with
support obligations per RCW 26.19.100.

IV. STANDARD OF LIVING CONSIDERATION

The children enjoyed a comfortable upper-middle-class standard of living during the
intact marriage. Both parents were high earners and the family lifestyle included
private school, international travel, and extracurricular activities. The children
were accustomed to economic circumstances that provided enrichment opportunities.
To maintain the standard of living the children enjoyed during marriage, support is
set above the standard calculation per RCW 26.19.001.

V. EXTRAORDINARY EXPENSES

Child Lucas has special needs requiring weekly occupational therapy at $160 per session.
These extraordinary medical expenses exceed insurance coverage and shall be shared equally.
Daughter Sophia requires orthodontic treatment costing $7,200 which is an extraordinary
expense to be split 50/50. Uninsured medical costs over $250 annually are extraordinary
expenses. Lucas' tutoring expenses of $300 monthly constitute extraordinary costs due
to learning disability.

VI. WORK-RELATED DAYCARE

Mother incurs work-related daycare costs of $1,450 per month for after-school care
while working full-time. These daycare expenses for employment purposes are necessary
for Mother's job as required under RCW 26.19.080. Father's child care while working
totals $180 monthly for summer camps. Work-related child care costs are included in
the deviation calculation.

ORDERED: November 5, 2024
"""


# ============================================================================
# GROUP 3: JURISDICTION CONCEPTS - DETAILED UCCJEA (5 FIXTURES)
# ============================================================================

@pytest.fixture
def inconvenient_forum_simple() -> str:
    """Simple INCONVENIENT_FORUM test case."""
    return "The court declines jurisdiction as inconvenient forum because Oregon is more appropriate."


@pytest.fixture
def jurisdiction_declined_simple() -> str:
    """Simple JURISDICTION_DECLINED test case."""
    return "Jurisdiction declined due to unjustifiable conduct in wrongfully removing the child."


@pytest.fixture
def registration_of_order_simple() -> str:
    """Simple REGISTRATION_OF_ORDER test case."""
    return "California custody order was registered in Washington for enforcement purposes."


@pytest.fixture
def uccjea_notice_simple() -> str:
    """Simple UCCJEA_NOTICE test case."""
    return "Notice to persons outside state was properly served per UCCJEA requirements."


@pytest.fixture
def temporary_emergency_custody_simple() -> str:
    """Simple TEMPORARY_EMERGENCY_CUSTODY test case."""
    return "Temporary emergency custody granted due to immediate danger to the child."


@pytest.fixture
def jurisdiction_detail_document() -> str:
    """
    Comprehensive jurisdiction document with all 5 jurisdiction_concepts_detail entities.
    Tests: INCONVENIENT_FORUM, JURISDICTION_DECLINED, REGISTRATION_OF_ORDER,
           UCCJEA_NOTICE, TEMPORARY_EMERGENCY_CUSTODY
    """
    return """
UCCJEA JURISDICTION ANALYSIS AND RULINGS

I. FORUM NON CONVENIENS MOTION

Father's motion to decline Washington jurisdiction on grounds of forum non conveniens
is GRANTED. Although Washington has subject matter jurisdiction, the court finds that
California is a more appropriate forum for this custody matter under RCW 26.27.261.
The child has resided in California for 14 months, all witnesses are in California,
and the inconvenient forum doctrine supports declining jurisdiction. Oregon would also
be a more appropriate forum than Washington given distances and convenience. The court
declines jurisdiction on convenience grounds and stays the Washington proceedings.

II. JURISDICTION DECLINED FOR UNJUSTIFIABLE CONDUCT

Mother's petition is DISMISSED. Jurisdiction is declined pursuant to RCW 26.27.271
because Mother engaged in unjustifiable conduct by wrongfully removing the child from
Texas in violation of that state's custody order. The court declines to exercise
jurisdiction when a party engaged in misconduct to acquire Washington jurisdiction.
Jurisdiction refused based on wrongful removal and forum shopping. The child should be
returned to Texas, which declined jurisdiction under UCCJEA section 271.

III. REGISTRATION OF FOREIGN CUSTODY ORDER

The Nevada District Court custody order dated May 15, 2022 (Case No. D-22-567890-D)
is hereby REGISTERED in Washington pursuant to RCW 26.27.441. Registration of this
custody order allows enforcement in Washington. The foreign order from Nevada registered
with King County Superior Court is enforceable as a Washington order. This order
registration completes the UCCJEA registration process. The out-of-state order is now
registered for modification and enforcement purposes.

IV. UCCJEA NOTICE TO OUT-OF-STATE PARTIES

Petitioner has served proper notice to persons outside state in compliance with
RCW 26.27.241. The biological father in Idaho received UCCJEA notice by certified
mail on September 1, 2024. Service outside state was accomplished under UCCJEA
requirements for jurisdictional notice. Notice under UCCJEA was also provided to
maternal grandmother in Arizona and paternal uncle in Montana. All interested parties
received jurisdictional notice per UCCJEA section 241.

V. TEMPORARY EMERGENCY JURISDICTION

The court exercises temporary emergency jurisdiction under RCW 26.27.231 due to
credible evidence of immediate danger to the child. Temporary emergency custody is
GRANTED to maternal grandmother pending full evidentiary hearing. The child is in
imminent risk of abuse if returned to parents. Emergency temporary order necessary
to protect child welfare. Temporary custody pending jurisdictional determination in
home state of Oregon. Ex parte temporary emergency custody entered based on sworn
declaration of harm.

ORDERED: November 5, 2024
"""


# ============================================================================
# GROUP 4: PARENTAGE PROCEEDINGS EXTENSIONS (6 FIXTURES)
# ============================================================================

@pytest.fixture
def presumption_of_parentage_simple() -> str:
    """Simple PRESUMPTION_OF_PARENTAGE test case."""
    return "Husband is the presumed father under the marital presumption of parentage."


@pytest.fixture
def rescission_of_acknowledgment_simple() -> str:
    """Simple RESCISSION_OF_ACKNOWLEDGMENT test case."""
    return "Father filed rescission of acknowledgment within the 60-day statutory period."


@pytest.fixture
def challenge_to_parentage_simple() -> str:
    """Simple CHALLENGE_TO_PARENTAGE test case."""
    return "Mother filed a challenge to presumed parentage based on genetic testing results."


@pytest.fixture
def assisted_reproduction_simple() -> str:
    """Simple ASSISTED_REPRODUCTION test case."""
    return "The child was conceived through in vitro fertilization using donor sperm."


@pytest.fixture
def surrogacy_agreement_simple() -> str:
    """Simple SURROGACY_AGREEMENT test case."""
    return "The court validated the surrogacy agreement between intended parents and gestational carrier."


@pytest.fixture
def genetic_test_results_simple() -> str:
    """Simple GENETIC_TEST_RESULTS test case."""
    return "DNA test results show 99.97% probability of paternity establishing biological father."


@pytest.fixture
def parentage_extended_document() -> str:
    """
    Comprehensive parentage document with all 6 parentage_proceedings_ext entities.
    Tests: PRESUMPTION_OF_PARENTAGE, RESCISSION_OF_ACKNOWLEDGMENT, CHALLENGE_TO_PARENTAGE,
           ASSISTED_REPRODUCTION, SURROGACY_AGREEMENT, GENETIC_TEST_RESULTS
    """
    return """
PARENTAGE PROCEEDINGS - COMPLEX DETERMINATION

I. PRESUMPTION OF PARENTAGE

John Smith is the presumed parent under RCW 26.26A.115 based on the marital presumption.
The child was born during the marriage on June 15, 2023, creating a presumption of
parentage that John is the legal father. The presumed father status applies automatically.
However, this marital presumption is rebuttable upon clear and convincing evidence.
Jane Smith cohabited with John when child was conceived, creating presumptive parent
status under alternative grounds.

II. CHALLENGE TO PARENTAGE

Jane Smith filed a challenge to paternity within two years as permitted under RCW 26.26A.240.
The challenge to presumed parentage alleges that John is not the biological father.
Mother contests the parentage determination established by marital presumption. This
challenge to parentage is based on DNA evidence showing another man is biological father.
Father disputes parentage of child born during marriage and seeks genetic testing.

III. GENETIC TEST RESULTS

Court-ordered genetic testing was performed at LabCorp on August 15, 2024. The DNA test
results show 99.98% probability of paternity for Michael Johnson. Genetic test results
establish that Michael is the biological father and John Smith is excluded. The paternity
index is 12,456:1 strongly indicating biological relationship. These genetic test results
confirm Michael's parentage claim with virtual certainty exceeding 99.9% probability.

IV. RESCISSION OF ACKNOWLEDGMENT

John Smith filed rescission of acknowledgment on July 10, 2024, within the 60-day
rescission period under RCW 26.26A.235. He seeks to rescind the acknowledgment of
paternity signed at the hospital. The 60-day rescission right allows withdrawal during
the statutory window. His motion to revoke acknowledgment was timely filed. The
rescission of acknowledgment will be granted based on genetic testing disproving paternity.

V. ASSISTED REPRODUCTION WITH DONOR

The parties' second child was conceived via assisted reproduction under RCW 26.26A.600.
The assisted reproduction agreement signed pre-conception established both parties as
legal parents despite using donor sperm. In vitro fertilization was performed at
Seattle Reproductive Medicine in March 2024. The IVF procedure involved anonymous
donor genetic material. Artificial insemination agreement confirms Jane and Michael
as intended legal parents. Parentage established through assisted reproduction contract.

VI. SURROGACY AGREEMENT

For the parties' third child, a court-validated surrogacy agreement was executed under
RCW 26.26A.705 with gestational carrier Sarah Williams. The gestational surrogacy
arrangement was pre-approved by court order. Jane and Michael are intended parents
under the surrogacy contract. The surrogate mother is the gestational carrier only,
with no parental rights. Gestational carrier agreement approved pre-birth establishing
Jane and Michael as legal parents upon delivery.

ORDERED: November 5, 2024
"""


# ============================================================================
# GROUP 5: ADOPTION PROCEEDINGS EXTENSIONS (6 FIXTURES)
# ============================================================================

@pytest.fixture
def preplacement_report_simple() -> str:
    """Simple PREPLACEMENT_REPORT test case."""
    return "The preplacement report recommends approval of the adoptive family placement."


@pytest.fixture
def sibling_contact_order_simple() -> str:
    """Simple SIBLING_CONTACT_ORDER test case."""
    return "Order entered maintaining sibling contact through quarterly visits post-adoption."


@pytest.fixture
def sealed_adoption_record_simple() -> str:
    """Simple SEALED_ADOPTION_RECORD test case."""
    return "Adoption records shall be sealed by court order to protect confidentiality."


@pytest.fixture
def stepparent_adoption_simple() -> str:
    """Simple STEPPARENT_ADOPTION test case."""
    return "Stepparent adoption petition filed by mother's current husband."


@pytest.fixture
def agency_placement_simple() -> str:
    """Simple AGENCY_PLACEMENT test case."""
    return "The child was placed by licensed adoption agency Catholic Community Services."


@pytest.fixture
def independent_adoption_simple() -> str:
    """Simple INDEPENDENT_ADOPTION test case."""
    return "This is an independent adoption without agency involvement or facilitation."


@pytest.fixture
def adoption_extended_document() -> str:
    """
    Comprehensive adoption document with all 6 adoption_proceedings_ext entities.
    Tests: PREPLACEMENT_REPORT, SIBLING_CONTACT_ORDER, SEALED_ADOPTION_RECORD,
           STEPPARENT_ADOPTION, AGENCY_PLACEMENT, INDEPENDENT_ADOPTION
    """
    return """
ADOPTION DECREE - COMPREHENSIVE PROCEEDINGS

I. AGENCY PLACEMENT VS. INDEPENDENT ADOPTION

This matter involves competing adoption proceedings. The first petition is an independent
adoption without agency involvement filed by birth mother's selected adoptive family.
The private adoption was arranged directly between birth mother and adoptive parents.
This non-agency adoption requires judicial approval and home study per RCW 26.33.020.
The adoption without agency facilitation proceeded as a direct placement case.

Subsequently, a second petition for agency placement was filed after the child was
placed by licensed adoption agency Adoption Advocates International. The licensed
agency facilitated a separate placement under RCW 26.33.020. Child placing agency
completed its own assessment and identified alternative adoptive family.

II. STEPPARENT ADOPTION PROCEEDINGS

Robert Martinez filed a stepparent adoption petition to adopt his wife Maria's biological
son from prior relationship under RCW 26.33.140. This step-parent adoption simplifies
the process as Robert has lived with the child for four years. Adoption by stepparent
requires consent of custodial mother and termination of non-custodial father's rights.
The stepparent adoption creates a permanent parent-child relationship with Maria's spouse.

III. PREPLACEMENT ASSESSMENT

The court received a favorable preplacement report from social worker dated September 15,
2024. The home study report assesses the Martinez family as suitable adoptive parents.
The adoptive family assessment included interviews, background checks, and home visits.
This suitability report recommends placement with this family. The preplacement study
concluded that the Martinez home provides a stable, loving environment per RCW 26.33.190.

IV. SIBLING CONTACT POST-ADOPTION

The decree shall include a sibling contact order under RCW 26.33.420 to maintain the
relationship between adopted child and biological sibling remaining with birth family.
The siblings shall have in-person sibling visitation twice annually in June and December.
Contact with siblings is maintained through video calls monthly. The order maintaining
sibling contact preserves the children's bond. Sibling communication via letters and
photos is encouraged between visits.

V. SEALED ADOPTION RECORDS

Upon finalization, the adoption file shall be sealed by court order per RCW 26.33.330.
The sealed adoption record protects privacy of all parties. Adoption records sealed
upon entry of this decree. Access to the confidential adoption file requires court
order for good cause shown. The sealed record includes original birth certificate,
relinquishment documents, and agency reports.

VI. FINALIZATION

The adoption is GRANTED. The stepparent adoption is finalized effective immediately.

ORDERED: November 5, 2024
"""


# ============================================================================
# GROUP 6: CHILD PROTECTION DETAIL (6 FIXTURES)
# ============================================================================

@pytest.fixture
def family_assessment_response_simple() -> str:
    """Simple FAMILY_ASSESSMENT_RESPONSE test case."""
    return "CPS chose the FAR pathway for this lower-risk investigation instead of traditional approach."


@pytest.fixture
def multidisciplinary_team_simple() -> str:
    """Simple MULTIDISCIPLINARY_TEAM test case."""
    return "The multidisciplinary team review included CPS, law enforcement, and medical professionals."


@pytest.fixture
def out_of_home_placement_simple() -> str:
    """Simple OUT_OF_HOME_PLACEMENT test case."""
    return "Emergency out-of-home placement with maternal aunt ordered pending dependency hearing."


@pytest.fixture
def reunification_services_simple() -> str:
    """Simple REUNIFICATION_SERVICES test case."""
    return "Mother shall participate in reunification services including parenting classes and therapy."


@pytest.fixture
def safety_plan_simple() -> str:
    """Simple SAFETY_PLAN test case."""
    return "An in-home safety plan was implemented with daily supervision by grandmother."


@pytest.fixture
def child_forensic_interview_simple() -> str:
    """Simple CHILD_FORENSIC_INTERVIEW test case."""
    return "A forensic interview was conducted at the Children's Advocacy Center on October 15th."


@pytest.fixture
def child_protection_detail_document() -> str:
    """
    Comprehensive child protection document with all 6 child_protection_detail entities.
    Tests: FAMILY_ASSESSMENT_RESPONSE, MULTIDISCIPLINARY_TEAM, OUT_OF_HOME_PLACEMENT,
           REUNIFICATION_SERVICES, SAFETY_PLAN, CHILD_FORENSIC_INTERVIEW
    """
    return """
CHILD PROTECTIVE SERVICES INVESTIGATION FINDINGS

I. INVESTIGATION METHODOLOGY

CPS received a report on October 1, 2024 alleging neglect of two minor children.
After intake screening, the assigned social worker chose the family assessment response
(FAR) pathway under RCW 26.44.260 rather than traditional investigation. The FAR
investigation approach is used for lower-risk allegations without imminent safety
threats. This assessment track focuses on engaging the family and providing services.
The family assessment response emphasizes family strengths and voluntary services
rather than punitive measures.

II. MULTIDISCIPLINARY TEAM REVIEW

Due to concerns about possible sexual abuse, a multidisciplinary team (MDT) convened
on October 3, 2024 per RCW 26.44.180. The MDT review included representatives from
CPS, Spokane Police Department, Spokane Regional Health District, and Sacred Heart
Medical Center. The multi-disciplinary team approach ensures coordinated investigation
of serious allegations. Team members reviewed medical evidence and interviewed witnesses.
This coordinated investigation by MDT prevents duplicative interviews and ensures
comprehensive assessment.

III. FORENSIC INTERVIEW

On October 5, 2024, an trained forensic interviewer conducted a child forensic interview
with the 8-year-old victim at Spokane's Children's Advocacy Center (CAC). The CAC
interview utilized evidence-based protocols to obtain the child's statement in a
non-leading manner. The forensic interview was video recorded and observed by detectives.
Child gave detailed account during forensic interview regarding alleged abuse by stepfather.
Forensic interviewer's report will be provided to prosecutor.

IV. EMERGENCY OUT-OF-HOME PLACEMENT

Based on the disclosures made during forensic interview and unsafe home conditions,
CPS obtained an emergency out-of-home placement order on October 5, 2024. Both children
were placed in foster care temporarily under RCW 26.44.240. After kinship study, placement
was transferred to maternal grandmother as kinship placement. The out-of-home placement
continues pending full dependency trial. Children remain in placement outside the home
for safety until parents complete services.

V. SAFETY PLAN ATTEMPTED

Before removal, CPS attempted to implement an in-home safety plan on October 2nd that
required mother's boyfriend to move out and grandmother to provide supervision. The
safety agreement was signed by mother agreeing to protective measures. However, the
safety intervention failed when boyfriend returned to home. The safety plan could not
ensure child safety due to mother's inability to follow through. In-home safety planning
was insufficient given risk level.

VI. REUNIFICATION SERVICES

The court ordered mother to engage in reunification services per RCW 26.44.195 with
goal of family reunification. Services to reunify family include individual therapy,
domestic violence treatment, parenting classes, and drug/alcohol evaluation. The
reunification plan addresses the factors that led to removal. Mother must complete
services before return of children. Case plan requires successful engagement in services
to return child to parent. The family reunification goal depends on mother's progress
in treatment.

SUMMARY OF FINDINGS: November 5, 2024
"""


# ============================================================================
# GROUP 7-9: ADDITIONAL PROCEDURES (8 FIXTURES)
# ============================================================================

@pytest.fixture
def mandatory_parenting_seminar_simple() -> str:
    """Simple MANDATORY_PARENTING_SEMINAR test case."""
    return "Both parties shall complete mandatory parenting seminar before entry of final decree."


@pytest.fixture
def attorney_fees_award_simple() -> str:
    """Simple ATTORNEY_FEES_AWARD test case."""
    return "Court awards mother $25,000 in reasonable attorney fees based on need and ability to pay."


@pytest.fixture
def support_modification_request_simple() -> str:
    """Simple SUPPORT_MODIFICATION_REQUEST test case."""
    return "Father filed petition to modify child support due to substantial change in income."


@pytest.fixture
def substantial_change_circumstances_simple() -> str:
    """Simple SUBSTANTIAL_CHANGE_OF_CIRCUMSTANCES test case."""
    return "Father's income decreased by 35%, constituting substantial change of circumstances."


@pytest.fixture
def automatic_support_adjustment_simple() -> str:
    """Simple AUTOMATIC_SUPPORT_ADJUSTMENT test case."""
    return "Support shall include automatic cost-of-living adjustment each July based on CPI."


@pytest.fixture
def parenting_coordinator_simple() -> str:
    """Simple PARENTING_COORDINATOR test case."""
    return "The court appoints Susan Miller as parenting coordinator to resolve day-to-day disputes."


@pytest.fixture
def mediation_requirement_simple() -> str:
    """Simple MEDIATION_REQUIREMENT test case."""
    return "Parties shall attempt mandatory mediation before filing any modification petition."


@pytest.fixture
def counseling_requirement_simple() -> str:
    """Simple COUNSELING_REQUIREMENT test case."""
    return "Parents are ordered to participate in joint family counseling to reduce conflict."


@pytest.fixture
def procedural_dispute_resolution_document() -> str:
    """
    Document covering procedural requirements and dispute resolution (8 entities).
    Tests: MANDATORY_PARENTING_SEMINAR, ATTORNEY_FEES_AWARD, SUPPORT_MODIFICATION_REQUEST,
           SUBSTANTIAL_CHANGE_OF_CIRCUMSTANCES, AUTOMATIC_SUPPORT_ADJUSTMENT,
           PARENTING_COORDINATOR, MEDIATION_REQUIREMENT, COUNSELING_REQUIREMENT
    """
    return """
DISSOLUTION DECREE WITH PROCEDURAL REQUIREMENTS

I. MANDATORY PARENT EDUCATION

Before entry of final decree, both parties SHALL complete the mandatory parenting seminar
required by RCW 26.09.181. The parenting class must be completed within 60 days. Certificate
of completion of parent education program must be filed with court. The co-parenting class
focuses on helping children cope with divorce. Failure to complete parenting after separation
seminar will delay finalization.

II. ATTORNEY FEES AWARD

Based on disparity in income and resources, the court awards Wife attorney fees in the
amount of $42,000 under RCW 26.09.140. Husband shall pay these reasonable attorney fees
to Wife's counsel within 90 days. The award of attorney fees considers each party's financial
resources and need. Prevailing party is entitled to attorney fee costs including expert
witness fees. This attorney's fees award includes $6,000 in costs.

III. DISPUTE RESOLUTION MECHANISMS

The parties are high-conflict and require structured dispute resolution. A parenting
coordinator is APPOINTED pursuant to RCW 26.09.015. Jennifer Smith, LMFT, shall serve
as parent coordinator with authority to make decisions about schedule changes, vacation
planning, and day-to-day issues. The PC shall have binding decision-making authority.
The coordinator shall resolve parenting disagreements without court intervention.

Additionally, the parties must attempt mandatory mediation before filing any petition
to modify the parenting plan per RCW 26.09.015. Mediation is required for all disputes
before court action. Parties shall mediate in good faith through Family Court Services.
Parents must attempt to mediate disputes before scheduling contempt hearings.

Finally, both parents shall participate in family counseling with Dr. Robert Chang to
improve communication and reduce conflict. This co-parenting therapy is required for
six months. The therapeutic intervention aims to help parents cooperate. Joint counseling
sessions shall occur twice monthly. The counseling requirement continues until therapist
recommends termination.

IV. CHILD SUPPORT MODIFICATION PROVISIONS

Either party may file a petition to modify child support under RCW 26.09.170 upon showing
substantial change in circumstances. A support modification request requires demonstrating
a change of at least 25% in the support amount. Economic table calculations showing 30%
change justify adjustment of support obligations. Income changes that warrant modification
must be involuntary and permanent.

If Father's income decreases by 25% or more, that constitutes substantial change of
circumstances justifying modification. Similarly, substantial change in Mother's earning
capacity would support a support review. The burden is on moving party to prove substantial
change of at least 25%.

V. AUTOMATIC ADJUSTMENT PROVISION

Child support shall include an automatic cost-of-living adjustment (COLA) effective each
July 1st under RCW 26.09.100. The COLA adjustment uses the Seattle-Tacoma-Bellevue
Consumer Price Index. Annual automatic support adjustment of approximately 2-3% applies
unless either party objects in writing. This inflation adjustment maintains the real
value of support. The automatic increase is self-executing without court order.

ORDERED: November 5, 2024
"""


# ============================================================================
# COMPREHENSIVE PHASE 3 DOCUMENT (ALL 43 ENTITIES)
# ============================================================================

@pytest.fixture
def phase3_comprehensive_document() -> str:
    """
    Comprehensive document containing all 43 Phase 3 entity types for E2E testing.
    Tests all 9 pattern groups in a single realistic family law document.
    """
    return """
SUPERIOR COURT OF WASHINGTON FOR KING COUNTY

In re: Marriage of Anderson and Comprehensive Family Law Matters
Case No. 24-3-11111-1 SEA

COMPREHENSIVE FINDINGS OF FACT, CONCLUSIONS OF LAW, AND FINAL ORDERS

═══════════════════════════════════════════════════════════
I. DISSOLUTION PROCEEDINGS & SEPARATION ALTERNATIVES
═══════════════════════════════════════════════════════════

The Wife's petition for legal separation filed March 1, 2024 is GRANTED rather than
dissolution to maintain insurance coverage. A decree of legal separation is entered
under RCW 26.09.030 permitting parties to live apart. Husband's alternative claim for
declaration of invalidity of marriage alleging fraud is DENIED. The marriage is valid
and no grounds exist for invalidity of marriage or annulment.

The parties' separation contract executed February 15, 2024 is approved. The property
settlement agreement fairly divides assets. The marital settlement agreement is incorporated.

PARENTING PLAN: Child shall have substantially equal residential time with both parents.
The residential schedule alternates weekly. Mother has majority of residential time during
school (60%). The residential time allocation serves child's best interests per RCW 26.09.002.

RETIREMENT DIVISION: Husband's 401(k) of $340,000 divided equally. A qualified domestic
relations order (QDRO) shall effectuate retirement benefit division per RCW 26.09.138.
Wife's IRA divided similarly. Pension division requires QDRO approval.

CHILD EXCHANGES: Due to past conflict, exchanges occur at designated safe exchange center
at Bellevue Police Department. Supervised exchange at neutral location mandatory. All
exchanges in public place at police station required.

═══════════════════════════════════════════════════════════
II. EXTENDED CHILD SUPPORT CALCULATION
═══════════════════════════════════════════════════════════

SUPPORT WORKSHEET: The child support worksheet (WS-01) shows basic support obligation
of $2,456 monthly. The support calculation worksheet uses combined income of $15,600.
The economic table worksheet is filed as Exhibit A per RCW 26.19.050.

POSTSECONDARY SUPPORT: Father contributes to postsecondary educational support when
children reach 18. University costs including tuition shared 65/35. College expenses
up to $20,000 annually. Tuition support for educational expenses beyond high school
per RCW 26.19.090.

TAX EXEMPTIONS: Mother awarded tax exemption for children in even years. Father claims
dependency exemption in odd years. Parents alternate tax exemption annually per RCW 26.19.100.

STANDARD OF LIVING: Children enjoyed upper-middle-class standard of living during marriage.
Both were high earners. Children accustomed to private school and travel. To maintain the
standard the children enjoyed, support exceeds basic calculation per RCW 26.19.001.

EXTRAORDINARY EXPENSES: Son's special needs require therapy ($180/week) - these
extraordinary medical expenses shared equally. Daughter's orthodontic costs ($8,400)
are extraordinary expenses split 50/50. Uninsured medical over $300 annually are
extraordinary costs. Son's tutoring expenses ($400/month) are extraordinary per RCW 26.19.080.

DAYCARE: Mother's work-related daycare of $1,600 monthly for after-school care included.
These daycare expenses for employment necessary per RCW 26.19.080. Father's child care
while working ($250/month summer) also included. Work-related child care factored in calculation.

═══════════════════════════════════════════════════════════
III. DETAILED UCCJEA JURISDICTIONAL ANALYSIS
═══════════════════════════════════════════════════════════

FORUM NON CONVENIENS: Mother's motion that California is more appropriate forum is DENIED.
While inconvenient forum doctrine permits declining jurisdiction per RCW 26.27.261, Washington
is proper venue. Court does not decline on convenience grounds despite distance issues.

JURISDICTION DECLINED: Father's argument that jurisdiction should be declined due to
Mother's unjustifiable conduct is DENIED. While RCW 26.27.271 permits declining when
party engaged in misconduct, Mother's move was lawful. Jurisdiction not refused based
on the relocation. Court does not decline to exercise jurisdiction.

ORDER REGISTRATION: A Nevada custody order dated June 1, 2020 is REGISTERED in Washington
per RCW 26.27.441. Registration of this order allows enforcement here. The foreign order
registered with King County is enforceable. Order registration completed under UCCJEA.

UCCJEA NOTICE: Father in Idaho served with proper notice to persons outside state per
RCW 26.27.241. UCCJEA notice provided by certified mail. Service outside state complied
with requirements. Grandmother in Montana received jurisdictional notice. Notice under
UCCJEA to all interested parties completed.

TEMPORARY EMERGENCY: Court exercises temporary emergency jurisdiction per RCW 26.27.231
due to evidence of immediate danger. Temporary emergency custody GRANTED to grandmother
pending hearing. Emergency temporary order necessary. Temporary custody pending jurisdictional
determination. Ex parte emergency custody entered.

═══════════════════════════════════════════════════════════
IV. PARENTAGE ESTABLISHMENT - COMPLEX PROCEEDINGS
═══════════════════════════════════════════════════════════

PRESUMED PARENT: John Anderson is presumed parent under marital presumption per
RCW 26.26A.115. Child born during marriage creates presumption of parentage. The
presumed father is legal parent. This presumptive parent status applies automatically.

CHALLENGE TO PARENTAGE: Wife filed challenge to presumed parentage within two years
per RCW 26.26A.240. The challenge to paternity alleges John not biological father.
Wife contests parentage. This paternity challenge based on DNA evidence showing
different biological father. Husband disputes parentage of child.

GENETIC TEST RESULTS: Court-ordered genetic testing at LabCorp August 2024. DNA test
results show 99.96% probability of paternity for Michael Chen. Genetic test results
establish Michael as biological father with paternity index of 18,543:1. These test
results confirm parentage exceeding 99.9% probability.

RESCISSION: John filed rescission of acknowledgment within 60-day period per
RCW 26.26A.235. Seeks to rescind acknowledgment signed at hospital. The 60-day
rescission right exercised timely. Motion to revoke acknowledgment granted based
on genetics disproving paternity.

ASSISTED REPRODUCTION: Second child conceived via assisted reproduction per RCW 26.26A.600.
Parties signed agreement pre-conception despite using donor sperm. In vitro fertilization
at Seattle Reproductive Medicine. IVF procedure with anonymous donor. Artificial insemination
agreement establishes both as legal parents.

SURROGACY: Third child born via court-validated surrogacy agreement per RCW 26.26A.705
with gestational carrier. Gestational surrogacy arrangement pre-approved. Wife and Michael
are intended parents. Surrogate mother has no parental rights. Gestational carrier agreement
approved pre-birth.

═══════════════════════════════════════════════════════════
V. ADOPTION PROCEEDINGS - EXTENDED PROCEDURES
═══════════════════════════════════════════════════════════

PREPLACEMENT REPORT: Favorable preplacement report from social worker September 15, 2024.
Home study report finds Anderson family suitable. Adoptive family assessment completed.
Suitability report recommends placement. Preplacement study concludes stable home per
RCW 26.33.190.

AGENCY VS. INDEPENDENT: Initially independent adoption without agency by birth mother's
choice. Private adoption arranged directly. Non-agency adoption required judicial approval.
Later, licensed adoption agency facilitated alternative placement. Agency placement by
Adoption Advocates per RCW 26.33.020. Child placing agency completed assessment.

STEPPARENT ADOPTION: Michael Chen filed stepparent adoption petition per RCW 26.33.140
to adopt Wife's child from prior relationship. Step-parent adoption simplified process.
Adoption by stepparent creates permanent relationship.

SIBLING CONTACT: Order includes sibling contact provision per RCW 26.33.420. Siblings
have sibling visitation twice yearly. Contact with siblings maintained. Maintain sibling
relationship through video calls monthly. Sibling communication encouraged.

SEALED RECORDS: Upon finalization, adoption records sealed per RCW 26.33.330. Sealed
adoption record protects privacy. File sealed upon entry of decree. Confidential adoption
accessible only by court order. Adoption file sealed includes birth certificate and
relinquishment.

═══════════════════════════════════════════════════════════
VI. CHILD PROTECTION INVESTIGATION DETAILS
═══════════════════════════════════════════════════════════

FAR PATHWAY: After report, CPS chose family assessment response (FAR) pathway per
RCW 26.44.260. FAR investigation for lower-risk case. Assessment track focuses on
services. Family assessment response emphasizes strengths.

MDT REVIEW: Multidisciplinary team (MDT) convened October 3rd per RCW 26.44.180. The
MDT review included CPS, police, medical. Multi-disciplinary team coordinated investigation.
Team reviewed medical evidence. Coordinated investigation by MDT comprehensive.

FORENSIC INTERVIEW: Forensic interviewer conducted child forensic interview at Children's
Advocacy Center October 5th. CAC interview used evidence-based protocol. Forensic interview
video recorded. Child gave account during interview. Forensic interviewer report provided.

OUT-OF-HOME PLACEMENT: Emergency out-of-home placement ordered October 5th. Children in
foster care temporarily per RCW 26.44.240. Later transferred to kinship placement with
grandmother. Placement outside home pending trial. Children remain in placement for safety.

SAFETY PLAN: CPS attempted in-home safety plan October 2nd requiring boyfriend to leave.
Safety agreement signed by mother. Protective measures included grandmother supervision.
Safety intervention failed. In-home safety insufficient.

REUNIFICATION SERVICES: Court ordered mother engage in reunification services per
RCW 26.44.195. Services to reunify include therapy, DV treatment, parenting. Reunification
plan addresses removal factors. Must complete services for return. Family reunification
goal depends on progress.

═══════════════════════════════════════════════════════════
VII. PROCEDURAL REQUIREMENTS & DISPUTE RESOLUTION
═══════════════════════════════════════════════════════════

PARENTING SEMINAR: Both parties complete mandatory parenting seminar per RCW 26.09.181
within 60 days before final decree. Parenting class certificate must be filed. Parent
education program required. Co-parenting class helps children cope.

ATTORNEY FEES: Court awards Wife attorney fees of $38,000 under RCW 26.09.140. Husband
pays reasonable attorney fees within 90 days. Award based on need and resources. Prevailing
party entitled to attorney fee costs. Attorney's fees award includes expert costs.

PARENTING COORDINATOR: Jennifer Smith appointed parenting coordinator per RCW 26.09.015
with authority over day-to-day issues. PC has binding authority. Parent coordinator
resolves schedule changes. Coordinator resolves parenting disagreements without court.

MANDATORY MEDIATION: Parties must attempt mandatory mediation before modification per
RCW 26.09.015. Mediation required for disputes. Parties mediate through Family Court
Services. Must attempt to mediate before contempt hearings.

COUNSELING REQUIREMENT: Both participate in family counseling with Dr. Chang. Co-parenting
therapy required six months. Therapeutic intervention helps cooperation. Joint counseling
twice monthly. Counseling requirement until therapist recommends termination per RCW 26.09.181.

SUPPORT MODIFICATION: Either party may file support modification under RCW 26.09.170
upon substantial change. Support modification request requires 25% change. Economic table
change of 30% justifies adjustment. Income change warrants modification if involuntary.
Father's 35% income decrease constitutes substantial change of circumstances. Mother's
earning change would support support review.

AUTOMATIC ADJUSTMENT: Support includes automatic cost-of-living adjustment each July
per RCW 26.09.100. COLA adjustment uses CPI. Annual automatic support adjustment of
2-3% applies. Inflation adjustment maintains value. Automatic increase self-executing.

═══════════════════════════════════════════════════════════
CERTIFICATE OF SERVICE
═══════════════════════════════════════════════════════════

ORDERED this 5th day of November, 2024.

_______________________________
Hon. Patricia Rodriguez
Superior Court Judge
"""


@pytest.fixture
def extraction_config_regex() -> Dict[str, any]:
    """Configuration for regex extraction mode testing."""
    return {
        "base_url": "http://localhost:8007",
        "extraction_mode": "regex",
        "confidence_threshold": 0.85,
        "timeout": 30.0
    }
