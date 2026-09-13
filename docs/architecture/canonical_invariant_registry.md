# Canonical Invariant Registry

> Status: normative index. Individual contracts remain the source of the
> domain-specific rule; this index records their semantic layer and prevents
> implementation details from being promoted as architecture.

## Reading rules

An invariant is a refactor-stable observable obligation. A canonical rule
uses `MUST`, `MUST NOT`, or `MAY` to describe that obligation. Numeric
thresholds, template paths, class or function names, diagnostic tags, retry
budgets, and configuration defaults are implementation or runtime-policy
details unless an external protocol or safety requirement makes the exact
value part of the obligation.

Every canonical invariant is interpreted with these fields:

- **Scope:** the behavior and owners to which the rule applies.
- **Rule:** the stable obligation.
- **Observable consequence:** what a caller, operator, or focused test can
  observe when the rule is met.
- **Allowed variation:** algorithms, thresholds, template sets, state names,
  and retry timing may change when the rule and its verification still hold.
- **Verification:** the focused behavior or contract tests linked by the
  owning contract.

Production code describes AS-IS behavior. A document becomes normative only
when the behavior is implemented, verified, intentionally designed, and
expected to survive refactoring. Conflicts between an existing contract and
code or tests are `CONFLICT_REQUIRES_REVIEW`; neither side is silently
rewritten to match the other.

## Inventory and disposition

| Document | Candidate | Semantic layer | Disposition |
| --- | --- | --- | --- |
| [Precondition Contracts](precondition_contracts.md) | completion, `DEFER`, recovery, and objective-world routing | `ARCHITECTURE_INVARIANT` | canonical parent contract |
| [Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md) | scheduling and runtime ownership | `ARCHITECTURE_INVARIANT` | canonical parent contract |
| [Battle Stall Recovery Contract](battle_stall_recovery_contract.md) | perception/decision separation and bounded recovery escalation | `DOMAIN_CONTRACT` | canonical |
| [Supervisor Lifecycle Contract](supervisor_lifecycle_contract.md) | lifecycle safety and crash-loop escalation | `DOMAIN_CONTRACT` | canonical |
| [Lobby Scene Contract](../features/navigation/lobby_scene_contract.md) | lobby perception and navigation safety | `DOMAIN_CONTRACT` | canonical |
| [Dungeon Relaunch Recovery Contract](../features/navigation/dungeon_relaunch_recovery_contract.md) | objective dungeon recovery and intent restoration | `DOMAIN_CONTRACT` | canonical |
| [Town Building Pipeline](../features/town_building/pipeline.md) | §8 bulletin-board decision semantics | `DOMAIN_CONTRACT` | `MIXED`; only §8 is a canonical specialization of the precondition contract |
| [Stamina Retreat Feature](../features/stamina_retreat_feature.md) | retreat precedence and temporary dungeon resume | `DOMAIN_CONTRACT` | canonical |
| [Notification Contract](../features/notification/notification_contract.md) | non-blocking notification delivery | `DOMAIN_CONTRACT` | canonical |
| `docs/storys/` | incident rationale and promotion history | `HISTORY` | retain as narrative; not normative |
| `docs/todos/` and `docs/architecture/research/` | proposed or investigative rules | `TODO` / `HISTORY` | do not promote without implementation and focused verification |

## Canonical hierarchy

`Precondition Contracts` owns the cross-domain rules for evidence, action
completion, defer, and recovery. Feature contracts may specialize those rules
only where they add an observable domain condition. They MUST link to the
parent rule instead of restating it with a different obligation.
