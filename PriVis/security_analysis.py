"""Evaluate validated PriVis data using explicit account and access rules."""

import argparse
from dataclasses import dataclass
from datetime import date
import logging
from pathlib import Path
from typing import Literal

from data_loader import DEFAULT_DATA_FOLDER, Dataset, DataValidationError, load_dataset


FindingType = Literal["expired_account", "denied_membership", "approval_required"]
SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


@dataclass(frozen=True)
class Finding:
    rule: FindingType
    severity: str
    user_id: str
    user_name: str
    account_name: str
    role: str
    explanation: str
    recommendation: str
    group_id: str | None = None
    group_name: str | None = None
    policy_decision: str | None = None
    policy_reason: str | None = None


def analyze_findings(dataset: Dataset, *, review_date: date) -> list[Finding]:
    """Evaluate findings for enabled accounts and return them in severity order."""
    enabled_users = {
        user.user_id: user
        for user in dataset.users.itertuples(index=False)
        if user.enabled
    }
    groups = {group.group_id: group for group in dataset.groups.itertuples(index=False)}
    policies = {
        (policy.role, policy.group_id): policy
        for policy in dataset.access_policy.itertuples(index=False)
    }
    findings = []
    for user in enabled_users.values():
        if user.end_date is not None and user.end_date < review_date:
            findings.append(Finding(
                rule="expired_account",
                severity="High",
                user_id=user.user_id,
                user_name=user.name,
                account_name=user.sam_account_name,
                role=user.role,
                explanation=f"The account is enabled after its end date ({user.end_date}).",
                recommendation="Confirm the end date and disable the account if access has ended.",
            ))

    for membership in dataset.memberships.itertuples(index=False):
        user = enabled_users.get(membership.user_id)
        if user is None:
            continue
        policy = policies.get((user.role, membership.group_id))
        if policy is None or policy.access_decision == "Allowed":
            continue

        if policy.access_decision == "Denied":
            rule = "denied_membership"
            explanation = f"The access policy explicitly denies this group to the {user.role} role."
            recommendation = "Confirm the role and group assignment, then remove the denied membership."
        else:
            reason = _approval_issue(membership, review_date)
            if reason is None:
                continue
            rule = "approval_required"
            explanation = f"This membership requires documented approval. {reason}"
            recommendation = "Verify or renew the documented approval, or remove the membership."

        group = groups[membership.group_id]
        findings.append(Finding(
            rule=rule,
            severity=group.risk_level,
            user_id=user.user_id,
            user_name=user.name,
            account_name=user.sam_account_name,
            role=user.role,
            group_id=group.group_id,
            group_name=group.group_name,
            policy_decision=policy.access_decision,
            policy_reason=policy.policy_reason,
            explanation=explanation,
            recommendation=recommendation,
        ))

    return sorted(findings, key=finding_sort_key)


def finding_sort_key(finding: Finding):
    return (
        SEVERITY_ORDER[finding.severity],
        finding.user_id,
        finding.rule,
        finding.group_id or "",
    )


def _approval_issue(membership, review_date: date) -> str | None:
    if membership.approval_status != "Approved":
        return f"The recorded approval status is {membership.approval_status}."
    if not membership.approval_ticket or membership.approval_expires is None:
        return "The approval record is missing a ticket or expiry date."
    if membership.approval_expires < review_date:
        return f"The approval expired on {membership.approval_expires}."
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Review PriVis access findings.")
    parser.add_argument("folder", nargs="?", type=Path, default=DEFAULT_DATA_FOLDER)
    parser.add_argument("--as-of", type=date.fromisoformat, metavar="YYYY-MM-DD",
                        help="Review date (defaults to the local date).")
    args = parser.parse_args()
    review_date = args.as_of or date.today()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        dataset = load_dataset(args.folder)
    except DataValidationError as error:
        logging.error("%s", error)
        return 1
    findings = analyze_findings(dataset, review_date=review_date)
    print(f"{len(findings)} finding(s) as of {review_date}")
    for finding in findings:
        subject = f"{finding.user_name} ({finding.account_name}, {finding.user_id})"
        if finding.group_id is not None:
            subject += f" / {finding.group_name} ({finding.group_id})"
        print(f"\n[{finding.severity}] {subject}")
        if finding.policy_decision is not None:
            print(f"  Policy: {finding.role} / {finding.policy_decision} / {finding.policy_reason}")
        print(f"  {finding.explanation}")
        print(f"  Review: {finding.recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
