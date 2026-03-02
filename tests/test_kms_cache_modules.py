def test_kms_pubkey_cache_import():
    import services.gateway.dadi_gateway.kms_public_key_cache as kc
    assert hasattr(kc, "KMS_PUBKEY_CACHE")

def test_health_extra_import():
    import services.gateway.dadi_gateway.health_extra as hx
    assert hasattr(hx, "router")
