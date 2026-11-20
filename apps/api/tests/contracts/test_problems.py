from api.shared.problems import problem_payload


def test_problem_payload_matches_the_django_envelope() -> None:
    payload = problem_payload(
        status_code=404,
        detail="Entity not found.",
        instance="/api/v1/index/entities/x/metrics/",
        trace_id="abc123",
    )

    assert payload == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Entity not found.",
        "instance": "/api/v1/index/entities/x/metrics/",
        "trace_id": "abc123",
    }
