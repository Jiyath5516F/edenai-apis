import json
import os
import re
from importlib import import_module
from io import BufferedReader
from typing import Any, Dict, List, Literal, Optional, Type

from edenai_apis.settings import features_path


def is_valid(x: str, y: str) -> bool:
    """
    Args:
        x: A string pattern to be searched for in y.
        y: A string in which the pattern x will be searched.

    Returns:
        bool: True if the pattern x is found in y, False otherwise.
    """
    return bool(re.search(x, y))


def compare_dicts(dict_a: Dict[Any, Any], dict_b: Dict[Any, Any]) -> bool:
    """
    Args:
        dict_a: A dictionary containing any key-value pairs.
        dict_b: A dictionary containing any key-value pairs.

    Returns:
        True if the dict have the same keys and values for corresponding keys, False otherwise.
    """
    if set(dict_a.keys()) != set(dict_b.keys()):
        return False

    for key in dict_a.keys():
        if not compare(dict_a[key], dict_b[key]):
            return False
    return True


def compare_lists(list_a: List[Any], list_b: List[Any]) -> bool:
    """Return `True` if the two lists are equivalent, else return `False`"""
    # Check if they have the same number of elements
    if len(list_a) != len(list_b):
        return False
    # Compare their different elements
    for i, item_a in enumerate(list_a):
        if not compare(item_a, list_b[i]):
            return False
    # If all OK return True
    return True


def compare(items_a: Any, items_b: Any) -> bool:
    """
    Args:
        items_a (Any): The first input item to compare.
        items_b (Any): The second input item to compare.

    Returns:
        bool: Returns True if the two input items are equal, otherwise False.

    Compares two input items and determines if they are equal.
    The comparison is done based on the type and content of the items.

    If the types of `items_a` and `items_b` are not equal and both are not None, the method will return False.
    Otherwise, it proceeds to compare the items.

    If both `items_a` and `items_b` are dictionaries, the method will perform a dictionary comparison
    using the `compare_dicts` method.

    If both `items_a` and `items_b` are lists, the method will perform a list comparison
    using the `compare_lists` method.

    If none of the above conditions are met, the method will assume the items are equal and return True.

    Note:
        - The `compare_dicts` and `compare_lists` methods used by this method are not shown here but assume
          they are properly implemented for dictionary and list comparisons.
        - The `type_no_int` method used in the initial check is assumed to be defined elsewhere.

    Example:
        >>> compare(7, 7)
        True
        >>> compare(7, 7.0)
        False
        >>> compare([1, 2, 3], [1, 2, 3])
        True
        >>> compare([1, 2, 3], [1, 2, 4])
        False
    """
    if (
        type_no_int(items_a) != type_no_int(items_b)
        and items_a is not None
        and items_b is not None
    ):
        return False

    # Compare dictionaries
    if isinstance(items_a, dict) and isinstance(items_b, dict):
        return compare_dicts(items_a, items_b)

    # Compare lists
    elif isinstance(items_a, list) and isinstance(items_b, list):
        return compare_lists(items_a, items_b)
    return True


def compare_responses(
    feature: str,
    subfeature: str,
    response: Any,
    phase: str = "",
) -> Literal[True]:
    """
    Compare standardized response of a subfeature with the generated output
    Raise `AssertionError` if not equivalent
    Returns `True`
    """
    if phase:
        response_path = os.path.join(
            features_path,
            feature,
            subfeature,
            phase,
            f"{subfeature}_{phase}_response.json",
        )
    else:
        response_path = os.path.join(
            features_path, feature, subfeature, f"{subfeature}_response.json"
        )

    # Some subfeatures have dynamic responses that we can't parse
    # the keys listed in `ignore_keys` won't be compared
    ignore_keys = []
    try:
        key_ignore_function_name = feature + "__" + subfeature + "_ignore"
        subfeature_normalized = subfeature.replace("_async", "")
        imp = import_module(
            f"edenai_apis.features.{feature}.{subfeature_normalized}.ignore_keys"
        )
        ignore_keys = getattr(imp, key_ignore_function_name)()
    except Exception:
        pass

    # Load valid standard response
    with open(response_path, "r", encoding="utf-8") as f:
        standard_response = json.load(f)
        if "original_response" in standard_response:
            raise TypeError(f"Please remove original_response in {response_path}")
        assert_standardization(standard_response, response, ignore_keys=ignore_keys)
    return True


def format_message_error(message: str, path_list_error: List[str]) -> str:
    """
    Args:
        message (str): The error message to be formatted.
        path_list_error (List[str]): The list of paths that caused the error.

    Returns:
        str: The formatted error message with the paths included.

    """
    return message + ". Path: " + ".".join(path_list_error)


