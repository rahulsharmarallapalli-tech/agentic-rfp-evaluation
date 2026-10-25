import json
from unittest.mock import Mock
import pytest
import requests
from rfp.document import extract_pdf
from rfp.evaluator import GeminiEvaluator, ProviderError, build_prompt
from rfp.models import Supplier


def supplier():
    return Supplier(supplier_name="Apex Systems",submission_date="2026-10-20",experience_rating=8)


def test_provider_contract_and_key_not_in_payload(monkeypatch,criteria,proposal,raw):
    response=Mock(status_code=200)
    response.json.return_value={"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":json.dumps(raw)}]}}]}
    post=Mock(return_value=response)
    monkeypatch.setattr(requests,"post",post)
    client=GeminiEvaluator("test-only-key")
    result=client.evaluate(supplier(),criteria,extract_pdf(proposal))
    assert json.loads(result)==raw
    kwargs=post.call_args.kwargs
    assert kwargs["headers"]["x-goog-api-key"] == "test-only-key"
    assert "test-only-key" not in json.dumps(kwargs["json"])
    assert kwargs["timeout"] == (10,90)
    assert kwargs["allow_redirects"] is False
    assert kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "UNTRUSTED DATA" in build_prompt(supplier(),criteria,extract_pdf(proposal))


@pytest.mark.parametrize("status,retryable",[(401,False),(403,False),(400,False),(429,True),(503,True)])
def test_provider_status_handling(monkeypatch,criteria,proposal,status,retryable):
    monkeypatch.setattr(requests,"post",Mock(return_value=Mock(status_code=status)))
    with pytest.raises(ProviderError) as e:
        GeminiEvaluator("test-only-key").evaluate(supplier(),criteria,extract_pdf(proposal))
    assert e.value.retryable is retryable
    assert "test-only-key" not in str(e.value)


def test_network_error_is_sanitized(monkeypatch,criteria,proposal):
    monkeypatch.setattr(requests,"post",Mock(side_effect=requests.ConnectionError("secret internal detail")))
    with pytest.raises(ProviderError) as e:
        GeminiEvaluator("test-only-key").evaluate(supplier(),criteria,extract_pdf(proposal))
    assert "secret" not in str(e.value)
    assert e.value.retryable


@pytest.mark.parametrize("body",[{}, {"candidates":[]}, {"candidates":[{"finishReason":"MAX_TOKENS"}]}])
def test_blocked_or_incomplete_output(monkeypatch,criteria,proposal,body):
    response=Mock(status_code=200)
    response.json.return_value=body
    monkeypatch.setattr(requests,"post",Mock(return_value=response))
    with pytest.raises(ProviderError):
        GeminiEvaluator("test-only-key").evaluate(supplier(),criteria,extract_pdf(proposal))
