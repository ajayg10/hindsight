# Query verification status

Only Q1 and its invariant are present for the Phase 0 concurrency spike. They are
unverified until the real-engine harness passes. Q2–Q10 belong to later gated phases.

Q1 uses a conditional update and records the task version on CLAIMED edges.
The harness pre-creates all Agents: a missing Agent in this draft query could
otherwise mutate the task before returning no rows. Later internal tools must
validate Agent identity before claim execution, or match the Agent before SET.

The invariant groups claims by task and version. The harness also checks the
number of successful responses, task status, and total claim edges, so an empty
graph cannot masquerade as a successful zero-double-claim result.
