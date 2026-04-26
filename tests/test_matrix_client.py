def test_matrix_client_declares_text_only_events():
    from subhub.matrix_client import MatrixTextClient

    assert MatrixTextClient.event_types() == ("RoomMessageText",)
