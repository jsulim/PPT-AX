from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from core.hwpx.fill import (
    build_cell_fills,
    build_personnel_profile_fills,
    build_repeating_fills,
    fill_hwpx_cells,
)
from core.hwpx.mapping import infer_label_mappings
from core.hwpx.read import form_text, read_hwpx
from core.hwpx.trim import trim_hwpx_to_form_start

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
        "company.business_no",
        "bid.name",
    }
    assert any(item["field_key"] == "company.business_no" for item in missing)
    assert len(report.filled) == len(fills)
    assert "인트윈" in filled.text
    assert "기존값" in filled.text
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
    assert "김기획" in filled.text
    consent_tables = [
        table
        for table in filled.tables
        if any("개인정보 수집 이용 동의서" in cell.text for row in table.rows for cell in row)
    ]
    assert len(consent_tables) == 1
    assert any(item["reason"] == "not_enough_blank_rows" for item in report.skipped)
    assert len(report.filled) >= 8


def test_fuzzy_label_and_header_matching(tmp_path: Path) -> None:
    input_path = tmp_path / "fuzzy.hwpx"
    output_path = tmp_path / "filled.hwpx"
    _write_hwpx(input_path, FUZZY_SECTION_XML)

    document = read_hwpx(input_path)
    mappings = infer_label_mappings(document)
    fills, missing = build_cell_fills(
        mappings,
        {
            "company": {"name": "인트윈"},
            "bid": {"name": "지역 관광 활성화 운영 용역"},
        },
    )
    table_rows, repeated_tables, repeat_missing = build_repeating_fills(
        document,
        {
            "track_records": [
                {
                    "taskName": "로컬 브랜드 캠페인",
                    "org": "C군",
                    "amountRaw": "30,000,000",
                    "desc": "홍보 콘텐츠 제작",
                }
            ],
            "personnel": [
                {"name": "최전략", "dept": "사업팀", "position": "총괄", "career": "10년"}
            ],
        },
    )

    report = fill_hwpx_cells(
        input_path,
        output_path,
        fills,
        table_rows=table_rows,
        repeated_tables=repeated_tables,
    )
    filled = read_hwpx(output_path)

    assert not missing
    assert not repeat_missing
    assert "인트윈" in filled.text
    assert "지역 관광 활성화 운영 용역" in filled.text
    assert "로컬 브랜드 캠페인" in filled.text
    assert "홍보 콘텐츠 제작" in filled.text
    assert "최전략" in filled.text
    assert "총괄" in filled.text
    assert report.filled


def test_trim_hwpx_to_form_start_removes_notice_pages(tmp_path: Path) -> None:
    input_path = tmp_path / "form.hwpx"
    _write_hwpx(input_path)

    assert trim_hwpx_to_form_start(input_path)

    trimmed = read_hwpx(input_path)
    assert "공고문 안내 내용" not in trimmed.text
    assert "별지 제1호 서식" in trimmed.text
    assert "입찰참가신청서" not in trimmed.text


def test_fill_repeats_personnel_profile_blocks(tmp_path: Path) -> None:
    input_path = tmp_path / "profile.hwpx"
    output_path = tmp_path / "filled.hwpx"
    _write_hwpx(input_path, PERSONNEL_PROFILE_SECTION_XML)

    document = read_hwpx(input_path)
    profiles, missing = build_personnel_profile_fills(
        document,
        {
            "company": {"name": "인트윈"},
            "personnel": [
                {
                    "name": "김기획",
                    "dept": "전략팀",
                    "age": "35",
                    "position": "PM",
                    "career": "8년",
                    "eduSchool": "한국대학교",
                    "eduMajor": "경영학",
                    "role": "총괄",
                    "participationPeriod": "2026.10~2027.01",
                    "participationRate": "50",
                },
                {
                    "name": "이운영",
                    "dept": "운영팀",
                    "age": "32",
                    "position": "PL",
                    "career": "6년",
                    "eduSchool": "서울대학교",
                    "eduMajor": "행정학",
                    "role": "운영",
                    "participationPeriod": "2026.10~2027.01",
                    "participationRate": "40",
                },
            ],
        },
    )

    report = fill_hwpx_cells(input_path, output_path, [], personnel_profiles=profiles)
    filled = read_hwpx(output_path)

    assert not missing
    assert "김기획" in filled.text
    assert "이운영" in filled.text
    assert filled.text.count("【별지 제11호 서식】 참여인력 이력사항") == 2
    assert filled.text.count("상호 또는 법인명 : 인트윈") == 2
    assert "[확인 필요: personnel.certifications]" not in filled.text
    assert any("personnel.name@profile:1" in item for item in report.filled)



PERSONNEL_PROFILE_SECTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>공고문 본문</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:t>【별지 제11호 서식】 참여인력 이력사항</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:t>참여인력 이력사항</hp:t></hp:run></hp:p>
  <hp:p>
    <hp:tbl>
      <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>성 명</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>소 속</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>연 령</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>직 위</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>학 력</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>대학교</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>전공</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>해당분야 근무경력</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>년      개월</hp:t></hp:run></hp:p></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>대학원</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>전공</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>자 격 증</hp:t></hp:run></hp:p></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>본 용역
참여 업무</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>본 용역
참여 기간</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>2026.  .   .
～ 2027.  .   .</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>참여율</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>%</hp:t></hp:run></hp:p></hp:tc>
      </hp:tr>
      <hp:tr><hp:tc><hp:p><hp:run/></hp:p></hp:tc></hp:tr>
      <hp:tr><hp:tc><hp:p><hp:run><hp:t>경    력    사    항</hp:t></hp:run></hp:p></hp:tc></hp:tr>
      <hp:tr>
        <hp:tc><hp:p><hp:run><hp:t>사업명</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>참여기간
(연월～연월)</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>담당업무</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>근무처</hp:t></hp:run></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run><hp:t>비고</hp:t></hp:run></hp:p></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
        <hp:tc><hp:p><hp:run/></hp:p></hp:tc>
      </hp:tr>
    </hp:tbl>
  </hp:p>
  <hp:p><hp:run><hp:t>상호 또는 법인명 :                   (인)</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:t>【별지 제12호 서식】 행정처분 확인서</hp:t></hp:run></hp:p>
</hp:sec>
"""


FUZZY_SECTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>법 인 명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>프로젝트명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>순번</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>프로젝트명</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>기관</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>사업비</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>수행내용</hp:t></hp:run></hp:p></hp:tc>
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
      <hp:tc><hp:p><hp:run><hp:t>투입인력</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>담당업무</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>실무경력</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
</hp:sec>
"""


def _write_hwpx(path: Path, section_xml: str = SECTION_XML) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Contents/section0.xml", section_xml)
        archive.writestr("mimetype", "application/hwp+zip")
