import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from models import ApprovalPolicy, ApprovalStatus, ExpenseApproval
from schemas import ApprovalPolicyCreate
from services import approval_service


class FakeAsyncSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None


@pytest.mark.anyio
async def test_find_matching_policy_is_case_insensitive_and_prefers_highest_floor(monkeypatch):
    workspace_id = uuid.uuid4()
    broad_policy = ApprovalPolicy(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="Broad",
        min_amount=Decimal("0"),
        max_amount=Decimal("1000"),
        categories=["Travel"],
        auto_approve_roles=[],
        required_approvers=1,
    )
    specific_policy = ApprovalPolicy(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="Specific",
        min_amount=Decimal("500"),
        max_amount=Decimal("1500"),
        categories=["  travel  "],
        auto_approve_roles=[],
        required_approvers=1,
    )

    monkeypatch.setattr(
        approval_service,
        "list_policies",
        AsyncMock(return_value=[broad_policy, specific_policy]),
    )

    matched = await approval_service.find_matching_policy(
        db=SimpleNamespace(),
        ws_id=workspace_id,
        amount=700,
        category="TRAVEL",
    )

    assert matched is specific_policy


@pytest.mark.anyio
async def test_submit_for_approval_marks_auto_approved_when_requester_role_matches(monkeypatch):
    workspace_id = uuid.uuid4()
    transaction_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    requester = SimpleNamespace(id=requester_id, role=SimpleNamespace(value="cfo"))
    policy = ApprovalPolicy(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="CFO Auto",
        min_amount=Decimal("0"),
        max_amount=Decimal("5000"),
        categories=[],
        auto_approve_roles=["owner", "cfo"],
        required_approvers=1,
    )
    db = FakeAsyncSession()

    monkeypatch.setattr(
        approval_service,
        "get_approval_by_transaction",
        AsyncMock(return_value=None),
    )

    approval = await approval_service.submit_for_approval(
        db=db,
        ws_id=workspace_id,
        txn_id=transaction_id,
        requester=requester,
        policy=policy,
    )

    assert approval.status == ApprovalStatus.auto_approved
    assert approval.approved_by == requester_id
    assert approval.approved_at is not None
    assert approval.notes == "Automatically approved by policy role"
    assert db.added == [approval]


@pytest.mark.anyio
async def test_submit_for_approval_rejects_duplicate_requests(monkeypatch):
    workspace_id = uuid.uuid4()
    transaction_id = uuid.uuid4()
    existing = ExpenseApproval(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        transaction_id=transaction_id,
        policy_id=uuid.uuid4(),
        requested_by=uuid.uuid4(),
        status=ApprovalStatus.pending,
    )
    requester = SimpleNamespace(id=uuid.uuid4(), role=SimpleNamespace(value="employee"))
    policy = ApprovalPolicy(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="General",
        min_amount=Decimal("0"),
        max_amount=Decimal("1000"),
        categories=[],
        auto_approve_roles=[],
        required_approvers=1,
    )

    monkeypatch.setattr(
        approval_service,
        "get_approval_by_transaction",
        AsyncMock(return_value=existing),
    )

    with pytest.raises(ValueError, match="already has an approval request"):
        await approval_service.submit_for_approval(
            db=FakeAsyncSession(),
            ws_id=workspace_id,
            txn_id=transaction_id,
            requester=requester,
            policy=policy,
        )


def test_approval_policy_create_rejects_inverted_amount_ranges():
    with pytest.raises(ValidationError, match="max_amount"):
        ApprovalPolicyCreate(
            name="Broken",
            min_amount=1000,
            max_amount=200,
        )
