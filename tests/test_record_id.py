from scripts.utils import record_id_from


def test_record_id_deterministic():
    rid1 = record_id_from("123", "A Title: Study of X")
    rid2 = record_id_from("123", "A Title: Study of X")
    assert rid1 == rid2


def test_record_id_normalizes_title():
    rid1 = record_id_from("123", "A Title: Study of X")
    rid2 = record_id_from("123", "a  title study of x!!!")
    assert rid1 == rid2

