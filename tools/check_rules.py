"""src/ 가 저장소 규칙(.github/copilot-instructions.md)을 지키는지 코드 문맥으로 검사한다.

grep은 주석·문자열·`horner_hash(` 같은 이름까지 걸리므로, 여기서는 ast로 실제 코드만 본다.
잡는 것:
  - dict / set / frozenset / hash 이름을 쓰는 곳 (호출, 대입, 인자 등)
  - {} {k: v} {x} 리터럴, dict·set 컴프리헨션
  - **kwargs 받기 (내부적으로 dict)
  - collections 모듈의 dict 계열 (Counter, defaultdict, OrderedDict, ChainMap)
사용법: python3 tools/check_rules.py [디렉터리]   (위반이 있으면 종료 코드 1)
"""
import ast
import os
import sys

FORBIDDEN_NAMES = ("dict", "set", "frozenset", "hash",
                   "Counter", "defaultdict", "OrderedDict", "ChainMap")


def check_source(source, filename="<src>"):
    tree = ast.parse(source, filename)
    problems = []

    def report(node, msg):
        problems.append("%s:%d: %s" % (filename, node.lineno, msg))

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            report(node, "금지된 이름 %r 사용" % node.id)
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES[4:]:
            report(node, "금지된 컬렉션 %r 사용" % node.attr)
        elif isinstance(node, ast.Dict):
            report(node, "dict 리터럴 사용")
        elif isinstance(node, ast.Set):
            report(node, "set 리터럴 사용")
        elif isinstance(node, (ast.DictComp, ast.SetComp)):
            report(node, "dict/set 컴프리헨션 사용")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if node.args.kwarg is not None:
                report(node, "**%s (dict) 인자 사용" % node.args.kwarg.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in FORBIDDEN_NAMES[4:]:
                    report(node, "금지된 컬렉션 %r import" % alias.name)
    return problems


def check_dir(path):
    problems = []
    for name in sorted(os.listdir(path)):
        if name.endswith(".py"):
            full = os.path.join(path, name)
            with open(full, encoding="utf-8") as f:
                problems.extend(check_source(f.read(), full))
    return problems


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = argv[1] if len(argv) > 1 else os.path.join(root, "src")
    problems = check_dir(path)
    for p in problems:
        print(p)
    print("규칙 위반 %d건" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
