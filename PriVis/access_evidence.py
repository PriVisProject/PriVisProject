"""Join the validated records used to review direct membership evidence."""

from dataclasses import dataclass


NO_POLICY = "No matching policy"
POLICY_DECISIONS = ("Allowed", "Denied", "Approval Required", NO_POLICY)


@dataclass(frozen=True)
class MembershipEvidence:
    user: object
    group: object
    membership: object
    policy: object | None
    findings: tuple

    @property
    def row(self):
        return (
            self.user.name, self.user.sam_account_name, self.user.department,
            self.user.role, self.group.group_name,
            self.policy.access_decision if self.policy else NO_POLICY,
        )


def collect_evidence(review):
    policies = {
        (policy.role, policy.group_id): policy
        for policy in review.dataset.access_policy.itertuples(index=False)
    }
    linked = {}
    for finding in review.findings:
        linked.setdefault((finding.user_id, finding.group_id), []).append(finding)

    evidence = []
    for membership in review.dataset.memberships.itertuples(index=False):
        user = review.users_by_id[membership.user_id]
        group = review.groups_by_id[membership.group_id]
        evidence.append(MembershipEvidence(
            user, group, membership, policies.get((user.role, group.group_id)),
            tuple(linked.get((user.user_id, group.group_id), ())),
        ))
    return evidence
