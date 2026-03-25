import argparse
import io
import sys
from typing import Any, Dict

# Windows 编码兼容性修复
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )

from report_builder import generate_report
from markdown_formatter import format_report_markdown
from utils import dump_json, fail, load_json_file, ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="S6 GenerateReportSkill")
    parser.add_argument("--action", required=True, choices=["generate_report"])
    parser.add_argument("--json-input-file", help="Path to input JSON file")
    parser.add_argument("--json-input", help="Inline input JSON string")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.json_input_file:
        return load_json_file(args.json_input_file)
    if args.json_input:
        import json

        return json.loads(args.json_input)
    raise ValueError("json-input-file or json-input is required")


def main() -> None:
    try:
        args = parse_args()
        payload = load_payload(args)

        if args.action == "generate_report":
            result = generate_report(payload)

            output_format = payload.get("options", {}).get("output_format", "json")

            if output_format == "markdown":
                print(format_report_markdown(result))
            else:
                print(dump_json(ok(result), pretty=args.pretty))
            return

        print(
            dump_json(
                fail("INVALID_ACTION", f"Unsupported action: {args.action}"),
                pretty=args.pretty,
            )
        )
    except FileNotFoundError as e:
        print(dump_json(fail("FILE_NOT_FOUND", str(e)), pretty=True))
    except ValueError as e:
        print(dump_json(fail("INVALID_INPUT", str(e)), pretty=True))
    except Exception as e:
        print(dump_json(fail("UNEXPECTED_ERROR", str(e)), pretty=True))


if __name__ == "__main__":
    main()
