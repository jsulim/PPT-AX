from app.services.form_jobs import (
    HwpxFormJob,
    list_hwpx_form_jobs,
    read_hwpx_form_job,
    write_hwpx_form_job,
)


def test_write_list_and_read_hwpx_form_job(tmp_path) -> None:
    job = HwpxFormJob(
        job_id="job-1",
        created_at="2026-10-03T00:00:00+00:00",
        source_filename="gicon.hwpx",
        original_filename="abc.hwpx",
        output_filename="job-1.hwpx",
        download_url="/forms/hwpx/outputs/job-1.hwpx",
        filled=["company.name@cell"],
        missing=[{"field_key": "company.email", "message": "missing"}],
        skipped=[{"reason": "not_enough_blank_rows"}],
        mappings=[{"field_key": "company.name", "cell_ref": "section.xml:tbl0:r0:c1"}],
        trim_applied=True,
    )

    job_path = write_hwpx_form_job(tmp_path, job)

    assert job_path.exists()
    assert [item.job_id for item in list_hwpx_form_jobs(tmp_path)] == ["job-1"]
    loaded = read_hwpx_form_job(tmp_path, "job-1")
    assert loaded is not None
    assert loaded.filled_count == 1
    assert loaded.missing_count == 1
    assert loaded.skipped_count == 1
    assert loaded.trim_applied


def test_read_hwpx_form_job_rejects_path_segments(tmp_path) -> None:
    assert read_hwpx_form_job(tmp_path, "../job-1") is None
