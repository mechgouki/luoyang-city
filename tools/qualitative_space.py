"""Exact finite qualitative fragment: strict x/y orders, identity, and membership.

No metric distances, map pixels, priors, confidence votes, or implicit fronts.
Objects, temporal scopes and boundary references are separate equivalence sets.
A satisfying rank assignment is ONE witness, never a uniquely recovered plan.
"""
from collections import defaultdict, deque

class Union:
    def __init__(self): self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        if self.p[a] != a: self.p[a] = self.find(self.p[a])
        return self.p[a]
    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b: self.p[max(a,b)] = min(a,b)

class Model:
    def __init__(self, atoms):
        self.atoms = list(atoms)
        while True:
            ids = {a['id'] for a in self.atoms}
            eligible = [a for a in self.atoms if set(a.get('requires', [])) <= ids]
            if len(eligible) == len(self.atoms): break
            self.atoms = eligible
        self.uf = {k: Union() for k in ('entity','phase','reference')}
        self.alias_ids = []
        for a in self.atoms:
            if a['kind'] == 'alias':
                self.uf[a.get('domain','entity')].join(a['a'], a['b'])
                self.alias_ids.append(a['id'])
        self.edges = {'x': defaultdict(list), 'y': defaultdict(list)}
        self.nodes = set()
        self.memberships = defaultdict(list)
        self.conflict = None
        for a in self.atoms:
            kind = a['kind']
            if kind == 'order':
                u, v = self.key(a['less'],a), self.key(a['more'],a)
                self.edges[a['axis']][u].append((v,a['id']))
                self.nodes.update((u,v))
            elif kind == 'membership':
                key = (self.uf['entity'].find(a['node']),self.uf['phase'].find(a.get('phase','t0')),
                       self.uf['reference'].find(a['boundary']))
                self.memberships[key].append((a['value'],a['id']))
            elif kind == 'distinct':
                domain = a.get('domain','entity')
                if self.uf[domain].find(a['a']) == self.uf[domain].find(a['b']):
                    self.conflict = {'kind':'identity', 'atom_ids':[a['id']]+self.alias_ids}
            elif kind not in ('alias','note'):
                raise ValueError('Unsupported constraint kind: '+kind)
        for key, vals in self.memberships.items():
            if len({v for v,_ in vals}) > 1:
                self.conflict = {'kind':'membership','key':list(key),'atom_ids':[i for _,i in vals]+self.alias_ids}
                break
        self.ranks = {}
        for axis in ('x','y'):
            ranks,cycle = self.topological(axis)
            self.ranks[axis] = ranks
            if cycle: self.conflict = {'kind':'strict_order_cycle','axis':axis,'atom_ids':cycle+self.alias_ids}
        self.sat = self.conflict is None

    def key(self, node, a=None):
        a = a or {}
        return (self.uf['reference'].find(a.get('reference','R07-axes')),
                self.uf['phase'].find(a.get('phase','t0')),self.uf['entity'].find(node))

    def topological(self, axis):
        g=self.edges[axis]; ns=set(self.nodes)
        deg={n:0 for n in ns}; rank={n:0 for n in ns}
        for u in ns:
            for v,_ in g[u]: deg[v]+=1
        ready=sorted(n for n in ns if not deg[n]); out=[]
        while ready:
            u=ready.pop(0);out.append(u)
            for v,_ in sorted(g[u]):
                rank[v]=max(rank[v],rank[u]+1);deg[v]-=1
                if deg[v]==0: ready.append(v);ready.sort()
        if len(out)==len(ns): return rank,[]
        active={n for n in ns if deg[n]}; seen=set(); stack=[]; trail=[]
        def visit(u):
            seen.add(u);stack.append(u)
            for v,i in g[u]:
                if v in stack:
                    start=stack.index(v)
                    return trail[start:]+[i]
                if v in active and v not in seen:
                    trail.append(i);ans=visit(v)
                    if ans:return ans
                    trail.pop()
            stack.pop();return []
        for n in sorted(active):
            if n not in seen:
                cycle=visit(n)
                if cycle:return {},cycle
        raise AssertionError('Cycle extraction failed')

    def path(self, axis, less, more, context=None):
        u,v=self.key(less,context),self.key(more,context)
        if u==v:return None
        queue=deque([(u,[])]);seen={u}
        while queue:
            node,proof=queue.popleft()
            for nxt,aid in self.edges[axis].get(node,[]):
                if nxt==v:return proof+[aid]
                if nxt not in seen:seen.add(nxt);queue.append((nxt,proof+[aid]))
        return None

    def query(self, q):
        if not self.sat:return {'status':'inconsistent','proof':[]}
        if q['kind']=='order':
            p=self.path(q['axis'],q['less'],q['more'],q)
            if p:return {'status':'entailed','proof':p,'identity_assumptions':self.alias_ids}
            inv=self.path(q['axis'],q['more'],q['less'],q)
            if inv or self.key(q['less'],q)==self.key(q['more'],q):
                return {'status':'contradicted','proof':inv or self.alias_ids}
            return {'status':'undetermined','proof':[]}
        if q['kind']=='membership':
            key=(self.uf['entity'].find(q['node']),self.uf['phase'].find(q.get('phase','t0')),
                 self.uf['reference'].find(q['boundary']))
            vals=self.memberships.get(key,[])
            if not vals:return {'status':'undetermined','proof':[]}
            return {'status':'entailed' if vals[0][0]==q['value'] else 'contradicted',
                    'proof':[i for _,i in vals], 'identity_assumptions':self.alias_ids}
        if q['kind']=='alias':
            u=self.uf[q.get('domain','entity')]
            return {'status':'entailed' if u.find(q['a'])==u.find(q['b']) else 'undetermined','proof':self.alias_ids}
        raise ValueError('Unsupported query')

    def certificate(self):
        """Full rank witness for the admitted fragment, including unplotted nodes."""
        if not self.sat: return None
        ranks={axis:[{'context':list(n),'rank':value} for n,value in sorted(self.ranks[axis].items())]
               for axis in ('x','y')}
        edges=[{'axis':axis,'less':list(u),'more':list(v),'atom_id':aid}
               for axis in ('x','y') for u,vs in sorted(self.edges[axis].items()) for v,aid in vs]
        for edge in edges:
            axis=edge['axis'];assert self.ranks[axis][tuple(edge['less'])]<self.ranks[axis][tuple(edge['more'])]
        return {'rank_assignment':ranks,'checked_edges':edges,
                'membership_assignment':[{'context':list(k),'value':v[0][0],'atom_ids':[i for _,i in v]}
                    for k,v in sorted(self.memberships.items())],
                'active_atom_ids':[a['id'] for a in self.atoms],
                'scope':'完整定性约束的秩见证；不是实际距离或施工平面。'}

    def witness(self, nodes, axis_origin='ic_palace_avenue'):
        if not self.sat:raise ValueError('Inconsistent model has no witness')
        result={}
        for axis in ('x','y'):
            ranks=dict(self.ranks[axis]); groups=defaultdict(list)
            for node in nodes: groups[ranks.get(self.key(node),0)].append(self.key(node))
            values={}
            for rank,group in groups.items():
                group=sorted(set(group))
                for i,key in enumerate(group):values[key]=rank+(i+1)/(len(group)+1)*0.4
            anchor=self.key(axis_origin if axis=='x' else 'ic_changhe_palace')
            offset=values.get(anchor,ranks.get(anchor,0))
            result[axis]={node:round(values.get(self.key(node),ranks.get(self.key(node),0))-offset,9) for node in nodes}
        # This only checks nodes rendered; unrendered mention nodes still have a full rank model.
        for a in self.atoms:
            if a['kind']=='order' and a.get('phase','t0')=='t0' and a['less'] in nodes and a['more'] in nodes:
                assert result[a['axis']][a['less']]<result[a['axis']][a['more']],a['id']
        return result

def minimal_core(atoms):
    """Deletion-based subset-minimal core, NOT a minimum-cardinality core."""
    core=list(atoms)
    if Model(core).sat:return []
    for a in list(core):
        trial=[c for c in core if c['id']!=a['id']]
        if not Model(trial).sat:core=trial
    assert not Model(core).sat
    assert all(Model([b for b in core if b['id']!=a['id']]).sat for a in core)
    return [a['id'] for a in core]

def select(atoms, enabled, excluded_families=()):
    """Filter facts and remove assumptions whose supporting atoms disappeared."""
    selected=[a for a in atoms if a.get('group','always') in {'always',*enabled}
              and not set(a.get('families',[])).intersection(excluded_families)]
    while True:
        ids={a['id'] for a in selected}
        updated=[a for a in selected if set(a.get('requires',[]))<=ids]
        if len(updated)==len(selected):return updated
        selected=updated
