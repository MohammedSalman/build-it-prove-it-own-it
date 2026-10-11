from app import __version__


def test_health_says_ok_and_names_the_release(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["release"] == __version__
