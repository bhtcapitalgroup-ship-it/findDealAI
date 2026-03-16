"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.contractors import router as contractors_router
from app.api.v1.documents import router as documents_router
from app.api.v1.financials import router as financials_router
from app.api.v1.leases import router as leases_router
from app.api.v1.maintenance import router as maintenance_router
from app.api.v1.payments import router as payments_router
from app.api.v1.properties import router as properties_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.units import router as units_router
from app.api.v1.extension import router as extension_router
from app.api.v1.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(properties_router)
api_router.include_router(units_router)
api_router.include_router(tenants_router)
api_router.include_router(leases_router)
api_router.include_router(payments_router)
api_router.include_router(maintenance_router)
api_router.include_router(contractors_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
api_router.include_router(financials_router)
api_router.include_router(webhooks_router)
api_router.include_router(extension_router)
