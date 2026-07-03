"""구조화 결과 정규화(_normalize) 유닛 테스트"""
from app.services.resume.structurer import _DEFAULT_STRUCTURE, _normalize


def test_normalize_fills_missing_keys():
    out = _normalize({"skills": ["Python", "FastAPI"]})
    assert out["skills"] == ["Python", "FastAPI"]
    assert out["education"] == {}
    assert out["career"] == {}
    assert out["projects"] == []
    assert out["self_introduction"] == {}
    assert out["desired_position"] == {}


def test_normalize_replaces_wrong_types_with_defaults():
    out = _normalize({"skills": "Python", "projects": {"name": "단일 객체"}})
    assert out["skills"] == []
    assert out["projects"] == []


def test_normalize_drops_unknown_keys():
    out = _normalize({"skills": [], "unknown_field": "값"})
    assert set(out.keys()) == set(_DEFAULT_STRUCTURE.keys())