def assert_standardization(
    items_a: Any,
    items_b: Any,
    path_list_error: Optional[List[str]] = None,
    ignore_keys: Optional[List[str]] = None,
) -> None:
    """
    Asserts that two items are standardized.

    Args:
        items_a: The first item to be compared.
        items_b: The second item to be compared.
        path_list_error: A list of paths to show the error location if any. Defaults to ["<root>"] if not specified.
        ignore_keys: A list of keys to be ignored during the comparison. Defaults to an empty list if not specified.
    """
    if path_list_error is None:
        path_list_error = ["<root>"]

    if ignore_keys is None:
        ignore_keys = []

    assert_not_none(isinstance(items_a, dict), items_b, path_list_error)

    # if both are not None, check type
    if items_a and items_b:
        # Prevent import MemoryFileUploadHandler
        if not (
            isinstance(items_a, BufferedReader) or isinstance(items_b, BufferedReader)
        ):
            assert (type_no_int(items_a) == type_no_int(items_b)) or issubclass(
                type_no_int(items_b), type_no_int(items_a)
            ), format_message_error(
                f"{type_no_int(items_a).__name__} != {type_no_int(items_b).__name__}",
                path_list_error,
            )

    # if both are list
    if isinstance(items_a, list) or isinstance(items_b, list):
        assert_equivalent_list(items_a, items_b, path_list_error, ignore_keys)

    # if both are dict
    elif isinstance(items_a, dict) or isinstance(items_b, dict):
        assert_equivalent_dict(items_a, items_b, path_list_error, ignore_keys)


def assert_equivalent_list(
    list_a: List[Any],
    list_b: List[Any],
    path_list_error: List[str],
    ignore_keys: List[str],
) -> None:
    """Assert List `a` and `b` are equivalent"""
    # check both are list
    assert isinstance(list_a, list) and isinstance(list_b, list), format_message_error(
        "Not two lists", path_list_error
    )

    # check both are not empty and check first element
    if len(list_a) > 0 and len(list_b) > 0:
        if isinstance(list_b[0], dict):
            assert_equivalent_dict(
                list_a[0], list_b[0], path_list_error + ["0"], ignore_keys
            )
        elif isinstance(list_b[0], list):
            assert_equivalent_list(
                list_a[0], list_b[0], path_list_error + ["0"], ignore_keys
            )


def assert_equivalent_dict(
    dict_a: Dict[Any, Any],
    dict_b: Dict[Any, Any],
    path_list_error: Optional[List[str]] = None,
    ignore_keys: Optional[List[str]] = None,
) -> None:
    """
    Asserts that two dictionaries are equivalent by comparing their keys and values.

    Args:
        dict_a: The first dictionary to compare.
        dict_b: The second dictionary to compare.
        path_list_error: A list representing the current path in the dictionary structure. Defaults to an empty list.
        ignore_keys: A list of keys to ignore during comparison. Defaults to an empty list.

    Raises:
        AssertionError: If the dictionaries are not equivalent.

    """
    if path_list_error is None:
        path_list_error = []

    if ignore_keys is None:
        ignore_keys = []

    assert isinstance(dict_a, dict) and isinstance(dict_b, dict), format_message_error(
        "Not two dicts", path_list_error
    )

    assert_list_unordered_equality(
        list(dict_a.keys()), list(dict_b.keys()), path_list_error, "keys"
    )

    for key in dict_a:
        if key in ignore_keys:
            continue

        key_a = dict_a.get(key)
        key_b = dict_b.get(key)
        assert_standardization(key_a, key_b, path_list_error + [key], ignore_keys)


def assert_list_unordered_equality(
    list_a: List[Any], list_b: List[Any], path_list_error: List[str], str_type: str
) -> None:
    """
    Asserts the unordered equality of two lists.

    Args:
        list_a (List[Any]): The first list to compare.
        list_b (List[Any]): The second list to compare.
        path_list_error (List[str]): The path of the list being compared, used for error message formatting.
        str_type (str): The type of the elements in the lists, used for error message formatting.

    Raises:
        AssertionError: If there are missing or extra elements between the two lists.
    """
    lacks = sorted(list(set(list_a) - set(list_b)))
    assert not lacks, format_message_error(
        f"Missing {str_type} {lacks}", path_list_error
    )
    extra = sorted(list(set(list_b) - set(list_a)))
    assert not extra, format_message_error(f"Extra {str_type} {extra}", path_list_error)


def assert_not_none(items_a: Any, items_b: Any, path_list_error: List[str]) -> None:
    """
    Asserts that both `items_a` and `items_b` are not `None`.

    Args:
        items_a (Any): The first item to check.
        items_b (Any): The second item to check.
        path_list_error (List[str]): A list used to store the error messages for the path.

    Raises:
        AssertionError: If either `items_a` or `items_b` is `None`, and the other item is of the wrong data type.

    Example:
       >>> assert_not_none("hello", {"key": "value"}, ["error1", "error2"])

    """
    if items_a is None:
        assert not isinstance(items_b, list), format_message_error(
            "None and dict", path_list_error
        )
        assert not isinstance(items_b, dict), format_message_error(
            "None and list", path_list_error
        )
    if items_b is None:
        assert not isinstance(items_a, list), format_message_error(
            "None and dict", path_list_error
        )
        assert not isinstance(items_a, dict), format_message_error(
            "None and list", path_list_error
        )


def type_no_int(var: Any) -> Type[Any]:
    """
    Args:
        var: The variable to check the type of.

    Returns:
        The type of the variable if it is not an integer, otherwise float.
    """
    return type(var) if not isinstance(var, int) else float
