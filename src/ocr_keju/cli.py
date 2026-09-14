from __future__ import annotations

import argparse
import sys

from ocr_keju.api import JX3BoxApiError, JX3BoxExamClient
from ocr_keju.config import Settings
from ocr_keju.database import QuestionRepository
from ocr_keju.image import load_image, preprocess_question_image
from ocr_keju.models import SearchResult
from ocr_keju.ocr import RapidOcrEngine
from ocr_keju.services import QuestionService
from ocr_keju.sync import QuestionBankSyncService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ocr-keju", description="OCR 科举助手核心调试 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="初始化本地 SQLite 题库")
    subparsers.add_parser("stats", help="显示本地题库统计")
    subparsers.add_parser("sync", help="从 JX3BOX 批量同步科举题库到本地")
    search_parser = subparsers.add_parser("search", help="本地优先查询一道题")
    search_parser.add_argument("question", help="题目文字")
    ocr_parser = subparsers.add_parser("ocr-image", help="对本地图片执行 OCR")
    ocr_parser.add_argument("image", help="图片路径")
    return parser


def _print_result(result: SearchResult) -> None:
    question = result.question
    print(f"来源: {result.source}")
    print(f"匹配度: {result.confidence:.1%}")
    print(f"题目: {question.title}")
    for index, option in enumerate(question.options):
        marker = "*" if index in question.answer_indices else " "
        print(f"  [{marker}] {index}. {option}")
    print(f"答案: {' / '.join(question.answer_text)}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = Settings.from_env()
    settings.ensure_directories()
    repository = QuestionRepository(settings.database_path)

    if args.command == "init-db":
        repository.initialize()
        print(f"数据库已初始化: {settings.database_path}")
        return 0

    if args.command == "stats":
        print(f"本地题目数量: {repository.count()}")
        print(f"数据库: {settings.database_path}")
        return 0

    if args.command == "ocr-image":
        image = preprocess_question_image(load_image(args.image))
        result = RapidOcrEngine().recognize(image)
        print(result.text)
        print(f"OCR 平均置信度: {result.mean_score:.1%}")
        print(f"OCR 耗时: {result.elapsed_seconds * 1000:.0f} ms")
        return 0 if result.text else 1

    if args.command == "sync":
        try:
            with JX3BoxExamClient(
                base_url=settings.api_base_url,
                timeout_seconds=settings.api_timeout_seconds,
            ) as api_client:
                report = QuestionBankSyncService(repository, api_client).sync()
        except JX3BoxApiError as exc:
            print(f"题库同步失败: {exc}", file=sys.stderr)
            return 2
        print(f"远端获取: {report.fetched}")
        print(f"本次写入/更新: {report.stored}")
        print(f"本地题库总数: {report.local_total}")
        return 0

    if args.command == "search":
        try:
            with JX3BoxExamClient(
                base_url=settings.api_base_url,
                timeout_seconds=settings.api_timeout_seconds,
            ) as api_client:
                service = QuestionService(repository, api_client)
                result = service.resolve(args.question)
        except JX3BoxApiError as exc:
            print(f"远端查询失败: {exc}", file=sys.stderr)
            return 2

        if result is None:
            print("未找到题目")
            return 1
        _print_result(result)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
