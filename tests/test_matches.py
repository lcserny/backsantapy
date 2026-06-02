from fastapi.testclient import TestClient
from main import app, matches

client = TestClient(app)


def names_wrapper():
    return {
        "names": {
            "leo": ["casu"],
            "sabina": ["leo"],
            "casu": [],
        }
    }


def exhausted_names_wrapper():
    return {
        "names": {
            "leo": ["sabina"],
            "sabina": ["leo"],
        }
    }


def simple_names_wrapper():
    return {
        "names": {
            "leo": [],
            "sabina": [],
        }
    }


def test_can_generate_links():
    response = client.post("/matches", json=names_wrapper())
    assert response.status_code == 200
    pairs = response.json()
    assert len(pairs) == 3
    pairs.sort(key=lambda x: x["name"])
    assert pairs[0]["name"] == "casu"
    assert pairs[1]["name"] == "leo"
    assert pairs[2]["name"] == "sabina"


def test_exclusions_cannot_exhaust_all_names():
    response = client.post("/matches", json=exhausted_names_wrapper())
    assert response.status_code == 400
    error = response.json()
    assert "contains all names" in error["detail"]


def test_can_find_match():
    pairs = client.post("/matches", json=simple_names_wrapper()).json()
    pairs.sort(key=lambda x: x["name"])
    first = pairs[0]

    response = client.get(f"/matches/{first['token']}")
    assert response.status_code == 200
    data = response.json()
    assert data["target"] == "sabina"


def test_can_find_match_only_once():
    pairs = client.post("/matches", json=simple_names_wrapper()).json()
    pairs.sort(key=lambda x: x["name"])
    first = pairs[0]

    first_response = client.get(f"/matches/{first['token']}")
    assert first_response.status_code == 200

    second_response = client.get(f"/matches/{first['token']}")
    assert second_response.status_code == 400


def test_when_finding_match_throw_if_not_found():
    response = client.get("/matches/nonexistent-token")
    assert response.status_code == 400
    error = response.json()
    assert "token not found" in error["detail"]


def test_can_clear_matches():
    client.post("/matches", json=simple_names_wrapper())
    assert len(matches) > 0

    response = client.delete("/matches")
    assert response.status_code == 204
    assert len(matches) == 0
