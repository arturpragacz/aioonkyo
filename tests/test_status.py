import pytest
from aioonkyo.status import TemperatureStatus
from aioonkyo.message_code import Code


def test_temperature_status_parse_method():
    test_cases = [
        # (parameter_bytes, expected_temp)
        (b"F 64C 18", 18),
        (b"F 82C 28", 28),
    ]

    mock_code = Code.TPD

    for param_bytes, expected_temp in test_cases:
        status_object = TemperatureStatus.parse(code=mock_code, parameter=param_bytes)

        assert isinstance(status_object, TemperatureStatus)
        assert status_object.celsius == expected_temp


def test_temperature_status_parse_raises_error_on_invalid():
    invalid_param = b"SOME UNEXPECTED GARBAGE"
    mock_code = Code.TPD

    with pytest.raises(ValueError):
        TemperatureStatus.parse(code=mock_code, parameter=invalid_param)
