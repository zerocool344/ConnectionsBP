import json

import pytest

from puzzle_bank import PuzzleBankError, load_bank


def valid_bank_dict() -> dict:
    return {
        "launch_date": "2026-08-17",
        "puzzles": [
            {
                "id": 1,
                "groups": [
                    {"tier": 1, "name": "CENTRIFUGAL PUMP PARTS", "words": ["IMPELLER", "VOLUTE", "WEAR RING", "SHAFT SLEEVE"]},
                    {"tier": 2, "name": "VALVE TYPES", "words": ["GATE", "GLOBE", "BUTTERFLY", "CHECK"]},
                    {"tier": 3, "name": "___ SEAL", "words": ["MECHANICAL", "LABYRINTH", "LIP", "GLAND"]},
                    {"tier": 4, "name": "P&ID ABBREVIATIONS", "words": ["PSV", "FIC", "LT", "TE"]},
                ],
            }
        ],
    }


def write_bank(tmp_path, bank_dict):
    path = tmp_path / "puzzles.json"
    path.write_text(json.dumps(bank_dict), encoding="utf-8")
    return path


def test_loads_valid_bank(tmp_path):
    bank = load_bank(write_bank(tmp_path, valid_bank_dict()))
    assert bank.launch_date.isoformat() == "2026-08-17"
    assert len(bank.puzzles) == 1
    assert bank.puzzles[0].groups[0].name == "CENTRIFUGAL PUMP PARTS"


def test_rejects_wrong_group_count(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"].pop()
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_bad_tiers(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"][3]["tier"] = 2
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_wrong_word_count(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"][0]["words"].append("CASING")
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_duplicate_words_case_insensitive(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"][0]["words"][0] = "gate"
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_duplicate_puzzle_ids(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"].append(json.loads(json.dumps(bad["puzzles"][0])))
    with pytest.raises(PuzzleBankError, match="duplicate"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_bad_launch_date(tmp_path):
    bad = valid_bank_dict()
    bad["launch_date"] = "yesterday"
    with pytest.raises(PuzzleBankError, match="launch_date"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_empty_puzzle_list(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"] = []
    with pytest.raises(PuzzleBankError, match="at least one"):
        load_bank(write_bank(tmp_path, bad))
