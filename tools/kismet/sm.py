"""Dump anim blueprint state machines: python sm.py AnimBP.json"""
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
ce = next(e for e in d['Exports'] if 'ClassExport' in e.get('$type', ''))
nodes = [p.get('Name') for p in ce['LoadedProperties'] if str(p.get('Name', '')).startswith('AnimGraphNode_')]
def val(p):
    t = p.get('$type', '')
    if 'ArrayPropertyData' in t:
        return [val(x) for x in p['Value']]
    if 'StructPropertyData' in t:
        return {x['Name']: val(x) for x in p['Value']}
    return p.get('Value')
bsm = next(p for p in ce['Data'] if p['Name'] == 'BakedStateMachines')
for m in val(bsm):
    states = m['States']
    print('MACHINE', m['MachineName'], 'initial', states[m['InitialState']]['StateName'])
    for i, t in enumerate(m['Transitions']):
        idx = t.get('CanTakeDelegateIndex')
        rule = nodes[idx] if isinstance(idx, int) and 0 <= idx < len(nodes) else idx
        print(f"  {states[t['PreviousState']]['StateName']:>22} -> {states[t['NextState']]['StateName']:<22} rule={rule} blend={t.get('CrossfadeDuration')}")
