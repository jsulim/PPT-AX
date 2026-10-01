from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.integrations import WorkProveImportRequest
from db.models import BidContext, NoticeContext, Outline, Project, UsageEvent


def import_work_prove_payload(db: Session, payload: WorkProveImportRequest) -> tuple[
    Project,
    NoticeContext,
    BidContext,
    Outline,
]:
    agency = payload.bid.demand_org or payload.bid.notice_org
    project = Project(
        name=payload.bid.name,
        agency=agency,
        stage="preparing",
        notes=f"work_prove 공고번호: {payload.bid.no or ''}".strip(),
    )
    db.add(project)
    db.flush()

    raw_text = payload.notice.body_text or payload.notice.raw_text
    notice_context = NoticeContext(
        project_id=project.id,
        raw_text=raw_text,
        requirements=payload.notice.requirements,
        scoring_items=payload.notice.scoring_items,
        summary={
            "forms": payload.notice.forms,
            "qualifications": payload.notice.qualifications,
            "source": "work_prove",
        },
        status="draft",
    )
    db.add(notice_context)

    bid_context = BidContext(
        project_id=project.id,
        data={
            "source": "work_prove",
            "bid": payload.bid.model_dump(by_alias=True),
            "company": payload.company,
            "personnel": payload.personnel,
            "track_records": payload.track_records,
            "selected_personnel": payload.selected_personnel,
            "selected_track_records": payload.selected_track_records,
        },
        status="draft",
    )
    db.add(bid_context)

    outline = Outline(
        project_id=project.id,
        template_id=None,
        status="draft",
        items=payload.outline_items,
    )
    db.add(outline)

    db.add(
        UsageEvent(
            user_email=payload.user_email,
            event="import_work_prove",
            payload={
                "bid_no": payload.bid.no,
                "bid_ord": payload.bid.ord,
                "project_name": payload.bid.name,
                "requirements": len(payload.notice.requirements),
                "outline_items": len(payload.outline_items),
            },
        )
    )

    db.commit()
    db.refresh(project)
    db.refresh(notice_context)
    db.refresh(bid_context)
    db.refresh(outline)
    return project, notice_context, bid_context, outline
