"""
Draft review routes: list, detail, approve, reject.
"""

import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

router = APIRouter()


@router.get("/")
async def draft_list(request: Request):
    mem = request.app.state.memory
    drafts = await mem.get_pending_drafts()
    return _TEMPLATES.TemplateResponse(
        "drafts.html", {"request": request, "drafts": drafts}
    )


@router.get("/drafts/{draft_id}")
async def draft_detail(draft_id: int, request: Request):
    mem = request.app.state.memory
    draft = await mem.get_draft(draft_id)
    if not draft:
        return _TEMPLATES.TemplateResponse(
            "drafts.html",
            {"request": request, "drafts": [], "error": f"Draft #{draft_id} not found."},
            status_code=404,
        )
    req = await mem.get_request(draft.request_id)
    return _TEMPLATES.TemplateResponse(
        "draft_detail.html", {"request": request, "draft": draft, "req": req}
    )


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int, request: Request):
    mem = request.app.state.memory
    draft = await mem.get_draft(draft_id)
    if draft and draft.verdict == "pending":
        await mem.review_draft(draft_id, "ok")
    return RedirectResponse(url="/", status_code=303)


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(
    draft_id: int,
    request: Request,
    actual_message_sent: str = Form(default=""),
    owner_comment: str = Form(default=""),
):
    mem = request.app.state.memory
    draft = await mem.get_draft(draft_id)
    if draft and draft.verdict == "pending":
        await mem.review_draft(
            draft_id,
            "nok",
            actual_message_sent.strip() or None,
            owner_comment.strip() or None,
        )
    return RedirectResponse(url="/", status_code=303)
