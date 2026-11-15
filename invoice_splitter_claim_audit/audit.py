"""Read-only, module-local AST and documentation analysis."""
import ast
import os
import re
from pathlib import Path
from .phrases import INVOICESPLITTER, NOINVOICESPLITTER, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace("’", "'").replace("n't", ' not').replace('-', ' ').split())


def paragraphs(text):
    lines = []
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            lines.append((number, ''))
        elif marker:
            fence = marker[1]
            lines.append((number, ''))
        else:
            lines.append((number, line))
    group = []
    start = 1
    for number, line in lines + [(len(lines) + 1, '')]:
        if line.strip():
            if not group:
                start = number
            group.append(line)
        elif group:
            yield start, normalize(' '.join(group))
            group = []


def matches(text, phrases):
    pattern = r'\b(?:' + '|'.join(re.escape(p) for p in sorted(phrases, key=lambda p: (-len(p), p))) + r')\b'
    return list(re.finditer(pattern, text))


def claims_in(text, path):
    result = []
    for line, paragraph in paragraphs(text):
        negative = matches(paragraph, NOINVOICESPLITTER)
        for match in negative:
            result.append(dict(family='NOINVOICESPLITTER', phrase=match[0], path=path, line=line))
        masked = list(paragraph)
        for match in negative:
            masked[match.start():match.end()] = ' ' * (match.end() - match.start())
        for match in matches(''.join(masked), INVOICESPLITTER):
            result.append(dict(family='INVOICESPLITTER', phrase=match[0], path=path, line=line))
    return result


def evidence_in(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    nodes = list(ast.walk(tree))
    aliases = {}
    imports = set()
    bound = set()
    definitions = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for item in node.names:
                imports.add(item.name.split('.')[0])
                aliases[item.asname or item.name.split('.')[0]] = item.name if item.asname else item.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if not node.level:
                imports.add(module.split('.')[0])
                for item in node.names:
                    aliases[item.asname or item.name] = module + '.' + item.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.With, ast.AsyncWith)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else [i.optional_vars for i in node.items if i.optional_vars]
            for target in targets:
                bound.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
    shadow = bound | definitions

    def clean(expr):
        return not any(isinstance(n, ast.Name) and n.id in shadow for n in ast.walk(expr))

    def imported(name):
        return aliases.get(name, '') if name not in shadow else ''

    calls = [n for n in nodes if isinstance(n, ast.Call)]
    client = False
    parse = []
    result = []
    for call in calls:
        func = call.func
        if isinstance(func, ast.Name):
            resolved = imported(func.id)
            if resolved == 'mindee.Client':
                client = True
            route = resolved.rsplit('.', 1)[-1]
            if resolved and route in GENERIC_NAMES and route not in definitions:
                result.append((call.lineno, route))
        elif isinstance(func, ast.Attribute):
            route = func.attr
            # Assignment to the receiver (client = Client(...)) is normal;
            # only a receiver replacing an imported binding is shadowing.
            roots = [n.id for n in ast.walk(func.value) if isinstance(n, ast.Name)]
            receiver_shadow = any(n in aliases and n in shadow for n in roots)
            if route in definitions or receiver_shadow:
                continue
            if route == 'Client' and isinstance(func.value, ast.Name) and func.value.id == 'mindee' and clean(func.value):
                client = True
            if route in GENERIC_NAMES:
                result.append((call.lineno, route))
            if 'veryfi' in imports and route in ('split_and_process_pdf', 'split_and_process_pdf_url'):
                result.append((call.lineno, route))
            if route == 'parse':
                args = list(call.args) + [k.value for k in call.keywords]
                if any(((isinstance(a, ast.Name) and a.id == 'InvoiceSplitterV1') or (isinstance(a, ast.Attribute) and a.attr == 'InvoiceSplitterV1')) and clean(a) and 'InvoiceSplitterV1' not in definitions for a in args):
                    parse.append((call.lineno, 'mindee.InvoiceSplitterV1'))
    if 'mindee' in imports and client:
        result.extend(parse)
    return sorted(set(result))


def audit(root, ignore=()):
    root = Path(root)
    if not root.is_dir():
        raise OSError('repository must be a directory: ' + str(root))
    prefixes = [Path(p).as_posix().strip('/') for p in ignore]

    def ignored(relative):
        name = relative.as_posix()
        return any(name == p or name.startswith(p + '/') or p == '.' for p in prefixes)

    claims, evidence = [], []
    def walk_error(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        base = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (base / d).is_symlink() and not ignored((base / d).relative_to(root)))
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(root)
            if path.is_symlink() or ignored(relative):
                continue
            parts = relative.parts
            if relative.as_posix() == 'README.md' or (path.suffix == '.md' and 'docs' in parts[:-1]):
                claims.extend(claims_in(path.read_text(encoding='utf-8'), relative.as_posix()))
            if path.suffix != '.py' or any(p in ('fixtures', 'docs', 'examples') for p in parts[:-1]):
                continue
            test = 'tests' in parts[:-1] or name.startswith('test_') or name.endswith('_test.py')
            for line, route in evidence_in(path.read_text(encoding='utf-8')):
                evidence.append(dict(path=relative.as_posix(), line=line, route=route, test=test))
    production = any(not e['test'] for e in evidence)
    findings = []
    if any(c['family'] == 'INVOICESPLITTER' for c in claims) and not production:
        findings.append(dict(rule='documented-invoice-splitter-claim-false', severity='MEDIUM' if evidence else 'HIGH', message='Documented positive claim lacks production evidence.'))
    if any(c['family'] == 'NOINVOICESPLITTER' for c in claims) and production:
        findings.append(dict(rule='documented-no-invoice-splitter-claim-false', severity='HIGH', message='Documented denial contradicts production evidence.'))
    return dict(verdict='FAIL' if findings else 'PASS', findings=findings, claims=claims, evidence=evidence)
