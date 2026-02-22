"""
Authentication middleware and login routes.

Auth strategy: single pre-shared token stored in REVIEW_TOKEN env var.
Browser sessions use an httponly cookie named "session".
API callers may use Authorization: Bearer <token> as an alternative.
"""

import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

_TEMPLATES = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

# Routes that don't require authentication
_PUBLIC_PATHS = {"/login"}

router = APIRouter()


class AuthMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated requests to /login."""

    def __init__(self, app, review_token: str):
        super().__init__(app)
        self._token = review_token

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Accept cookie (browser) or Bearer header (API / CLI)
        session = request.cookies.get("session")
        bearer = request.headers.get("authorization", "").removeprefix("Bearer ").strip()

        if session == self._token or bearer == self._token:
            return await call_next(request)

        return RedirectResponse(url="/login", status_code=303)


@router.get("/login")
async def login_page(request: Request):
    return _TEMPLATES.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login_submit(request: Request, token: str = Form(...)):
    review_token = request.app.state.review_token
    if token == review_token:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie("session", token, httponly=True, samesite="lax")
        return response
    return _TEMPLATES.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid token. Try again."},
        status_code=401,
    )
