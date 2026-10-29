import pytest
from pydantic import ValidationError

from app.security.schemas import (Category, Decision, SecurityVerdict, Stage, combine)


def make(decision=Decision.ALLOW, **kw):
    base = dict(stage=Stage.PRE_RETRIEVAL, decision=decision, score=0.1, detector="rules")
    base.update(kw)
    return SecurityVerdict(**base)


def test_api_output_is_camel_case():
    out = make(Decision.BLOCK, category=Category.PROMPT_INJECTION, latency_ms=4.2).model_dump(by_alias=True)
    assert out["latencyMs"] == 4.2
    assert out["chunkId"] is None
    assert out["source"] == "security"
    assert "latency_ms" not in out


def test_accepts_snake_and_camel_input():
    assert make(latency_ms=3).latency_ms == 3
    assert SecurityVerdict(stage="pre_response", decision="FLAG", score=0.5,
                           detector="links", latencyMs=7).latency_ms == 7


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_score_must_be_between_0_and_1(bad):
    with pytest.raises(ValidationError):
        make(score=bad)


def test_detector_name_required():
    with pytest.raises(ValidationError):
        make(detector="")


def test_verdict_is_immutable():
    v = make()
    with pytest.raises(ValidationError):
        v.decision = Decision.BLOCK


def test_combine_empty_is_allow():
    r = combine([])
    assert r.final_decision is Decision.ALLOW and not r.blocked


def test_combine_takes_most_severe():
    r = combine([make(Decision.ALLOW), make(Decision.FLAG), make(Decision.BLOCK), make(Decision.FLAG)])
    assert r.final_decision is Decision.BLOCK and r.blocked


def test_combine_flag_does_not_block():
    r = combine([make(Decision.ALLOW), make(Decision.FLAG)])
    assert r.final_decision is Decision.FLAG and not r.blocked


def test_block_on_one_chunk_drops_it_and_does_not_block_request():
    chunk = make(Decision.BLOCK, stage=Stage.POST_RETRIEVAL, chunk_id="c1",
                 category=Category.INDIRECT_INJECTION)
    assert chunk.dropped_chunk and not chunk.blocks_request
    r = combine([chunk])
    assert r.final_decision is Decision.FLAG and not r.blocked


def test_block_at_post_retrieval_without_chunk_id_blocks_request():
    v = make(Decision.BLOCK, stage=Stage.POST_RETRIEVAL)
    assert not v.dropped_chunk and v.blocks_request
    assert combine([v]).blocked


def test_block_at_pre_response_blocks_request():
    v = make(Decision.BLOCK, stage=Stage.PRE_RESPONSE)
    assert v.blocks_request and combine([v]).blocked


def test_dropped_chunk_plus_input_block_still_blocks():
    chunk = make(Decision.BLOCK, stage=Stage.POST_RETRIEVAL, chunk_id="c1")
    assert combine([chunk, make(Decision.BLOCK)]).blocked
