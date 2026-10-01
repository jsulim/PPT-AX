from app.schemas.integrations import WorkProveImportRequest
from app.services.work_prove import import_work_prove_payload


class FakeSession:
    def __init__(self) -> None:
        self.objects: list[object] = []

    def add(self, value: object) -> None:
        self.objects.append(value)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        return None

    def refresh(self, value: object) -> None:
        return None


def test_import_work_prove_payload_splits_contexts() -> None:
    payload = WorkProveImportRequest.model_validate(
        {
            "bid": {
                "no": "20261001001",
                "ord": "00",
                "name": "지역 관광 활성화 운영 용역",
                "noticeOrg": "공고기관",
                "demandOrg": "수요기관",
                "budget": 100000000,
            },
            "notice": {
                "bodyText": "과업지시서 본문",
                "requirements": [{"req_id": "R1", "title": "운영계획"}],
                "scoringItems": [{"key": "S1", "name": "수행계획", "points": 30}],
                "forms": [{"no": "1", "name": "입찰참가신청서"}],
                "qualifications": [{"text": "유사용역 실적"}],
            },
            "company": {"name": "인트윈"},
            "selectedPersonnel": [{"name": "홍길동"}],
            "selectedTrackRecords": [{"taskName": "관광 행사"}],
            "outlineItems": [{"scoring_item_key": "S1", "slide_type_key": "method_detail"}],
            "userEmail": "user@example.com",
        }
    )
    db = FakeSession()

    project, notice_context, bid_context, outline = import_work_prove_payload(db, payload)  # type: ignore[arg-type]

    assert project.name == "지역 관광 활성화 운영 용역"
    assert project.agency == "수요기관"
    assert notice_context.raw_text == "과업지시서 본문"
    assert notice_context.requirements[0]["req_id"] == "R1"
    assert bid_context.data["bid"]["name"] == "지역 관광 활성화 운영 용역"
    assert bid_context.data["selected_personnel"] == [{"name": "홍길동"}]
    assert outline.items[0]["slide_type_key"] == "method_detail"
    assert len(db.objects) == 5
