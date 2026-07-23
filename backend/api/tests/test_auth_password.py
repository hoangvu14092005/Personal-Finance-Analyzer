import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def testPasswordWithOnlyDigitsRaises():
    with pytest.raises(ValidationError, match="Password must include both letters and digits"):
        RegisterRequest(email="a@b.com", password="12345678")


def testPasswordWithOnlyLettersRaises():
    with pytest.raises(ValidationError, match="Password must include both letters and digits"):
        RegisterRequest(email="a@b.com", password="abcdefgh")


def testPasswordWithLettersAndDigitsPasses():
    result = RegisterRequest(email="a@b.com", password="abc12345")
    assert result.password == "abc12345"


def testEmptyPasswordRaises():
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="")


def testPasswordWithNonAsciiLettersPasses():
    result = RegisterRequest(email="a@b.com", password="mậtkhẩu123")
    assert result.password == "mậtkhẩu123"
