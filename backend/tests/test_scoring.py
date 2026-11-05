from app.agent.scoring import filter_known_originals, fit_score, missing_keywords, verdict
from app.schemas import Importance, MatchAssessment, MatchLevel, RequirementMatch, TailoredBullet
from tests.fakes import BULLET_1, MATCH, RESUME


def m(level, importance=Importance.must_have):
    return RequirementMatch(requirement="x", importance=importance, level=level)


def test_fit_score_weighting():
    # must strong (2) + must partial (1) + nice missing (0) out of 5 -> 60
    assert fit_score(MATCH) == 60
    assert verdict(60) == "stretch"


def test_all_strong_is_100():
    a = MatchAssessment(matches=[m(MatchLevel.strong), m(MatchLevel.strong, Importance.nice_to_have)])
    assert fit_score(a) == 100


def test_two_missing_must_haves_caps_score():
    a = MatchAssessment(
        matches=[m(MatchLevel.missing), m(MatchLevel.missing)]
        + [m(MatchLevel.strong, Importance.nice_to_have)] * 10
    )
    assert fit_score(a) <= 59


def test_empty_requirements():
    assert fit_score(MatchAssessment(matches=[])) == 0


def test_missing_keywords_uses_word_boundaries():
    missing = missing_keywords(["Python", "LangGraph", "Go", "FAISS"], RESUME)
    assert missing == ["LangGraph", "Go"]  # "Go" must not match inside other words


def test_filter_known_originals_drops_invented_source():
    ok = TailoredBullet(original=BULLET_1.upper(), rewritten="r")
    fake = TailoredBullet(original="Shipped a rocket", rewritten="r")
    kept, dropped = filter_known_originals([ok, fake], RESUME)
    assert kept == [ok] and dropped == [fake]
