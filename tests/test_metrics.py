from eidolon import metrics


def test_metrics_generate_latest():
    data = metrics.get_metrics_response()
    content, content_type = data
    assert content
    assert metrics.CONTENT_TYPE_LATEST in content_type
