import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List

LEADERBOARD_FILE = Path("leaderboard.json")

@dataclass
class ScoreEntry:
    name: str
    score: int
    puzzle_id: int

def load_leaderboard() -> List[ScoreEntry]:
    if not LEADERBOARD_FILE.exists():
        return []
    try:
        data = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
        return [ScoreEntry(**entry) for entry in data]
    except Exception:
        return []

def save_score(name: str, score: int, puzzle_id: int) -> None:
    scores = load_leaderboard()
    scores.append(ScoreEntry(name=name, score=score, puzzle_id=puzzle_id))
    # Sort by score descending
    scores.sort(key=lambda x: x.score, reverse=True)
    # Keep top 100
    scores = scores[:100]
    LEADERBOARD_FILE.write_text(json.dumps([asdict(s) for s in scores], indent=2), encoding="utf-8")

def get_top_scores(limit: int = 10) -> List[ScoreEntry]:
    scores = load_leaderboard()
    return scores[:limit]
