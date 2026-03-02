def test_streaming_utils_import():
    import services.gateway.dadi_gateway.streaming_utils as su
    assert hasattr(su, "stream_bytes")
