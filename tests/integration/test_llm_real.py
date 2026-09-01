import pytest


pytestmark = pytest.mark.model


@pytest.mark.skip(reason="requires an OpenAI-compatible translation endpoint")
def test_llm_real_smoke():
    pass
