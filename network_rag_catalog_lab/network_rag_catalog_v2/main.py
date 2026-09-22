import json
import sys
from app.pipeline import run, plan_to_dict


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Network operation request: ")
    plan = run(prompt)

    print("\nJSON PLAN:")
    print(json.dumps(plan_to_dict(plan), indent=2))
