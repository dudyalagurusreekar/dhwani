def calculate_risk(
    fake_probability
):

    fake_probability = max(
        0.0,
        min(
            1.0,
            fake_probability
        )
    )

    score = round(
        fake_probability * 100
    )

    if score >= 70:

        status = "HIGH"

        alert = (
            "Possible AI-generated "
            "voice detected"
        )

        recommendation = (
            "VERIFY_CALLER"
        )

    elif score >= 40:

        status = "SUSPICIOUS"

        alert = (
            "Voice requires "
            "additional verification"
        )

        recommendation = (
            "VERIFY_CALLER"
        )

    else:

        status = "LOW"

        alert = (
            "No high-risk signal detected"
        )

        recommendation = "CONTINUE"

    return {

        "risk_score": score,

        "status": status,

        "alert": alert,

        "recommendation":
            recommendation
    }