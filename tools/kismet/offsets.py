"""In-memory Kismet sizes (UE4.26) for UAssetGUI JSON, to recover statement offsets.

usage: python offsets.py file.json UBERGRAPH_NAME [STATEMENT_INDEX ...]
Prints total size check, the event entry points, and who jumps to the given statements.
"""
import json, sys

PTR, NAME = 8, 12


def T(o):
    return o['$type'].split('.')[-1].split(',')[0] if isinstance(o, dict) and '$type' in o else None


def size(o):
    t = T(o)
    if t is None:
        raise ValueError('not an expression: %r' % (o,))
    s = 1
    g = o.get
    if t in ('EX_True', 'EX_False', 'EX_Self', 'EX_NoObject', 'EX_Nothing', 'EX_PopExecutionFlow', 'EX_EndOfScript'):
        return s
    if t in ('EX_InstanceVariable', 'EX_LocalVariable', 'EX_LocalOutVariable', 'EX_ObjectConst'):
        return s + PTR
    if t in ('EX_IntConst', 'EX_FloatConst', 'EX_SkipOffsetConst', 'EX_Jump', 'EX_PushExecutionFlow'):
        return s + 4
    if t == 'EX_ByteConst':
        return s + 1
    if t == 'EX_NameConst':
        return s + NAME
    if t in ('EX_VectorConst', 'EX_RotationConst'):
        return s + 12
    if t == 'EX_StringConst':
        return s + len(g('Value').encode('latin-1')) + 1
    if t == 'EX_UnicodeStringConst':
        return s + len(g('Value').encode('utf-16-le')) + 2
    if t == 'EX_SoftObjectConst':
        return s + size(g('Value'))
    if t == 'EX_JumpIfNot':
        return s + 4 + size(g('BooleanExpression'))
    if t == 'EX_PopExecutionFlowIfNot':
        return s + size(g('BooleanExpression'))
    if t == 'EX_ComputedJump':
        return s + size(g('CodeOffsetExpression'))
    if t == 'EX_Return':
        return s + size(g('ReturnExpression'))
    if t == 'EX_Let':
        return s + PTR + size(g('Variable')) + size(g('Expression'))
    if t in ('EX_LetBool', 'EX_LetObj'):
        return s + size(g('VariableExpression')) + size(g('AssignmentExpression'))
    if t == 'EX_LetValueOnPersistentFrame':
        return s + PTR + size(g('AssignmentExpression'))
    if t == 'EX_Context':
        return s + size(g('ObjectExpression')) + 4 + PTR + size(g('ContextExpression'))
    if t == 'EX_InterfaceContext':
        return s + size(g('InterfaceValue'))
    if t == 'EX_StructMemberContext':
        return s + PTR + size(g('StructExpression'))
    if t in ('EX_DynamicCast', 'EX_ObjToInterfaceCast'):
        return s + PTR + size(g('Target'))
    if t == 'EX_PrimitiveCast':
        return s + 1 + size(g('Target'))
    if t in ('EX_FinalFunction', 'EX_CallMath', 'EX_LocalFinalFunction'):
        return s + PTR + sum(size(p) for p in g('Parameters')) + 1
    if t in ('EX_VirtualFunction', 'EX_LocalVirtualFunction'):
        return s + NAME + sum(size(p) for p in g('Parameters')) + 1
    if t == 'EX_CallMulticastDelegate':
        return s + PTR + size(g('Delegate')) + sum(size(p) for p in g('Parameters')) + 1
    if t == 'EX_BindDelegate':
        return s + NAME + size(g('Delegate')) + size(g('ObjectTerm'))
    if t == 'EX_AddMulticastDelegate':
        return s + size(g('Delegate')) + size(g('DelegateToAdd'))
    if t == 'EX_RemoveMulticastDelegate':
        return s + size(g('Delegate')) + size(g('DelegateToAdd'))
    if t == 'EX_ClearMulticastDelegate':
        return s + size(g('DelegateToClear'))
    if t == 'EX_ArrayGetByRef':
        return s + size(g('ArrayVariable')) + size(g('ArrayIndex'))
    if t == 'EX_StructConst':
        return s + PTR + 4 + sum(size(v) for v in g('Value')) + 1
    if t == 'EX_ArrayConst':   # inner property, element count, elements, EX_EndArrayConst
        return s + PTR + 4 + sum(size(v) for v in g('Elements') or []) + 1
    if t == 'EX_SetArray':
        return s + size(g('AssigningProperty')) + sum(size(v) for v in g('Elements')) + 1
    if t == 'EX_SetMap':
        return s + size(g('MapProperty')) + 4 + sum(size(v) for v in g('Elements')) + 1
    if t == 'EX_SwitchValue':
        n = 2 + 4 + size(g('IndexTerm')) + size(g('DefaultTerm'))
        for c in g('Cases'):
            n += size(c['CaseIndexValueTerm']) + 4 + size(c['CaseTerm'])
        return s + n
    if t == 'EX_TextConst':
        v = g('Value')
        kind = v['TextLiteralType']
        kind = kind if isinstance(kind, str) else str(kind)
        n = 1
        if 'Empty' in kind:
            pass
        elif 'LocalizedText' in kind:
            n += size(v['LocalizedSource']) + size(v['LocalizedKey']) + size(v['LocalizedNamespace'])
        elif 'InvariantText' in kind:
            n += size(v['InvariantLiteralString'])
        elif 'LiteralString' in kind:
            n += size(v['LiteralString'])
        elif 'StringTableEntry' in kind:
            n += PTR + size(v['StringTableId']) + size(v['StringTableKey'])
        else:
            raise ValueError('text kind ' + kind)
        return s + n
    raise ValueError('unhandled ' + t)


