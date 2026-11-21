#!/usr/bin/env python3
"""Phase 1 一键执行脚本：安装依赖、初始化数据库、生成数据、运行测试"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def run(cmd, cwd=None):
    """运行命令并打印输出。"""
    print(f"[CMD] {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_ROOT,
                           capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main():
    # 1. 安装依赖
    rc = run("pip install -r requirements.txt")
    if rc != 0:
        print("依赖安装失败")
        return rc

    # 2. 初始化数据库并生成模拟数据
    print("\n===== 初始化数据库 =====")
    rc = run("python scripts/init_demo_data.py --reset")
    if rc != 0:
        print("数据库初始化失败")
        return rc

    # 3. 运行 pytest
    print("\n===== 运行 pytest =====")
    rc = run("python -m pytest tests/ -v")
    if rc != 0:
        print("测试失败")
        return rc

    print("\n===== Phase 1 全部完成 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())