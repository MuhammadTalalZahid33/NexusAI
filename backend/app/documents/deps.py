"""Temporary tenancy dependency.

Real authentication + org resolution arrives in Milestone 7. Until then we
resolve a single default organization (creating it on first use) so document
endpoints have an org_id to scope by. Crucially, the rest of the code already
treats org_id as the tenant boundary, so swapping this for real auth later is
a localized change -- the isolation model does not get rebuilt.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Organization

_DEFAULT_ORG_NAME = "Default Organization"


async def get_current_org_id(session: AsyncSession) -> uuid.UUID:
    org = await session.scalar(
        select(Organization).where(Organization.name == _DEFAULT_ORG_NAME)
    )
    if org is None:
        org = Organization(name=_DEFAULT_ORG_NAME)
        session.add(org)
        await session.commit()
        await session.refresh(org)
    return org.id
