def test_rate_limit_redis_import():
    import services.gateway.dadi_gateway.rate_limit_redis as rlr
    assert hasattr(rlr, "RateLimitRedisMiddleware")
