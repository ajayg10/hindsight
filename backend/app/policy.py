"""
Hindsight Deterministic Policy Engine.
Encodes the 5 explicit governance rules:
- RULE-01-SPLIT-STORM: Group connected alerting services into a single incident via WCC
- RULE-02-ROOT-CAUSE: Traverse dependency graph to identify common root causes
- RULE-03-INVESTIGATE-CONFLICT: Graph path subsumption to resolve multi-investigator conflicts
- RULE-04-GUARDRAIL-BLAST: Human approval gate when blast radius > 5 services or revenue > $1,000/min
- RULE-05-STALE-PROCEDURE-REFUSAL: Refuse runbooks targeting superseded infrastructure (ADR-17)

Every decision returns the chosen rule ID, reason string, and UI policy chip.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    condition: str
    tool: str
    reason: str
    chip: str

POLICY_RULES: Dict[str, PolicyRule] = {
    "RULE-01-SPLIT-STORM": PolicyRule(
        rule_id="RULE-01-SPLIT-STORM",
        condition="Alert stream received with multiple alerting services",
        tool="split_storm",
        reason="Group connected alerting services into a single incident via WCC to prevent alert storms and duplicate work.",
        chip="WCC Storm Collapse"
    ),
    "RULE-02-ROOT-CAUSE": PolicyRule(
        rule_id="RULE-02-ROOT-CAUSE",
        condition="Incident opened with alerting services requiring root cause candidate exploration",
        tool="root_cause_candidates",
        reason="Traverse upstream dependency graph to identify common ancestor root causes explaining all alerts.",
        chip="Dependency Intersection"
    ),
    "RULE-03-INVESTIGATE-CONFLICT": PolicyRule(
        rule_id="RULE-03-INVESTIGATE-CONFLICT",
        condition="Multiple investigators submit competing root cause hypotheses for the same incident",
        tool="resolve_conflict",
        reason="Evaluate dependency path between candidate root causes; upstream failure subsumes downstream symptom (Q10).",
        chip="Graph Subsumption Q10"
    ),
    "RULE-04-GUARDRAIL-BLAST": PolicyRule(
        rule_id="RULE-04-GUARDRAIL-BLAST",
        condition="Remediation blast radius > 5 services or revenue impact > $1,000/min",
        tool="blast_radius",
        reason="Blast radius exceeds autonomous execution threshold (5 services); require human approval gate before destructive actions.",
        chip="Blast Radius Gate"
    ),
    "RULE-05-STALE-PROCEDURE-REFUSAL": PolicyRule(
        rule_id="RULE-05-STALE-PROCEDURE-REFUSAL",
        condition="Procedure targets infrastructure or dependencies modified/retired by subsequent architectural change (ADR)",
        tool="recall_procedure",
        reason="Procedure targets retired infrastructure (cache-a superseded by change-adr-17); refuse execution despite high historical win rate and select valid alternative (R-12).",
        chip="ADR Invalidation Refusal"
    ),
    "RULE-06-OWNERSHIP-ROUTING": PolicyRule(
        rule_id="RULE-06-OWNERSHIP-ROUTING",
        condition="Service incident requires owning team identification and escalation channel",
        tool="who_owns",
        reason="Traverse OWNS and MEMBER_OF graph relationships to identify owning team, Slack channels, and responsible engineers.",
        chip="Team Ownership"
    ),
    "RULE-07-EXPERT-ROUTING": PolicyRule(
        rule_id="RULE-07-EXPERT-ROUTING",
        condition="Incident triage requires domain expert with active availability",
        tool="who_knows",
        reason="Query EXPERT_IN scores and on-call/leave status to dynamically route around absent engineers to active experts.",
        chip="Expert Routing"
    ),
    "RULE-08-DECISION-PROVENANCE": PolicyRule(
        rule_id="RULE-08-DECISION-PROVENANCE",
        condition="Service architecture or failure mode requires historical context from ADRs and discussion threads",
        tool="trace_decision",
        reason="Trace architectural decision records (ADRs), discussion threads, and authors across organizational memory graph.",
        chip="Decision Provenance"
    ),
    "RULE-09-DOC-STALENESS-AUDIT": PolicyRule(
        rule_id="RULE-09-DOC-STALENESS-AUDIT",
        condition="Structural dependency changes occur that invalidate existing documentation and runbooks",
        tool="staleness_audit",
        reason="Audit runbooks and documentation verified prior to structural graph dependency modifications and open remediation tasks.",
        chip="Doc Staleness Audit"
    ),
}

def get_rule(rule_id: str) -> PolicyRule:
    if rule_id not in POLICY_RULES:
        raise KeyError(f"Unknown policy rule ID: {rule_id}")
    return POLICY_RULES[rule_id]

def list_rules() -> List[Dict[str, str]]:
    return [asdict(r) for r in POLICY_RULES.values()]

def evaluate_blast_guardrail(blast_count: int, rev_per_min: float, max_services: int = 5, max_rev_per_min: float = 1000.0) -> Dict[str, Any]:
    requires_approval = blast_count > max_services or rev_per_min > max_rev_per_min
    rule = get_rule("RULE-04-GUARDRAIL-BLAST")
    return {
        "rule_id": rule.rule_id,
        "requires_approval": requires_approval,
        "blast_count": blast_count,
        "rev_per_min": rev_per_min,
        "reason": f"Blast radius of {blast_count} services (${rev_per_min:,.0f}/min) {'exceeds' if requires_approval else 'within'} automated limit ({max_services} services, ${max_rev_per_min:,.0f}/min).",
        "chip": rule.chip
    }

def evaluate_procedure_staleness(procedure_id: str, invalidating_changes: List[str]) -> Dict[str, Any]:
    rule = get_rule("RULE-05-STALE-PROCEDURE-REFUSAL")
    is_refused = len(invalidating_changes) > 0
    if is_refused:
        changes_str = ", ".join(invalidating_changes)
        reason = f"Procedure {procedure_id} refused: invalidated by architectural change(s): {changes_str}."
    else:
        reason = f"Procedure {procedure_id} approved: no invalidating architectural changes detected."
    return {
        "rule_id": rule.rule_id,
        "procedure_id": procedure_id,
        "refused": is_refused,
        "invalidating_changes": invalidating_changes,
        "reason": reason,
        "chip": rule.chip
    }
