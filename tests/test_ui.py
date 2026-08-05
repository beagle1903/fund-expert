from fundexpert.ui import load_last_run_state, save_last_run_state

def test_load_save_last_run_state(tmp_path, monkeypatch):
    test_file = tmp_path / "last.json"
    import fundexpert.ui
    monkeypatch.setattr(fundexpert.ui, "LAST_RUN_FILE", test_file)
    
    # test empty
    assert load_last_run_state() == {}
    
    # test save
    state = {"universe": "tefas", "risk_level": "low"}
    save_last_run_state(state)
    assert load_last_run_state() == state
    
    # test invalid json
    test_file.write_text("{invalid")
    assert load_last_run_state() == {}

    # test OS error during save
    from unittest.mock import patch
    with patch("os.replace", side_effect=OSError):
        save_last_run_state(state)
