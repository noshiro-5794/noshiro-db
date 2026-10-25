from scripts.parity import diff, normalize


def test_equal_documents_have_no_differences() -> None:
    assert list(diff({"a": 1, "b": [1, 2]}, {"a": 1, "b": [1, 2]})) == []


def test_missing_and_extra_keys_are_named() -> None:
    differences = list(diff({"a": 1}, {"b": 2}))
    assert "missing in the new response" in differences[0]
    assert "extra in the new response" in differences[1]


def test_numbers_compare_by_value_not_by_type() -> None:
    assert list(diff({"value": 7}, {"value": 7.0})) == []


def test_list_length_is_reported() -> None:
    assert list(diff([1, 2], [1])) == [": length 2 != 1"]


def test_unordered_paths_compare_as_sets() -> None:
    old = {"facts": [{"evidence": [{"id": 1}, {"id": 2}]}]}
    new = {"facts": [{"evidence": [{"id": 2}, {"id": 1}]}]}

    assert list(diff(old, new)) != []
    assert (
        list(
            diff(
                normalize(old, unordered=frozenset({"facts[].evidence"})),
                normalize(new, unordered=frozenset({"facts[].evidence"})),
            )
        )
        == []
    )
