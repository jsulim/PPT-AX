from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.settings import Settings
from core.pptx.apply_text import TextReplacement, apply_text_replacements
from db.models import (
    BidContext,
    Document,
    GeneratedDeck,
    NoticeContext,
    Outline,
    Project,
    Template,
    TemplateTextSlot,
    UsageEvent,
)


@dataclass(frozen=True)
class DeckBuildPlan:
    replacements: list[TextReplacement]
    warnings: list[dict[str, str]]


def build_project_deck(
    db: Session,
    *,
    project_id: uuid.UUID,
    template_id: uuid.UUID,
    settings: Settings,
) -> GeneratedDeck:
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("사업 카드를 찾을 수 없습니다.")

    template = db.get(Template, template_id)
    if template is None:
        raise ValueError("템플릿을 찾을 수 없습니다.")
    if template.status != "analyzed":
        raise ValueError("분석이 끝난 템플릿만 사용할 수 있습니다.")

    document = db.get(Document, template.document_id)
    if document is None:
        raise ValueError("템플릿 원본 문서를 찾을 수 없습니다.")

    bid_context = db.scalar(
        select(BidContext)
        .where(BidContext.project_id == project_id)
        .order_by(BidContext.created_at.desc())
    )
    notice_context = db.scalar(
        select(NoticeContext)
        .where(NoticeContext.project_id == project_id)
        .order_by(NoticeContext.created_at.desc())
    )
    outline = db.scalar(
        select(Outline)
        .where(Outline.project_id == project_id)
        .order_by(Outline.created_at.desc())
    )
    slots = list(
        db.scalars(
            select(TemplateTextSlot)
            .where(TemplateTextSlot.template_id == template_id)
            .order_by(TemplateTextSlot.slide_index, TemplateTextSlot.shape_id)
        ).all()
    )

    context = _build_context(project, bid_context, notice_context, outline)
    plan = create_deck_build_plan(slots, context)
    deck_id = uuid.uuid4()
    safe_title = _safe_filename(project.name)
    output_path = settings.outputs_dir / f"{deck_id}_{safe_title}.pptx"
    apply_report = apply_text_replacements(
        Path(document.stored_path),
        output_path,
        plan.replacements,
    )

    deck = GeneratedDeck(
        id=deck_id,
        project_id=project_id,
        template_id=template_id,
        outline_id=outline.id if outline else None,
        title=f"{project.name} 제안서 초안",
        status="ready",
        output_path=str(output_path),
        report={
            "mode": "local_text_only",
            "applied_slots": apply_report.applied,
            "skipped_slots": apply_report.skipped,
            "warnings": plan.warnings,
            "replacement_count": len(plan.replacements),
        },
    )
    db.add(deck)
    db.add(
        UsageEvent(
            event="build_deck",
            payload={
                "project_id": str(project_id),
                "template_id": str(template_id),
                "deck_id": str(deck_id),
                "replacement_count": len(plan.replacements),
            },
        )
    )
    db.commit()
    db.refresh(deck)
    return deck


