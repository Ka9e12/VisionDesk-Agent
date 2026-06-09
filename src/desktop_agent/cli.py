from __future__ import annotations

import argparse
import json
import sys

from desktop_agent.config import AgentConfig, load_env_file
from desktop_agent.controller import AgentController
from desktop_agent.doctor import doctor
from desktop_agent.perception.collector import PerceptionCollector
from desktop_agent.runtime.logger import RunLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="desktop-agent",
        description="Local multimodal desktop agent.",
    )
    parser.add_argument("--env", default=".env", help="Path to env file")

    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run an autonomous desktop task")
    run.add_argument("task", help="Natural-language task")
    run.add_argument("--max-steps", type=int, default=None)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--yes", action="store_true", help="Approve high-risk confirmations")
    run.add_argument("--ocr", action="store_true", help="Enable optional OCR")
    run.add_argument("--browser-dom", action="store_true", help="Enable optional browser DOM snapshot")
    run.add_argument("--accessibility", action="store_true", help="Enable optional macOS accessibility probe")

    perceive = sub.add_parser("perceive", help="Capture one observation")
    perceive.add_argument("--ocr", action="store_true")
    perceive.add_argument("--browser-dom", action="store_true")
    perceive.add_argument("--accessibility", action="store_true")

    sub.add_parser("doctor", help="Check local environment")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env)
    config = AgentConfig.from_env()

    if args.command == "doctor":
        for name, ok, detail in doctor(config):
            mark = "ok" if ok else "missing"
            print(f"{mark:7} {name:24} {detail}")
        return 0

    if args.command == "perceive":
        config = config.with_overrides(
            include_ocr=args.ocr or None,
            include_browser_dom=args.browser_dom or None,
            include_accessibility=args.accessibility or None,
        )
        logger = RunLogger(config.log_dir)
        collector = PerceptionCollector(config, logger)
        obs = collector.collect(task="perceive", step=1, recent_actions=[])
        logger.log("observation", obs.to_prompt_dict())
        print(json.dumps(obs.to_prompt_dict(), ensure_ascii=False, indent=2))
        print(f"log_dir: {logger.run_dir}")
        return 0

    if args.command == "run":
        config = config.with_overrides(
            max_steps=args.max_steps,
            dry_run=True if args.dry_run else None,
            assume_yes=True if args.yes else None,
            include_ocr=True if args.ocr else None,
            include_browser_dom=True if args.browser_dom else None,
            include_accessibility=True if args.accessibility else None,
        )
        result = AgentController(config).run(args.task)
        print("\n结果：", "成功" if result.success else "未完成")
        print(result.message)
        print(f"log_dir: {result.log_dir}")
        return 0 if result.success else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
