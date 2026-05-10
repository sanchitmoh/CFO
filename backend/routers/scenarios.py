"""
AI CFO — Cash Flow Scenario Planning Router
Scenario CRUD, comparison, sensitivity, Monte Carlo, templates, sharing.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User
from schemas import (
    ScenarioCreate, ScenarioUpdate, ScenarioOut,
    ScenarioComparisonResponse, SensitivityRequest, SensitivityResponse,
    MonteCarloRequest, MonteCarloResponse, ScenarioTemplate,
    ScenarioShareCreate, ScenarioShareOut,
)
from services import scenario_service
from services.audit_service import log_action

router = APIRouter()


# ── Templates ─────────────────────────────────────────────────────

@router.get("/templates", response_model=list[ScenarioTemplate])
async def list_templates(user: User = Depends(get_current_user)):
    return scenario_service.get_templates()


@router.get("/templates/{template_id}", response_model=ScenarioTemplate)
async def get_template(template_id: str, user: User = Depends(get_current_user)):
    t = scenario_service.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


# ── Shared With Me ────────────────────────────────────────────────

@router.get("/shared", response_model=list[ScenarioShareOut])
async def list_shared_with_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    shares = await scenario_service.list_shared_with_me(db, user.id)
    return [ScenarioShareOut.model_validate(s) for s in shares]


# ── Scenario CRUD ─────────────────────────────────────────────────

@router.get("/", response_model=list[ScenarioOut])
async def list_scenarios(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scenarios = await scenario_service.list_scenarios(db, user.workspace_id)
    return [ScenarioOut.model_validate(s) for s in scenarios]


@router.post("/", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    data: ScenarioCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scen = await scenario_service.create_scenario(db, user.workspace_id, user.id, data)
    await db.commit()
    await log_action(db, user, "scenario.create", "scenario", scen.id, new_value={"name": data.name})
    return ScenarioOut.model_validate(scen)


@router.get("/compare", response_model=ScenarioComparisonResponse)
async def compare_scenarios(
    ids: str = Query(..., description="Comma-separated scenario UUIDs"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scenario_ids = [uuid.UUID(s.strip()) for s in ids.split(",")]
    return await scenario_service.compare_scenarios(db, user.workspace_id, scenario_ids)


@router.get("/{scenario_id}", response_model=ScenarioOut)
async def get_scenario(
    scenario_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scen = await scenario_service.get_scenario(db, user.workspace_id, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioOut.model_validate(scen)


@router.put("/{scenario_id}", response_model=ScenarioOut)
async def update_scenario(
    scenario_id: uuid.UUID,
    data: ScenarioUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scen = await scenario_service.get_scenario(db, user.workspace_id, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scen = await scenario_service.update_scenario(db, user.workspace_id, scen, data)
    await db.commit()
    return ScenarioOut.model_validate(scen)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scen = await scenario_service.get_scenario(db, user.workspace_id, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Scenario not found")
    await log_action(db, user, "scenario.delete", "scenario", scen.id)
    await scenario_service.delete_scenario(db, scen)
    await db.commit()


# ── Sensitivity & Monte Carlo ─────────────────────────────────────

@router.post("/{scenario_id}/sensitivity", response_model=SensitivityResponse)
async def sensitivity_analysis(
    scenario_id: uuid.UUID,
    data: SensitivityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await scenario_service.run_sensitivity(db, user.workspace_id, scenario_id, data)


@router.post("/monte-carlo", response_model=MonteCarloResponse)
async def monte_carlo(
    data: MonteCarloRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    return await scenario_service.run_monte_carlo(db, user.workspace_id, data)


# ── Sharing ───────────────────────────────────────────────────────

@router.post("/{scenario_id}/share", response_model=ScenarioShareOut, status_code=status.HTTP_201_CREATED)
async def share_scenario(
    scenario_id: uuid.UUID,
    data: ScenarioShareCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scen = await scenario_service.get_scenario(db, user.workspace_id, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Scenario not found")
    share = await scenario_service.share_scenario(db, scenario_id, user.id, data)
    await db.commit()
    await log_action(db, user, "scenario.share", "scenario", scenario_id,
                     new_value={"shared_with": str(data.shared_with_user_id), "permission": data.permission})
    return ScenarioShareOut.model_validate(share)


@router.get("/{scenario_id}/shares", response_model=list[ScenarioShareOut])
async def list_scenario_shares(
    scenario_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    scen = await scenario_service.get_scenario(db, user.workspace_id, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Scenario not found")
    shares = await scenario_service.list_shares_for_scenario(db, scenario_id)
    return [ScenarioShareOut.model_validate(s) for s in shares]


@router.delete("/{scenario_id}/share/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_scenario_share(
    scenario_id: uuid.UUID,
    share_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    await scenario_service.revoke_share(db, share_id)
    await db.commit()
