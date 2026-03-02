def test_evidence_validator_import():
    import services.gateway.dadi_gateway.evidence_validator as ev
    assert hasattr(ev, "validate_evidence_manifest")