def create_deck_build_plan(
    slots: list[TemplateTextSlot],
    context: dict[str, Any],
) -> DeckBuildPlan:
    replacements: list[TextReplacement] = []
    warnings: list[dict[str, str]] = []
    first_cover_slot_id: uuid.UUID | None = None

    for slot in slots:
        if slot.locked or slot.value_type == "fixed":
            continue
        if first_cover_slot_id is None and slot.slide_index == 1 and slot.kind != "notes":
            first_cover_slot_id = slot.id

    for slot in slots:
        text: str | None = None
        source = ""
        if slot.locked or slot.value_type == "fixed":
            continue

        if slot.field_binding:
            text = _resolve_path(context, slot.field_binding)
            source = f"field_binding:{slot.field_binding}"
            if text is None:
                warnings.append(
                    {
                        "slot_id": str(slot.id),
                        "shape_id": slot.shape_id,
                        "message": "field_binding 값을 찾지 못했습니다.",
                    }
                )
                continue
        elif _looks_project_title_slot(slot) or slot.id == first_cover_slot_id:
            text = _resolve_path(context, "project_card.name")
            source = "auto:project_title"
        elif _looks_agency_slot(slot):
            text = _resolve_path(context, "project_card.agency")
            source = "auto:agency"
        elif _looks_budget_slot(slot):
            text = _format_budget(_resolve_raw(context, "bid_context.bid.budget"))
            source = "auto:budget"
        elif _looks_requirement_slot(slot):
            text = _requirements_text(context)
            source = "auto:requirements"

        if text is None or text == "":
            continue

        replacements.append(
            TextReplacement(
                slide_index=slot.slide_index,
                shape_id=slot.shape_id,
                text=_fit_text(str(text), slot.max_char_count),
            )
        )
        if len(str(text)) > slot.max_char_count:
            warnings.append(
                {
                    "slot_id": str(slot.id),
                    "shape_id": slot.shape_id,
                    "message": f"{source} 값이 권장 글자 수를 넘어 잘랐습니다.",
                }
            )

    if not replacements:
        warnings.append(
            {
                "slot_id": "",
                "shape_id": "",
                "message": (
                    "치환할 슬롯이 없습니다. 템플릿 슬롯 이름이나 "
                    "field_binding을 지정해주세요."
                ),
            }
        )

    return DeckBuildPlan(replacements=replacements, warnings=warnings)


def _build_context(
    project: Project,
    bid_context: BidContext | None,
    notice_context: NoticeContext | None,
    outline: Outline | None,
) -> dict[str, Any]:
    bid_data = bid_context.data if bid_context else {}
    notice_data = {
        "raw_text": notice_context.raw_text if notice_context else "",
        "requirements": notice_context.requirements if notice_context else [],
        "scoring_items": notice_context.scoring_items if notice_context else [],
        "summary": notice_context.summary if notice_context else {},
    }
    return {
        "project_card": {
            "name": project.name,
            "agency": project.agency,
            "domain": project.domain,
            "year": project.year,
            "stage": project.stage,
            "notes": project.notes,
        },
        "bid_context": bid_data,
        "notice_context": notice_data,
        "outline": {"items": outline.items if outline else []},
    }


def _resolve_path(context: dict[str, Any], path: str) -> str | None:
    value = _resolve_raw(context, path)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(_short_item(item) for item in value[:5])
    if isinstance(value, dict):
        return "\n".join(f"{key}: {value[key]}" for key in list(value)[:5])
    return str(value)


def _resolve_raw(context: dict[str, Any], path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _looks_project_title_slot(slot: TemplateTextSlot) -> bool:
    key = _slot_key(slot)
    return any(token in key for token in ("project_name", "bid_name", "title", "cover_title"))


def _looks_agency_slot(slot: TemplateTextSlot) -> bool:
    key = _slot_key(slot)
    return any(token in key for token in ("agency", "org", "client", "demand"))


def _looks_budget_slot(slot: TemplateTextSlot) -> bool:
    key = _slot_key(slot)
    return "budget" in key or "amount" in key


def _looks_requirement_slot(slot: TemplateTextSlot) -> bool:
    key = _slot_key(slot)
    return "requirement" in key or "requirements" in key


def _slot_key(slot: TemplateTextSlot) -> str:
    return " ".join(
        [
            slot.slot_name or "",
            slot.role_key or "",
            slot.original_text or "",
        ]
    ).lower()


def _requirements_text(context: dict[str, Any]) -> str:
    requirements = _resolve_raw(context, "notice_context.requirements") or []
    if not isinstance(requirements, list):
        return ""
    lines = []
    for index, item in enumerate(requirements[:5], start=1):
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or item.get("detail")
        else:
            title = str(item)
        if title:
            lines.append(f"{index}. {title}")
    return "\n".join(lines)


def _short_item(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("name", "title", "taskName", "personName"):
            if key in item and item[key]:
                return str(item[key])
    return str(item)


def _format_budget(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return str(value)
    if amount >= 100_000_000:
        return f"{amount // 100_000_000:,}억원"
    if amount >= 10_000:
        return f"{amount // 10_000:,}만원"
    return f"{amount:,}원"


def _fit_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."


def _safe_filename(value: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]+', " ", value).strip()
    return safe[:60] or "proposal"
