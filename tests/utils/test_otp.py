from app.utils.otp import (
    generate_otp,
    hash_otp,
    verify_otp,
)


def test_generate_otp_returns_six_digits() -> None:
    otp = generate_otp()

    assert len(otp) == 6
    assert otp.isdigit()


def test_hash_otp_does_not_store_plain_otp() -> None:
    otp = "483921"

    otp_hash = hash_otp(
        otp,
    )

    assert otp_hash != otp
    assert len(otp_hash) == 64


def test_verify_otp_returns_true_for_correct_otp() -> None:
    otp = "483921"

    otp_hash = hash_otp(
        otp,
    )

    assert verify_otp(
        otp,
        otp_hash,
    )


def test_verify_otp_returns_false_for_wrong_otp() -> None:
    otp_hash = hash_otp(
        "483921",
    )

    assert not verify_otp(
        "123456",
        otp_hash,
    )
