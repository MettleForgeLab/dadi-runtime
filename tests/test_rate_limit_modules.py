def test_rate_limit_module_import():
    import services.gateway.dadi_gateway.rate_limit as rl
    assert hasattr(rl, "RateLimitMiddleware")

def test_request_size_limit_module_import():
    import services.gateway.dadi_gateway.request_size_limit as sl
    assert hasattr(sl, "RequestSizeLimitMiddleware")
