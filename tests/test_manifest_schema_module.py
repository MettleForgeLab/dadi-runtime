def test_manifest_validator_import():
    import services.gateway.dadi_gateway.manifest_validator as mv
    assert hasattr(mv, "validate_deliverable_manifest")
