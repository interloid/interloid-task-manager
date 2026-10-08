from ua_parser import parse


def parse_user_agent(
    user_agent: str | None,
) -> tuple[str, str]:
    if not user_agent:
        return "Unknown", "Unknown"

    parsed = parse(user_agent)

    browser = parsed.user_agent.family if parsed.user_agent is not None else "Unknown"

    os_name = parsed.os.family if parsed.os is not None else "Unknown"

    return browser, os_name
