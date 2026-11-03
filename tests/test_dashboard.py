from streamlit.testing.v1 import AppTest


def test_dashboard_renders_without_exceptions(monkeypatch):
    import os
    monkeypatch.setenv('DB_USER', 'reporter')
    monkeypatch.setenv('DB_PASSWORD', os.environ['REPORTER_PASSWORD'])
    app = AppTest.from_file('dashboard/app.py').run(timeout=20)
    assert not app.exception
    assert not app.error


def test_dashboard_filters_and_failed_run_notice(monkeypatch, process, tiny, datasets):
    import os
    process(tiny)
    process(datasets/'missing_finance')
    monkeypatch.setenv('DB_USER', 'reporter')
    monkeypatch.setenv('DB_PASSWORD', os.environ['REPORTER_PASSWORD'])
    app = AppTest.from_file('dashboard/app.py').run(timeout=20)
    assert not app.exception and not app.error
    assert 'previous successful version' in app.warning[0].value
    assert [m.value for m in app.metric] == ['$175.00','1','$175.00','$175.00','$0.00']
    app.sidebar.selectbox[0].set_value(__import__('datetime').date(2026,1,1)).run()
    assert app.metric[0].value == '$250.00'
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.error and not app.exception
    assert [m.value for m in app.metric] == ['$250.00','$250.00','$0.00']
