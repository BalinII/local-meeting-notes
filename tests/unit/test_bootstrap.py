from local_meeting_notes.bootstrap import bootstrap_application


def test_bootstrap_registers_placeholder_services() -> None:
    app_state = bootstrap_application()

    assert "meeting_detector" in app_state.services
    assert "audio_capture" in app_state.services
    assert "export_service" in app_state.services
