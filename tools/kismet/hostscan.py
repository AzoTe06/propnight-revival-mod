"""Listen-server host risk scan for Blueprint JSON exports (UAssetGUI).

usage: python hostscan.py DIR_OR_JSON... [--verbose]

On a dedicated server the owning client and the server are two copies of a pawn; on a
listen-server host they are the same object. Two patterns break the host's own pawn:

 A. "flag then server RPC": a local event sets a bool to true, then calls a server RPC
    whose flow tests that same bool (DropServ skipped because Stunned? was already set
    locally: the host's drop bug).
 B. "local + authority": an event tests both IsLocallyControlled and HasAuthority; the
    host takes only one of the branches (KatanaBlinkSpell: the end of the blink never ran).

Reports candidates only: every hit must be read by hand (trace.py / bp.py).
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from offsets import size, T  # noqa: E402

LOCAL_FUNCS = {'IsLocallyControlled', 'IsLocalController', 'IsLocalPlayerController', 'IsLocallyControlled?'}
LOCAL_RX = re.compile(r'^(Is|Get)?.*(IsLocal|LocalPlayer|LocallyControlled)', re.I)
AUTH_RX = re.compile(r'(HasAuthority|OnServer\?|IsServer)', re.I)
AUTH_FUNCS = {'HasAuthority', 'K2_GetRemoteRole', 'GetLocalRole', 'GetRemoteRole', 'IsServer', 'IsDedicatedServer'}


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def var_name(o):
    """Name of the variable an expression designates (instance / local / context member)."""
    t = T(o)
    if t in ('EX_InstanceVariable', 'EX_LocalVariable', 'EX_LocalOutVariable'):
        p = o['Variable']['New']['Path']
        return (t, p[-1] if p else '?')
    if t == 'EX_Context':
        inner = var_name(o.get('ContextExpression') or {})
        if inner:
            return ('EX_Context', inner[1])
    return None


def scan(path, server_reads, results, verbose):
    d = json.load(open(path, encoding='utf-8'))
    imports, exports = d.get('Imports', []), d['Exports']

    def ref(i):
        if isinstance(i, int) and i < 0 and -i - 1 < len(imports):
            return imports[-i - 1].get('ObjectName', str(i))
        if isinstance(i, int) and 0 < i <= len(exports):
            return exports[i - 1].get('ObjectName', str(i))
        return str(i)

    ubers = [e for e in exports if str(e.get('ObjectName', '')).startswith('ExecuteUbergraph') and e.get('ScriptBytecode')]
    if not ubers:
        return
    uber = ubers[0]
    bc = uber['ScriptBytecode']
    offs, pos = [], 0
    for st in bc:
        offs.append(pos)
        pos += size(st)
    at = {o: i for i, o in enumerate(offs)}
    flags = {e['ObjectName']: e.get('FunctionFlags', '') for e in exports if 'FunctionFlags' in e}
    entries = {}
    for e in exports:
        if e is uber or not e.get('ScriptBytecode'):
            continue

        def find(o, e=e):
            if T(o) in ('EX_LocalFinalFunction', 'EX_FinalFunction', 'EX_CallMath') and o.get('Parameters'):
                p = o['Parameters'][0]
                if T(p) == 'EX_IntConst' and ref(o.get('StackNode')) == uber['ObjectName']:
                    entries[e['ObjectName']] = p['Value']
        walk(e['ScriptBytecode'], find)

    # temp variable -> instance variables read to compute it (one level of taint, then closure)
    taint = {}
    for st in bc:
        if T(st) in ('EX_Let', 'EX_LetBool', 'EX_LetObj', 'EX_LetValueOnPersistentFrame'):
            dest = var_name(st.get('Variable') or st.get('VariableExpression') or {})
            src = st.get('Expression') or st.get('AssignmentExpression')
            reads = set()

            def rd(o, reads=reads):
                n = var_name(o)
                if n:
                    reads.add(n[1])
            walk(src, rd)
            if dest:
                taint.setdefault(dest[1], set()).update(reads)
    for _ in range(3):
        for k, v in taint.items():
            extra = set()
            for r in v:
                extra |= taint.get(r, set())
            v |= extra

    def calls_in(o):
        out = []

        def fn(x):
            t = T(x)
            if t in ('EX_VirtualFunction', 'EX_LocalVirtualFunction'):
                out.append(x['VirtualFunctionName'])
            elif t in ('EX_FinalFunction', 'EX_LocalFinalFunction', 'EX_CallMath'):
                out.append(ref(x.get('StackNode')))
        walk(o, fn)
        return out

    def reach(start):
        order, seen, queue = [], set(), [start]
        while queue:
            s = queue.pop(0)
            if s in seen or s not in at:
                continue
            i = at[s]
            while i < len(bc):
                if offs[i] in seen:
                    break
                seen.add(offs[i])
                st = bc[i]
                t = T(st)
                order.append(i)
                if t == 'EX_Jump':
                    queue.append(st['CodeOffset'])
                    break
                if t == 'EX_JumpIfNot':
                    queue.append(st['CodeOffset'])
                elif t == 'EX_PushExecutionFlow':
                    queue.append(st['PushingAddress'])
                elif t in ('EX_PopExecutionFlow', 'EX_Return', 'EX_EndOfScript'):
                    break
                elif t == 'EX_ComputedJump':
                    break

                def lat(x):
                    if T(x) == 'EX_SkipOffsetConst':
                        queue.append(x['Value'])
                walk(st, lat)
                i += 1
        return order

    def cond_reads(st):
        expr = st.get('BooleanExpression')
        if expr is None:
            return set()
        names = set()

        def rd(o):
            n = var_name(o)
            if n:
                names.add(n[1])
        walk(expr, rd)
        out = set(names)
        for n in names:
            out |= taint.get(n, set())
        return out

    name = os.path.splitext(os.path.basename(path))[0]
    info = {}
    for ev, off in entries.items():
        order = reach(off)
        sets_true, called, reads, local, auth = [], [], set(), False, False
        checks = []
        auth_return = False   # an authority test that ends the flow when true
        after_guard = []      # calls made after such a guard
        auth_temps = set()
        for i in order:
            st = bc[i]
            t = T(st)
            if t == 'EX_LetBool' and T(st.get('AssignmentExpression')) == 'EX_True':
                n = var_name(st.get('VariableExpression') or {})
                if n and n[0] != 'EX_LocalVariable':
                    sets_true.append((i, n[1]))
            if t in ('EX_JumpIfNot', 'EX_PopExecutionFlowIfNot'):
                reads |= cond_reads(st)
            if t == 'EX_JumpIfNot':
                cv = var_name(st.get('BooleanExpression') or {})
                nxt = bc[i + 1] if i + 1 < len(bc) else {}
                if cv and cv[1] in auth_temps and T(nxt) in ('EX_PopExecutionFlow', 'EX_Return'):
                    auth_return = True
            if auth_return:
                after_guard += [c for c in calls_in(st)]
            if t in ('EX_Let', 'EX_LetBool'):
                dv = var_name(st.get('Variable') or st.get('VariableExpression') or {})
                if dv and any(AUTH_RX.search(c) or c in AUTH_FUNCS for c in calls_in(st)):
                    auth_temps.add(dv[1])
            for c in calls_in(st):
                if (AUTH_RX.search(c) or c in AUTH_FUNCS) and t not in ('EX_Let', 'EX_LetBool'):
                    # out-parameter style call: KillerOnServer?(Result)
                    def outs(o):
                        n = var_name(o)
                        if n and n[0] == 'EX_LocalVariable':
                            auth_temps.add(n[1])
                    walk(st, outs)
            for c in calls_in(st):
                called.append((i, c))
                if c in LOCAL_FUNCS or LOCAL_RX.search(c):
                    local = True
                    checks.append(c)
                if c in AUTH_FUNCS or AUTH_RX.search(c) or c == 'IsDedicatedServer':
                    auth = True
                    checks.append(c)
            if 'SwitchHasAuthority' in json.dumps(st) or 'Role' in str(var_name(st.get('Variable') or {}) or ''):
                auth = True
        info[ev] = dict(auth_return=auth_return, after_guard=after_guard, checks=sorted(set(checks)), sets=sets_true, calls=called, reads=reads, local=local, auth=auth,
                        server='FUNC_NetServer' in flags.get(ev, ''), multicast='FUNC_NetMulticast' in flags.get(ev, ''))
        if info[ev]['server']:
            server_reads.setdefault(ev, set()).update(reads)
    results.append((name, info, flags))


def main():
    paths = []
    for a in sys.argv[1:]:
        if a.startswith('--'):
            continue
        if os.path.isdir(a):
            paths += [os.path.join(a, f) for f in sorted(os.listdir(a)) if f.endswith('.json')]
        else:
            paths.append(a)
    verbose = '--verbose' in sys.argv
    server_reads, results = {}, []
    for p in paths:
        try:
            scan(p, server_reads, results, verbose)
        except Exception as e:  # noqa: BLE001
            print(f'{p}: skipped ({type(e).__name__}: {e})')
    print('== A. flag set locally, then a server RPC that tests it')
    for name, info, flags in results:
        for ev, x in info.items():
            if x['server']:
                continue
            for ci, c in x['calls']:
                if c not in server_reads:
                    continue
                hit = sorted({v for si, v in x['sets'] if si < ci or True} & server_reads[c])
                if hit:
                    print(f'{name}.{ev} -> {c}: {", ".join(hit)}')
    report_c(results)
    print('== B. events testing both local control and authority')
    for name, info, flags in results:
        for ev, x in info.items():
            if x['local'] and x['auth']:
                kind = 'server' if x['server'] else 'multicast' if x['multicast'] else 'event'
                print(f'{name}.{ev} ({kind}): {", ".join(x["checks"])}')


def report_c(results):
    print('== C. "if server: stop", then a local-player branch (skipped on a listen-server host)')
    for name, info, flags in results:
        for ev, x in info.items():
            if x['auth_return'] and any(LOCAL_RX.search(c) or c in LOCAL_FUNCS for c in x['after_guard']):
                notable = sorted({c for c in x['after_guard'] if not re.match(r'^(Is|Get|Conv_|Make|Break|Array_|Not_|Boolean|Equal|Less|Greater|Add_|Subtract|Multiply|Divide|Select|K2_Get|Delay|PrintString|Concat|IsValid|Killer(IsLocalPlayer|OnServer)\?)', c)})
                print(f'{name}.{ev}: {", ".join(notable)[:300]}')


if __name__ == '__main__':
    main()
