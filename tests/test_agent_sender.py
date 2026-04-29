from agent.sender import get_health_url


def test_get_health_url_uses_api_origin():
    assert get_health_url("https://inventario.example.com/checkin") == "https://inventario.example.com/"
    assert get_health_url("http://127.0.0.1:8000/api/checkin") == "http://127.0.0.1:8000/"
