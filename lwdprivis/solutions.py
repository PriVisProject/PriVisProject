"""Apply supported remediation actions to copies of the active tables."""

from dataclasses import replace

from security_analysis import analyze_findings


def remedy(dataset, findings, review_date):
    users = dataset.users.copy()
    memberships = dataset.memberships
    removals = set()
    for finding in findings:
        if finding.rule == "expired_account":
            users.loc[users["user_id"].eq(finding.user_id), "enabled"] = False
        elif finding.rule in ("denied_membership", "approval_required"):
            removals.add((finding.user_id, finding.group_id))
        else:
            raise ValueError(f"No sandbox action for {finding.rule}.")
    if removals:
        keep = [
            pair not in removals
            for pair in zip(memberships["user_id"], memberships["group_id"])
        ]
        memberships = memberships.loc[keep].copy()
    updated = replace(dataset, users=users, memberships=memberships)
    return updated, analyze_findings(updated, review_date=review_date)
