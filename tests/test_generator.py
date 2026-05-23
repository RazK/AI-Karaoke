import json
import os
import shutil
from pathlib import Path
import pytest
from generate.generator import generate

FIXTURE_LRC = Path(__file__).parent / "fixtures" / "lrc_fixture.json"
FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus_fixture.txt"

# Matches fixture syllable counts: line0=6, line1=6, line2=8
# (pyphen counts "real" as "re-al" = 2 syllables)
MOCK_VALID = json.dumps([
    {"generated": [["As", "sem"], ["ble"], ["shelf"], ["right"], ["now"]]},     # 2+1+1+1+1 = 6
    {"generated": [["Check"], ["the"], ["di", "a", "gram"], ["now"]]},          # 1+1+3+1 = 6
    {"generated": [["In", "sert"], ["screw"], ["type"], ["A"], ["care", "ful", "ly"]]},  # 2+1+1+1+3 = 8
])

MOCK_BAD_COUNT = json.dumps([
    {"generated": [["Fix"], ["the"], ["shelf"]]},  # 3 ≠ 6
    {"generated": [["Check"], ["the"], ["now"]]},  # 3 ≠ 6
    {"generated": [["In", "sert"], ["screw"]]},    # 3 ≠ 8
])


def _setup_data_dir(tmp_path: Path, song_id="test-song", dataset_id="test-dataset") -> Path:
    data_dir = tmp_path / "data"
    (data_dir / "lrc").mkdir(parents=True)
    (data_dir / "datasets").mkdir()
    shutil.copy(FIXTURE_LRC, data_dir / "lrc" / f"{song_id}.json")
    shutil.copy(FIXTURE_CORPUS, data_dir / "datasets" / f"{dataset_id}.txt")
    return data_dir


def test_generate_returns_correct_shape(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    result = generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=lambda p: MOCK_VALID)
    assert result["songId"] == "test-song"
    assert result["datasetId"] == "test-dataset"
    assert len(result["lines"]) == 3


def test_generate_lines_have_required_fields(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    result = generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=lambda p: MOCK_VALID)
    for line in result["lines"]:
        assert "startMs" in line
        assert "original" in line
        assert "generated" in line


def test_syllable_counts_match_in_output(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    result = generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=lambda p: MOCK_VALID)
    for line in result["lines"]:
        orig = sum(len(w) for w in line["original"])
        gen = sum(len(w) for w in line["generated"])
        assert orig == gen


def test_start_ms_preserved(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    result = generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=lambda p: MOCK_VALID)
    assert result["lines"][0]["startMs"] == 0
    assert result["lines"][1]["startMs"] == 4000
    assert result["lines"][2]["startMs"] == 8000


def test_max_lines_respected(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    result = generate("test-song", "test-dataset", data_dir=str(data_dir), max_lines=2, _call_fn=lambda p: json.dumps([
        {"generated": [["As", "sem"], ["ble"], ["shelf"], ["right"], ["now"]]},  # 6
        {"generated": [["Check"], ["the"], ["di", "a", "gram"], ["now"]]},       # 6
    ]))
    assert len(result["lines"]) == 2


def test_retry_on_bad_response(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    call_count = [0]

    def mock_call(prompt):
        call_count[0] += 1
        return MOCK_VALID if call_count[0] >= 2 else MOCK_BAD_COUNT

    result = generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=mock_call)
    assert call_count[0] == 2
    assert len(result["lines"]) == 3


def test_raises_after_max_retries(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    with pytest.raises(RuntimeError, match="Generation failed"):
        generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=lambda p: MOCK_BAD_COUNT)


def test_retry_passes_error_hint(tmp_path):
    data_dir = _setup_data_dir(tmp_path)
    prompts = []

    def mock_call(prompt):
        prompts.append(prompt)
        return MOCK_VALID if len(prompts) >= 2 else MOCK_BAD_COUNT

    generate("test-song", "test-dataset", data_dir=str(data_dir), _call_fn=mock_call)
    assert "PREVIOUS ATTEMPT FAILED" in prompts[1]


# --- smoke / full tests (require --smoke / --full --yes and ANTHROPIC_API_KEY) ---

@pytest.mark.smoke
def test_smoke_africa_ikea():
    result = generate("africa", "ikea-manuals", data_dir="data", max_lines=3)
    assert len(result["lines"]) == 3
    for line in result["lines"]:
        orig = sum(len(w) for w in line["original"])
        gen = sum(len(w) for w in line["generated"])
        assert orig == gen, f"syllable mismatch: {orig} vs {gen}"


@pytest.mark.full
@pytest.mark.parametrize("song_id,dataset_id", [
    ("bohemian-rhapsody", "ikea-manuals"),
    ("bohemian-rhapsody", "yelp-reviews-1star"),
    ("someone-like-you", "ikea-manuals"),
    ("africa", "craigslist-ads"),
])
def test_full_acceptance(song_id, dataset_id):
    result = generate(song_id, dataset_id, data_dir="data")
    assert len(result["lines"]) > 0
    for line in result["lines"]:
        orig = sum(len(w) for w in line["original"])
        gen = sum(len(w) for w in line["generated"])
        assert orig == gen, f"[{song_id} × {dataset_id}] syllable mismatch on line startMs={line['startMs']}: {orig} vs {gen}"