def main():
    d = json.load(open(sys.argv[1], encoding='utf-8'))
    exports = d['Exports']
    uber = next(e for e in exports if e.get('ObjectName') == sys.argv[2])
    bc = uber['ScriptBytecode']
    offs, pos = [], 0
    for st in bc:
        offs.append(pos)
        pos += size(st)
    print('computed', pos, 'declared', uber.get('ScriptBytecodeSize'))
    index_of = {o: i for i, o in enumerate(offs)}
    # event stubs: functions calling the ubergraph with an IntConst entry point
    entries = {}
    for e in exports:
        if e is uber or not e.get('ScriptBytecode'):
            continue
        txt = json.dumps(e['ScriptBytecode'])
        if False:
            continue

        def find(o):
            if isinstance(o, dict):
                if T(o) in ('EX_LocalFinalFunction', 'EX_FinalFunction', 'EX_CallMath') and o.get('Parameters'):
                    p = o['Parameters'][0]
                    if T(p) == 'EX_IntConst':
                        entries[p['Value']] = e['ObjectName']
                for v in o.values():
                    find(v)
            elif isinstance(o, list):
                for v in o:
                    find(v)
        find(e['ScriptBytecode'])
    # jumps / pushes / latent resume points inside the ubergraph
    refs = []
    for i, st in enumerate(bc):
        def find(o):
            if isinstance(o, dict):
                t = T(o)
                if t in ('EX_Jump', 'EX_JumpIfNot'):
                    refs.append((o['CodeOffset'], i, t))
                elif t == 'EX_PushExecutionFlow':
                    refs.append((o['PushingAddress'], i, t))
                elif t == 'EX_SkipOffsetConst':
                    refs.append((o['Value'], i, 'latent'))
                for v in o.values():
                    find(v)
            elif isinstance(o, list):
                for v in o:
                    find(v)
        find(st)
    for arg in [a for a in sys.argv[3:] if not a.startswith("--")]:
        k = int(arg)
        # walk back to the start of the block: nearest statement that is an entry or a jump target
        targets = set(entries) | {r[0] for r in refs}
        j = k
        while j > 0 and offs[j] not in targets:
            j -= 1
        print(f'statement {k} offset {offs[k]} block starts at statement {j} offset {offs[j]}')
        if offs[j] in entries:
            print('  entry event:', entries[offs[j]])
        for r in refs:
            if r[0] == offs[j]:
                print(f'  reached from statement {r[1]} via {r[2]}')
    if '--entries' in sys.argv:
        for o in sorted(entries):
            print(o, index_of.get(o), entries[o])


if __name__ == '__main__':
    main()
