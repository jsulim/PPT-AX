from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from core.hwpx.fill import build_cell_fills, build_repeating_fills, fill_hwpx_cells
from core.hwpx.mapping import infer_label_mappings
from core.hwpx.read import form_text, read_hwpx

SECTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>공고문 안내 내용</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:t>별지 제1호 서식</hp:t></hp:run></hp:p>
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>상호</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>대표자</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>기존값</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>사업자등록번호</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>사업명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>연번</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>사업명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>발주처</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>계약금액</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>계약기간</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>번호</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>성명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>소속</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>직위</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>경력</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>개인정보 수집 이용 동의서</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>성명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>소속</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>직위</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
</hp:sec>
"""


def test_read_map_and_fill_hwpx_cells(tmp_path: Path) -> None:
    input_path = tmp_path / "form.hwpx"
    output_path = tmp_path / "filled.hwpx"
    _write_hwpx(input_path)

    document = read_hwpx(input_path)
    mappings = infer_label_mappings(document)
    fills, missing = build_cell_fills(
        mappings,
        {
            "company": {
                "name": "인트윈",
                "ceo_name": "홍길동",
            },
            "bid": {
                "name": "GICON 마케팅 Impact 프로그램 운영",
            },
        },
    )

    report = fill_hwpx_cells(input_path, output_path, fills)
    filled = read_hwpx(output_path)

    assert "별지 제1호 서식" in form_text(document)
    assert {mapping.field_key for mapping in mappings} >= {
        "company.name",
        "company.ceo_name",
        "company.business_no",
        "bid.name",
    }
    assert any(item["field_key"] == "company.business_no" for item in missing)
    assert len(report.filled) == len(fills)
    assert "인트윈" in filled.text
    assert "홍길동" in filled.text
    assert "GICON 마케팅 Impact 프로그램 운영" in filled.text
    assert "[확인 필요: company.business_no]" in filled.text


def test_fill_repeating_track_records_personnel_and_consent(tmp_path: Path) -> None:
    input_path = tmp_path / "form.hwpx"
    output_path = tmp_path / "filled.hwpx"
    _write_hwpx(input_path)

    document = read_hwpx(input_path)
    table_rows, repeated_tables, missing = build_repeating_fills(
        document,
        {
            "track_records": [
                {
                    "taskName": "관광 활성화 캠페인",
                    "org": "A시",
                    "amountRaw": "50,000,000",
                    "contractPeriod": "2025.01~2025.03",
                },
                {
                    "taskName": "지역 축제 운영",
                    "org": "B재단",
                    "amountRaw": "70,000,000",
                    "contractPeriod": "2024.05~2024.06",
                },
            ],
            "personnel": [
                {"name": "김기획", "dept": "전략팀", "position": "PM", "career": "8년"},
                {"name": "이운영", "dept": "운영팀", "position": "PL", "career": "6년"},
                {"name": "박홍보", "dept": "홍보팀", "position": "매니저", "career": "4년"},
            ],
        },
    )

    report = fill_hwpx_cells(
        input_path,
        output_path,
        [],
        table_rows=table_rows,
        repeated_tables=repeated_tables,
    )
    filled = read_hwpx(output_path)

    assert not missing
    assert "관광 활성화 캠페인" in filled.text
    assert "지역 축제 운영" in filled.text
    assert "김기획" in filled.text
    assert "이운영" in filled.text
    assert "박홍보" in filled.text
    consent_tables = [
        table
        for table in filled.tables
        if any("개인정보 수집 이용 동의서" in cell.text for row in table.rows for cell in row)
    ]
    assert len(consent_tables) == 3
    assert len(report.filled) >= 8


def _write_hwpx(path: Path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Contents/section0.xml", SECTION_XML)
        archive.writestr("mimetype", "application/hwp+zip")
