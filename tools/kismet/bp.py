"""Compact Kismet bytecode reader for UAssetGUI JSON exports.

usage: python bp.py file.json grep REGEX [context]   -> statements matching REGEX (with +-context)
       python bp.py file.json funcs                  -> list function exports
       python bp.py file.json range FUNC START END   -> print statements START..END of FUNC
"""
import json, re, sys

path = sys.argv[1]
d = json.load(open(path, encoding='utf-8'))
imports = d.get('Imports', [])
exports = d['Exports']


def ref(i):
    if not isinstance(i, int) or i == 0:
        return str(i)
    if i < 0 and -i - 1 < len(imports):
        return imports[-i - 1].get('ObjectName', str(i))
    if i > 0 and i - 1 < len(exports):
        return exports[i - 1].get('ObjectName', str(i))
    return str(i)


SKIP = {'KismetPropertyPointer', 'FFieldPath', 'InstanceVariable', 'LocalVariable', 'LocalOutVariable'}


def toks(o, out):
    if isinstance(o, dict):
        t = o.get('$type', '')
        if t:
            name = t.split('.')[-1].split(',')[0].replace('EX_', '')
            if name not in SKIP:
                out.append(name)
        if isinstance(o.get('Path'), list):
            out.append('<' + '.'.join(o['Path']) + '>')
        for k in ('StackNode', 'Function', 'Value', 'CodeOffset', 'VirtualFunctionName'):
            v = o.get(k)
            if v is None or isinstance(v, (dict, list)):
                continue
            if k in ('StackNode', 'Function') or (k == 'Value' and 'ObjectConst' in t):
                out.append('@' + ref(v))
            else:
                out.append('=' + str(v))
        for k, v in o.items():
            if k not in ('$type',):
                toks(v, out)
    elif isinstance(o, list):
        for v in o:
            toks(v, out)


def stmt(s):
    out = []
    toks(s, out)
    return ' '.join(out)


funcs = [(i, e) for i, e in enumerate(exports) if e.get('ScriptBytecode')]
mode = sys.argv[2]
if mode == 'funcs':
    for i, e in funcs:
        print(i, e['ObjectName'], len(e['ScriptBytecode']))
elif mode == 'grep':
    rx = re.compile(sys.argv[3], re.I)
    ctx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    for i, e in funcs:
        bc = e['ScriptBytecode']
        texts = [stmt(s) for s in bc]
        hits = [j for j, t in enumerate(texts) if rx.search(t)]
        shown = set()
        for j in hits:
            for k in range(max(0, j - ctx), min(len(bc), j + ctx + 1)):
                if k in shown:
                    continue
                shown.add(k)
                print(f"{e['ObjectName']}[{k}]{'*' if k == j else ' '} {texts[k][:400]}")
            if ctx:
                print('--')
elif mode == 'range':
    name, a, b = sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    for i, e in funcs:
        if e['ObjectName'] == name:
            bc = e['ScriptBytecode']
            for k in range(a, min(b + 1, len(bc))):
                print(f"[{k}] {stmt(bc[k])[:500]}")
