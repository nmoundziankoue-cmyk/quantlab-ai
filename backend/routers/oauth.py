"""M9 Phase 10 — OAuth2 provider endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from services.oauth_providers import get_provider, list_providers, generate_state

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


@router.get("/providers")
def get_providers():
    return {"providers": list_providers()}


@router.get("/authorize/{provider}")
def authorize(provider: str, redirect_uri: str = Query(...)):
    p = get_provider(provider)
    if not p:
        raise HTTPException(404, f"Provider '{provider}' not found")
    state = generate_state()
    url = p.build_authorization_url(redirect_uri, state)
    return {"authorization_url": url, "state": state, "provider": provider}


class TokenExchange(BaseModel):
    provider: str
    code: str
    redirect_uri: str


@router.post("/token")
def exchange_token(body: TokenExchange):
    p = get_provider(body.provider)
    if not p:
        raise HTTPException(404, f"Provider '{body.provider}' not found")
    tokens = p.exchange_code(body.code, body.redirect_uri)
    user_info = p.get_user_info(tokens.access_token)
    return {
        "tokens": tokens.__dict__,
        "user": {
            "provider": user_info.provider,
            "provider_user_id": user_info.provider_user_id,
            "email": user_info.email,
            "name": user_info.name,
            "avatar_url": user_info.avatar_url,
        },
    }
