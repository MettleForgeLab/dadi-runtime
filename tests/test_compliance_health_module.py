def test_compliance_health_import():
    import services.gateway.dadi_gateway.compliance_health as ch
    assert hasattr(ch, "health_compliance")
