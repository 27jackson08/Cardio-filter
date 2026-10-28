import pytest

from cardiofilter import dataset

INDEX = (
    "Patient ID,Recording locations:,Age,Sex\n"
    "2530,AV+PV+TV+MV,Child,Female\n"
    "9979,AV+MV,Child,Female\n"
    ",AV,Child,Male\n"
    "1111,AV+AV,Child,Male\n"
)


def test_parse_index_and_plan_files():
    entries = dataset.parse_index(INDEX)
    assert entries == [
        ("2530", ("AV", "PV", "TV", "MV")),
        ("9979", ("AV", "MV")),
        ("1111", ("AV",)),
    ]
    files = dataset.plan_files(entries[1:2])
    assert files == [
        "9979.txt",
        "9979_AV.wav",
        "9979_AV.tsv",
        "9979_AV.hea",
        "9979_MV.wav",
        "9979_MV.tsv",
        "9979_MV.hea",
    ]


def test_download_subset_uses_fetch_and_resumes(tmp_path):
    calls = []

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        if url.endswith("training_data.csv"):
            return INDEX.encode()
        if url.endswith("2530_PV.wav"):
            raise OSError("404")
        return b"payload"

    messages = []
    written = dataset.download_subset(
        tmp_path, n_subjects=1, fetch_fn=fake_fetch, progress=messages.append
    )
    names = sorted(p.name for p in written)
    assert "2530.txt" in names and "2530_AV.wav" in names and "2530_PV.wav" not in names
    assert any(m.startswith("skip 2530_PV.wav") for m in messages)
    assert all(u.startswith(dataset.PHYSIONET_BASE) for u in calls)
    # resuming downloads nothing new
    assert dataset.download_subset(tmp_path, n_subjects=1, fetch_fn=fake_fetch) == []
    # None means every subject
    all_written = dataset.download_subset(tmp_path, n_subjects=None, fetch_fn=fake_fetch)
    assert any(p.name == "1111_AV.wav" for p in all_written)


def test_download_subset_validation(tmp_path):
    with pytest.raises(ValueError):
        dataset.download_subset(tmp_path, n_subjects=0, fetch_fn=lambda u: b"")
    with pytest.raises(ValueError):
        dataset.fetch("http://physionet.org/x")
