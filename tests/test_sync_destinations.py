"""Incremental sync state belongs to the relay that received each bundle."""
from iris import library as L, sync as Y


def test_notes_are_sent_once_to_each_relay(tmp_path, monkeypatch):
    store = str(tmp_path)
    mid = L.new_note(store, 'One note')
    L.save_notes(store, mid, 'Destination-specific delivery')
    sent = []
    monkeypatch.setattr(Y, 'push', lambda sd, note, server, token: sent.append((note, server)))
    a, b = 'https://a.test/sync', 'https://b.test/sync'
    assert Y.push_changed(store, a, 't') == ([mid], [])
    assert Y.push_changed(store, b, 't') == ([mid], [])
    assert Y.push_changed(store, a, 't') == ([], [mid])
    assert Y.push_changed(store, b, 't') == ([], [mid])
    assert sent == [(mid, a), (mid, b)]


def test_folder_delivery_is_scoped_to_relay(tmp_path, monkeypatch):
    store = str(tmp_path)
    L.create_folder(store, 'Project')
    sent = []
    monkeypatch.setattr(Y, '_req', lambda url, token, payload: sent.append(url))
    assert Y.push_folders(store, 'https://a.test/sync', 't') is True
    assert Y.push_folders(store, 'https://b.test/sync', 't') is True
    assert Y.push_folders(store, 'https://a.test/sync', 't') is False
    assert Y.push_folders(store, 'https://b.test/sync', 't') is False
    assert sent == ['https://a.test/sync/push/_folders', 'https://b.test/sync/push/_folders']


def test_legacy_unknown_destination_cache_is_not_delivery_proof(tmp_path, monkeypatch):
    store = str(tmp_path)
    mid = L.new_note(store, 'Old cache')
    Y.save_state(store, {'last_pull': 12, 'push_hashes': {mid: Y.bundle_hash(store, mid)},
                         'folders_hash': 'unused-old-cache'})
    sent = []
    monkeypatch.setattr(Y, 'push', lambda *args: sent.append(args[1]))
    assert Y.push_changed(store, 'https://new.test/sync', 't') == ([mid], [])
    assert sent == [mid]
    assert Y.state_file(store)['last_pull'] == 12


def test_failed_delivery_does_not_mark_second_relay_synced(tmp_path, monkeypatch):
    import pytest
    store = str(tmp_path)
    mid = L.new_note(store, 'Retry')
    monkeypatch.setattr(Y, 'push', lambda *args: None)
    Y.push_changed(store, 'https://a.test', 't')
    def fail(*args):
        raise OSError('relay unavailable')
    monkeypatch.setattr(Y, 'push', fail)
    with pytest.raises(OSError, match='unavailable'):
        Y.push_changed(store, 'https://b.test', 't')
    monkeypatch.setattr(Y, 'push', lambda *args: None)
    assert Y.push_changed(store, 'https://b.test', 't') == ([mid], [])


def test_destination_state_does_not_store_url_or_token(tmp_path, monkeypatch):
    store = str(tmp_path)
    L.new_note(store, 'Private relay')
    monkeypatch.setattr(Y, 'push', lambda *args: None)
    Y.push_changed(store, 'https://relay.test/private-path', 'private-token')
    raw = (tmp_path / '.sync-state.json').read_text()
    assert 'relay.test' not in raw
    assert 'private-path' not in raw
    assert 'private-token' not in raw


def test_real_two_relay_note_and_folder_delivery(tmp_path):
    """Real HTTP servers on ephemeral ports, synthetic text only."""
    import json
    import threading
    from contextlib import ExitStack
    from http.server import HTTPServer
    from iris.sync_server import make_handler

    store = str(tmp_path / 'device')
    folder = L.create_folder(store, 'Roadmap')
    mid = L.new_note(store, 'Spec', folder=folder['id'])
    L.save_notes(store, mid, 'Available on both relays')
    with ExitStack() as cleanup:
        for name in ('first', 'second'):
            root = tmp_path / name
            root.mkdir()
            server = HTTPServer(('127.0.0.1', 0), make_handler(str(root), 'local-test'))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            cleanup.callback(worker.join, 5)
            cleanup.callback(server.server_close)
            cleanup.callback(server.shutdown)
            url = f'http://127.0.0.1:{server.server_port}'
            assert Y.push_changed(store, url, 'local-test') == ([mid], [])
            assert Y.push_folders(store, url, 'local-test') is True
            assert Y.push_changed(store, url, 'local-test') == ([], [mid])
            assert Y.push_folders(store, url, 'local-test') is False
            bundle = json.loads((root / mid / 'bundle.json').read_text())
            assert bundle['notes'] == 'Available on both relays'
            assert 'audio' not in bundle
            folders = json.loads((root / '_folders' / 'bundle.json').read_text())
            assert folders['folders'] == [folder]
