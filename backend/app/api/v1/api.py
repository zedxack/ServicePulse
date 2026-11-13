"""
ServicePulse - API v1 Router Assembly
Author: Muhammadyusuf Usmonov
"""
from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    agent,
    audit,
    auth,
    dashboard,
    health,
    incidents,
    inventory,
    organizations,
    remediation,
    software,
    tickets,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(software.router, prefix="/software", tags=["software"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(remediation.router, prefix="/remediations", tags=["remediations"])
