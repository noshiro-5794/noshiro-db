# Migration records

These reports preserve the original evidence from the Django retirement.
References to running legacy services describe the state at the time of each
report. Consult the [current migration guide](../migration.md) and
[deployment guide](../../../../deploy/README.md) for operating instructions.

| Record | Contents |
| --- | --- |
| [Migration ledger](migration-ledger.md) | Implementation, rehearsal results, and the production cutover |
| [HTTP parity](http-parity.md) | Request, response, and write-effect comparisons |
| [Cutover review](cutover-review.md) | Early blockers and transition requirements |
| [Compatibility notes](compatibility.md) | Protocol and schema decisions during the parallel run |
| [Schema transition](schema-transition.md) | Alembic ownership and historical revisions |
| [Display projections](display-projections.md) | Matching and presentation backfill evidence |
| [Worker baseline](worker-baseline.md) | Legacy task responsibilities and queue behavior |
| [Worker migration plan](worker-migration-plan.md) | The task migration sequence and verification strategy |
