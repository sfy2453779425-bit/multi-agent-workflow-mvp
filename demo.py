import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from weather_agent import TemplateWeatherAgent  # noqa: E402


DEFAULT_QUERY = "서울 내일 날씨 알려주고 옷 추천해줘"


def main() -> None:
    query = " ".join(sys.argv[1:]).strip() or DEFAULT_QUERY
    agent = TemplateWeatherAgent()
    result = agent.run(query)

    print("=== Input ===")
    print(query)
    print()
    print("=== Fixed Template Trace ===")
    for index, step in enumerate(result.trace, start=1):
        print(f"{index}. {step.name}: {step.detail}")
    print()
    print("=== Final Answer ===")
    print(result.answer)


if __name__ == "__main__":
    main()
