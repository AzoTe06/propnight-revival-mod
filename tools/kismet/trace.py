"""Follow Kismet control flow from an ubergraph entry offset.

usage: python trace.py file.json UBERGRAPH START_OFFSET [MAX_STATEMENTS]
Prints basic blocks labelled by offset, each once, in discovery order.
Control statements are rendered as: goto L / if not (...) goto L / push L / pop / pop if not (...).
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from offsets import size, T  # noqa: E402

SKIP = {'KismetPropertyPointer', 'FFieldPath', 'InstanceVariable', 'LocalVariable', 'LocalOutVariable'}


def main():
    d = json.load(open(sys.argv[1], encoding='utf-8'))
    imports, exports = d.get('Imports', []), d['Exports']

    def ref(i):
        if isinstance(i, int) and i < 0 and -i - 1 < len(imports):
            return imports[-i - 1].get('ObjectName', str(i))
        if isinstance(i, int) and 0 < i <= len(exports):
            return exports[i - 1].get('ObjectName', str(i))
        return str(i)

    def toks(o, out):
        if isinstance(o, dict):
            t = o.get('$type', '')
            if t:
                name = t.split('.')[-1].split(',')[0].replace('EX_', '')
                if name not in SKIP:
                    out.append(name)
            if isinstance(o.get('Path'), list):
                out.append('<' + '.'.join(o['Path']) + '>')
            for k in ('StackNode', 'Function', 'Value', 'VirtualFunctionName'):
                v = o.get(k)
                if v is None or isinstance(v, (dict, list)):
                    continue
                if k == 'StackNode' or (k == 'Value' and 'ObjectConst' in t):
                    out.append('@' + ref(v))
                else:
                    out.append('=' + str(v))
            for k, v in o.items():
                if k != '$type':
                    toks(v, out)
        elif isinstance(o, list):
            for v in o:
                toks(v, out)

    def text(o):
        out = []
        toks(o, out)
        return ' '.join(out)

    uber = next(e for e in exports if e.get('ObjectName') == sys.argv[2])
    bc = uber['ScriptBytecode']
    offs, pos = [], 0
    for st in bc:
        offs.append(pos)
        pos += size(st)
    at = {o: i for i, o in enumerate(offs)}
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    queue, seen, printed = [int(sys.argv[3])], set(), 0
    while queue and printed < limit:
        start = queue.pop(0)
        if start in seen or start not in at:
            continue
        seen.add(start)
        print(f'L{start}:')
        i = at[start]
        while i < len(bc) and printed < limit:
            st, t = bc[i], T(bc[i])
            printed += 1
            if i != at[start] and offs[i] in seen:
                print(f'    (falls into L{offs[i]})')
                break
            seen.add(offs[i])
            if t == 'EX_Jump':
                print(f'    goto L{st["CodeOffset"]}')
                queue.append(st['CodeOffset'])
                break
            if t == 'EX_JumpIfNot':
                print(f'    if not ({text(st["BooleanExpression"])[:220]}) goto L{st["CodeOffset"]}')
                queue.append(st['CodeOffset'])
            elif t == 'EX_PushExecutionFlow':
                print(f'    push L{st["PushingAddress"]}  (runs after the next pop)')
                queue.append(st['PushingAddress'])
            elif t == 'EX_PopExecutionFlow':
                print('    pop')
                break
            elif t == 'EX_PopExecutionFlowIfNot':
                print(f'    pop if not ({text(st["BooleanExpression"])[:220]})')
            elif t in ('EX_Return', 'EX_EndOfScript'):
                print('    return')
                break
            else:
                s = text(st)
                for skip in ('SkipOffsetConst', ):
                    if skip in s and 'Delay' in s:
                        # latent: resume offset is the SkipOffsetConst value
                        pass
                print(f'    {s[:300]}')
                for k in _latent(st):
                    print(f'      (latent resume -> L{k})')
                    queue.append(k)
            i += 1


def _latent(o):
    found = []

    def walk(x):
        if isinstance(x, dict):
            if T(x) == 'EX_SkipOffsetConst':
                found.append(x['Value'])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(o)
    return found


if __name__ == '__main__':
    main()
