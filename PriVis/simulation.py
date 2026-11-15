"""Read-only membership removal using the existing security rules."""

from dataclasses import dataclass, replace
from datetime import date

from data_loader import Dataset
from security_analysis import Finding, analyze_findings, finding_sort_key


@dataclass(frozen=True)
class SimulationResult:
    before: tuple[Finding, ...]
    after: tuple[Finding, ...]
    cleared: tuple[Finding, ...]
    added: tuple[Finding, ...]


def preview_removal(dataset: Dataset, *, user_id: str, group_id: str,
                    review_date: date, baseline: tuple[Finding, ...] | None = None
                    ) -> SimulationResult:
    """Reevaluate the selected user's rules and retain other accounts' findings."""
    memberships = dataset.memberships
    selected = memberships["user_id"].eq(user_id)
    removed = selected & memberships["group_id"].eq(group_id)
    if removed.sum() != 1:
        raise ValueError("Select a current direct membership for this user.")

    before = baseline
    if before is None:
        before = tuple(analyze_findings(dataset, review_date=review_date))
    simulated = replace(
        dataset,
        users=dataset.users.loc[dataset.users["user_id"].eq(user_id)],
        memberships=memberships.loc[selected & ~removed],
    )
    user_after = analyze_findings(simulated, review_date=review_date)
    # The engine evaluates each account independently. Preserve its global order
    # by retaining baseline entries that still occur in the isolated review.
    surviving = set(user_after)
    user_before = {finding for finding in before if finding.user_id == user_id}
    after = tuple(f for f in before if f.user_id != user_id or f in surviving)
    added = tuple(f for f in user_after if f not in user_before)
    if added:
        after = tuple(sorted((*after, *added), key=finding_sort_key))
    cleared = tuple(f for f in before if f.user_id == user_id and f not in surviving)
    return SimulationResult(before, after, cleared, added)
