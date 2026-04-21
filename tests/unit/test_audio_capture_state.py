from local_meeting_notes.audio_capture.state import read_capture_state, write_capture_state


def test_capture_state_round_trip(local_tmp_dir) -> None:
    path = local_tmp_dir / "audio_capture_state.json"
    payload = {
        "capture_id": "capture-1234",
        "status": "running",
        "output_dir": str(local_tmp_dir / "audio"),
    }

    write_capture_state(path, payload)
    loaded = read_capture_state(path)

    assert loaded == payload
