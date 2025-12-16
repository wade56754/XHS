#!/usr/bin/env python3
"""
安全审计脚本

用于检查代码和日志中是否存在敏感信息泄露。

检查项目:
1. 明文 Cookie 值
2. 硬编码密钥
3. 日志中的敏感信息
4. 环境变量配置

使用方式:
    python scripts/security_audit.py [项目目录]
    python scripts/security_audit.py --check-logs /var/log/mediacrawler
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """严重程度"""
    CRITICAL = "CRITICAL"  # 立即修复
    HIGH = "HIGH"          # 尽快修复
    MEDIUM = "MEDIUM"      # 计划修复
    LOW = "LOW"            # 可忽略
    INFO = "INFO"          # 信息提示


@dataclass
class SecurityIssue:
    """安全问题"""
    file: str
    line: int
    issue_type: str
    severity: Severity
    message: str
    match: str = ""


class SecurityAuditor:
    """
    安全审计器

    检查代码库中的安全问题
    """

    # Cookie 相关正则
    COOKIE_PATTERNS = [
        (r'web_session=[A-Za-z0-9%_-]{10,}', 'XHS web_session Cookie'),
        (r'a1=[A-Za-z0-9%_-]{10,}', 'XHS a1 Cookie'),
        (r'gid=[A-Za-z0-9%_-]{10,}', 'XHS gid Cookie'),
        (r'webId=[A-Za-z0-9%_-]{10,}', 'XHS webId Cookie'),
        (r'xsecappid=[A-Za-z0-9%_-]{10,}', 'XHS xsecappid Cookie'),
    ]

    # 硬编码密钥正则
    KEY_PATTERNS = [
        (r'(api_key|apikey|api-key)\s*[=:]\s*["\'][A-Za-z0-9_-]{20,}["\']', '硬编码 API Key'),
        (r'(secret|secret_key)\s*[=:]\s*["\'][A-Za-z0-9_-]{20,}["\']', '硬编码 Secret'),
        (r'(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', '硬编码密码'),
        (r'MASTER_KEY\s*[=:]\s*["\'][^"\']+["\']', '硬编码主密钥'),
        (r'ENCRYPTION_KEY\s*[=:]\s*["\'][^"\']+["\']', '硬编码加密密钥'),
        (r'PRIVATE_KEY\s*[=:]\s*["\'][^"\']+["\']', '硬编码私钥'),
    ]

    # 忽略的目录
    IGNORE_DIRS = {
        'node_modules', '.venv', 'venv', '__pycache__',
        '.git', '.idea', '.vscode', 'dist', 'build',
        'eggs', '*.egg-info'
    }

    # 忽略的文件
    IGNORE_FILES = {
        '*.pyc', '*.pyo', '*.so', '*.dylib',
        '*.png', '*.jpg', '*.gif', '*.ico',
        '*.woff', '*.woff2', '*.ttf', '*.eot',
    }

    # 要检查的文件扩展名
    CHECK_EXTENSIONS = {
        '.py', '.js', '.ts', '.json', '.yaml', '.yml',
        '.env', '.ini', '.cfg', '.conf', '.toml',
        '.md', '.txt', '.sh', '.bash'
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.issues: List[SecurityIssue] = []

    def should_check_file(self, filepath: Path) -> bool:
        """判断是否应该检查此文件"""
        # 检查是否在忽略目录中
        for part in filepath.parts:
            if part in self.IGNORE_DIRS:
                return False

        # 检查扩展名
        if filepath.suffix.lower() not in self.CHECK_EXTENSIONS:
            return False

        # 检查是否是忽略文件
        for pattern in self.IGNORE_FILES:
            if filepath.match(pattern):
                return False

        return True

    def audit_file(self, filepath: Path) -> List[SecurityIssue]:
        """
        审计单个文件

        Args:
            filepath: 文件路径

        Returns:
            发现的问题列表
        """
        issues = []

        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
        except Exception as e:
            issues.append(SecurityIssue(
                file=str(filepath),
                line=0,
                issue_type='AUDIT_ERROR',
                severity=Severity.INFO,
                message=f'无法读取文件: {e}'
            ))
            return issues

        relative_path = str(filepath.relative_to(self.project_root))

        # 检查 Cookie 明文
        for pattern, description in self.COOKIE_PATTERNS:
            for i, line in enumerate(lines, 1):
                # 跳过注释和测试代码
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('//'):
                    continue
                if 'test' in filepath.stem.lower() or 'mock' in filepath.stem.lower():
                    continue

                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    issues.append(SecurityIssue(
                        file=relative_path,
                        line=i,
                        issue_type='PLAINTEXT_COOKIE',
                        severity=Severity.CRITICAL,
                        message=f'发现明文 Cookie ({description})',
                        match=matches[0][:30] + '...'
                    ))

        # 检查硬编码密钥
        for pattern, description in self.KEY_PATTERNS:
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('//'):
                    continue

                if re.search(pattern, line, re.IGNORECASE):
                    # 排除示例和模板
                    if 'example' in line.lower() or 'xxx' in line.lower():
                        continue
                    if 'your_' in line.lower() or 'replace' in line.lower():
                        continue

                    issues.append(SecurityIssue(
                        file=relative_path,
                        line=i,
                        issue_type='HARDCODED_SECRET',
                        severity=Severity.HIGH,
                        message=description
                    ))

        return issues

    def audit_logs(self, log_dir: str) -> List[SecurityIssue]:
        """
        审计日志文件

        Args:
            log_dir: 日志目录

        Returns:
            发现的问题列表
        """
        issues = []
        log_path = Path(log_dir)

        if not log_path.exists():
            return issues

        for log_file in log_path.glob('**/*.log'):
            try:
                content = log_file.read_text(encoding='utf-8', errors='ignore')

                for pattern, description in self.COOKIE_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(SecurityIssue(
                            file=str(log_file),
                            line=0,
                            issue_type='COOKIE_IN_LOG',
                            severity=Severity.CRITICAL,
                            message=f'日志中发现 Cookie 明文 ({description})'
                        ))
                        break

            except Exception:
                pass

        return issues

    def audit_env(self) -> List[SecurityIssue]:
        """
        审计环境变量配置

        Returns:
            发现的问题列表
        """
        issues = []

        # 必需的安全配置
        required_vars = [
            ('COOKIE_MASTER_KEY', '加密主密钥'),
        ]

        # 推荐的安全配置
        recommended_vars = [
            ('COOKIE_KEY_SALT', '密钥派生盐值'),
            ('COOKIE_KEY_ID', '密钥版本ID'),
        ]

        for var, description in required_vars:
            if not os.environ.get(var):
                issues.append(SecurityIssue(
                    file='.env',
                    line=0,
                    issue_type='MISSING_CONFIG',
                    severity=Severity.HIGH,
                    message=f'缺少必需的环境变量: {var} ({description})'
                ))

        for var, description in recommended_vars:
            if not os.environ.get(var):
                issues.append(SecurityIssue(
                    file='.env',
                    line=0,
                    issue_type='MISSING_CONFIG',
                    severity=Severity.LOW,
                    message=f'推荐设置环境变量: {var} ({description})'
                ))

        return issues

    def run_full_audit(self, check_env: bool = True) -> Dict[str, Any]:
        """
        运行完整审计

        Args:
            check_env: 是否检查环境变量

        Returns:
            审计结果
        """
        self.issues = []

        # 审计源代码
        for filepath in self.project_root.rglob('*'):
            if filepath.is_file() and self.should_check_file(filepath):
                self.issues.extend(self.audit_file(filepath))

        # 审计日志
        log_dirs = [
            self.project_root / 'logs',
            self.project_root / 'log',
            Path('/var/log/mediacrawler'),
        ]
        for log_dir in log_dirs:
            if log_dir.exists():
                self.issues.extend(self.audit_logs(str(log_dir)))

        # 审计环境变量
        if check_env:
            self.issues.extend(self.audit_env())

        # 统计
        critical = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in self.issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in self.issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in self.issues if i.severity == Severity.LOW)

        return {
            'total_issues': len(self.issues),
            'critical': critical,
            'high': high,
            'medium': medium,
            'low': low,
            'issues': self.issues,
            'passed': critical == 0 and high == 0
        }


def print_report(result: Dict[str, Any]):
    """打印审计报告"""
    print("\n" + "=" * 70)
    print("                    安全审计报告")
    print("=" * 70)
    print(f"总问题数: {result['total_issues']}")
    print(f"  - 严重 (CRITICAL): {result['critical']}")
    print(f"  - 高危 (HIGH):     {result['high']}")
    print(f"  - 中危 (MEDIUM):   {result['medium']}")
    print(f"  - 低危 (LOW):      {result['low']}")
    print("=" * 70)

    if result['issues']:
        # 按严重程度排序
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4
        }
        sorted_issues = sorted(
            result['issues'],
            key=lambda x: severity_order[x.severity]
        )

        print("\n问题详情:\n")
        for issue in sorted_issues:
            severity_color = {
                Severity.CRITICAL: '\033[91m',  # 红色
                Severity.HIGH: '\033[93m',      # 黄色
                Severity.MEDIUM: '\033[94m',    # 蓝色
                Severity.LOW: '\033[90m',       # 灰色
                Severity.INFO: '\033[90m',      # 灰色
            }
            reset = '\033[0m'

            color = severity_color.get(issue.severity, '')
            print(f"{color}[{issue.severity.value}]{reset} {issue.issue_type}")
            print(f"  文件: {issue.file}" + (f":{issue.line}" if issue.line else ""))
            print(f"  说明: {issue.message}")
            if issue.match:
                print(f"  匹配: {issue.match}")
            print()

    print("=" * 70)
    if result['passed']:
        print("\033[92m✅ 安全审计通过\033[0m")
    else:
        print("\033[91m❌ 安全审计失败\033[0m")
        print("\n请修复所有 CRITICAL 和 HIGH 级别的问题后再部署。")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='MediaCrawler 安全审计工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python security_audit.py                      # 审计当前目录
  python security_audit.py /path/to/project     # 审计指定目录
  python security_audit.py --check-logs /var/log/app  # 额外检查日志目录
  python security_audit.py --no-env             # 不检查环境变量
        """
    )

    parser.add_argument(
        'project_dir',
        nargs='?',
        default='.',
        help='项目目录 (默认: 当前目录)'
    )
    parser.add_argument(
        '--check-logs',
        dest='log_dir',
        help='额外的日志目录'
    )
    parser.add_argument(
        '--no-env',
        action='store_true',
        help='不检查环境变量'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='以 JSON 格式输出'
    )

    args = parser.parse_args()

    # 运行审计
    auditor = SecurityAuditor(args.project_dir)
    result = auditor.run_full_audit(check_env=not args.no_env)

    # 额外检查日志
    if args.log_dir:
        result['issues'].extend(auditor.audit_logs(args.log_dir))
        result['total_issues'] = len(result['issues'])

    # 输出结果
    if args.json:
        import json
        # 转换为可序列化格式
        output = {
            **result,
            'issues': [
                {
                    'file': i.file,
                    'line': i.line,
                    'issue_type': i.issue_type,
                    'severity': i.severity.value,
                    'message': i.message,
                    'match': i.match
                }
                for i in result['issues']
            ]
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(result)

    # 返回退出码
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
