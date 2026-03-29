from app.cache_policy import (
    CacheKeyContext,
    classify_cache_policy,
    direct_answer_cache_key,
    is_casual_query,
    search_answer_cache_key,
    search_results_cache_key,
)


def test_classify_critical_market_query():
    assert (
        classify_cache_policy("What is the current EUR/USD rate?") == "critical_market"
    )


def test_classify_direct_knowledge_query():
    assert classify_cache_policy("What is diversification?") == "direct_knowledge"


def test_classify_casual_query_as_direct_knowledge():
    assert classify_cache_policy("How are you?") == "direct_knowledge"
    assert classify_cache_policy("greetings") == "direct_knowledge"


def test_classify_search_noncritical_query():
    assert (
        classify_cache_policy("Summarize last week ECB regulatory updates")
        == "search_noncritical"
    )


def test_classify_uncertain_defaults_to_critical():
    assert classify_cache_policy("Tell me something about markets") == "critical_market"


def test_cache_keys_are_stable():
    ctx = CacheKeyContext(model="qwen2.5:7b", prompt_revision="v1")
    direct_key = direct_answer_cache_key("What is diversification?", ctx)
    search_answer_key = search_answer_cache_key("Summarize last week Fed updates", ctx)
    search_results_key = search_results_cache_key("Summarize last week Fed updates")

    assert direct_key.startswith("agent:direct:v1:")
    assert search_answer_key.startswith("agent:search_answer:v1:")
    assert search_results_key.startswith("agent:search_results:v1:")


def test_is_casual_query_positive_and_negative_cases():
    assert is_casual_query("hello")
    assert is_casual_query("Good morning!")
    assert is_casual_query("what's up?")
    assert not is_casual_query("What is the current EUR/USD?")
