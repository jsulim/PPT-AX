from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.decks import DeckBuildRequest, GeneratedDeckRead
from app.services.decks import build_project_deck
from app.settings import Settings, get_settings
from db.models import GeneratedDeck

router = APIRouter(tags=["decks"])


@router.post("/projects/{project_id}/decks", response_model=GeneratedDeckRead, status_code=201)
def build_deck(
    project_id: uuid.UUID,
    payload: DeckBuildRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GeneratedDeck:
    try:
        return build_project_deck(
            db,
            project_id=project_id,
            template_id=payload.template_id,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/decks/{deck_id}", response_model=GeneratedDeckRead)
def get_deck(deck_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> GeneratedDeck:
    deck = db.get(GeneratedDeck, deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="생성된 제안서를 찾을 수 없습니다.")
    return deck


@router.get("/decks/{deck_id}/download")
def download_deck(deck_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> FileResponse:
    deck = db.get(GeneratedDeck, deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="생성된 제안서를 찾을 수 없습니다.")

    output_path = Path(deck.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="PPTX 파일을 찾을 수 없습니다.")

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{deck.title}.pptx",
    )
