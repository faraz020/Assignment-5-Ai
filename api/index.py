from flask import Flask, request, jsonify, send_from_directory
import random
import os
import json
from itertools import combinations

app = Flask(__name__, static_folder='../static')

# ─────────────────────────────────────────────
#  PROPOSITIONAL LOGIC & RESOLUTION REFUTATION
# ─────────────────────────────────────────────

class Clause:
    """A disjunction of literals. Each literal is a string like 'P_1_2' or '~P_1_2'."""
    def __init__(self, literals):
        self.literals = frozenset(literals)

    def __eq__(self, other):
        return self.literals == other.literals

    def __hash__(self):
        return hash(self.literals)

    def __repr__(self):
        return '{' + ', '.join(sorted(self.literals)) + '}'

    def is_empty(self):
        return len(self.literals) == 0


def negate(literal):
    if literal.startswith('~'):
        return literal[1:]
    return '~' + literal


def resolve(ci, cj):
    """Resolve two clauses. Returns list of resolvents (may be empty if nothing resolved)."""
    resolvents = []
    for lit in ci.literals:
        neg = negate(lit)
        if neg in cj.literals:
            new_lits = (ci.literals - {lit}) | (cj.literals - {neg})
            resolvents.append(Clause(new_lits))
    return resolvents


def pl_resolution(kb_clauses, query_literal):
    """
    Resolution Refutation: prove query_literal by refuting its negation.
    Returns (proved: bool, steps: int)
    """
    negated = Clause([negate(query_literal)])
    clauses = set(kb_clauses) | {negated}
    steps = 0
    while True:
        new = set()
        clause_list = list(clauses)
        for i in range(len(clause_list)):
            for j in range(i + 1, len(clause_list)):
                resolvents = resolve(clause_list[i], clause_list[j])
                steps += 1
                for r in resolvents:
                    if r.is_empty():
                        return True, steps
                    new.add(r)
                if steps > 5000:          # safety cap
                    return False, steps
        if new.issubset(clauses):
            return False, steps
        clauses |= new


# ─────────────────────────────────────────────
#  KNOWLEDGE BASE
# ─────────────────────────────────────────────

class KnowledgeBase:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.clauses = set()
        self.total_steps = 0

    def cell_id(self, r, c, kind):
        return f"{kind}_{r}_{c}"

    def tell_safe(self, r, c):
        """Assert cell (r,c) has no pit and no wumpus."""
        self.clauses.add(Clause([f'~P_{r}_{c}']))
        self.clauses.add(Clause([f'~W_{r}_{c}']))

    def tell_percept(self, r, c, breeze, stench):
        """
        Encode B_{r,c} <=> OR of P_{adj} and S_{r,c} <=> OR of W_{adj}.
        We convert biconditionals to CNF clauses.
        """
        neighbors = self._neighbors(r, c)

        # ── Breeze ──────────────────────────────
        if breeze:
            # B => (P_n1 | P_n2 | ...)
            self.clauses.add(Clause([f'P_{nr}_{nc}' for nr, nc in neighbors]))
            # Each P_ni => B  (already known, so no extra clause needed for us)
        else:
            # ~B => ~P for every neighbor
            for nr, nc in neighbors:
                self.clauses.add(Clause([f'~P_{nr}_{nc}']))

        # ── Stench ──────────────────────────────
        if stench:
            self.clauses.add(Clause([f'W_{nr}_{nc}' for nr, nc in neighbors]))
        else:
            for nr, nc in neighbors:
                self.clauses.add(Clause([f'~W_{nr}_{nc}']))

    def ask_safe(self, r, c):
        """
        Ask: is cell (r,c) safe (no pit AND no wumpus)?
        Returns (safe: bool, steps: int)
        """
        safe_pit, s1 = pl_resolution(self.clauses, f'~P_{r}_{c}')
        safe_wumpus, s2 = pl_resolution(self.clauses, f'~W_{r}_{c}')
        steps = s1 + s2
        self.total_steps += steps
        return safe_pit and safe_wumpus, steps

    def _neighbors(self, r, c):
        result = []
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                result.append((nr, nc))
        return result


# ─────────────────────────────────────────────
#  GAME STATE (stored in-memory per session via JSON body)
# ─────────────────────────────────────────────

def make_game(rows, cols):
    """Create a fresh game dict."""
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    start = (0, 0)

    # Place pits (≈20% of cells, not on start)
    pit_cells = [c for c in cells if c != start]
    num_pits = max(1, int(len(cells) * 0.20))
    pits = random.sample(pit_cells, min(num_pits, len(pit_cells)))

    # Place wumpus (not on start, not on pit)
    safe_for_wumpus = [c for c in cells if c != start and c not in pits]
    wumpus = random.choice(safe_for_wumpus) if safe_for_wumpus else None

    # Gold (not on start, not on hazard)
    safe_for_gold = [c for c in cells if c != start and c not in pits and c != wumpus]
    gold = random.choice(safe_for_gold) if safe_for_gold else start

    return {
        'rows': rows,
        'cols': cols,
        'agent': list(start),
        'pits': [list(p) for p in pits],
        'wumpus': list(wumpus) if wumpus else None,
        'gold': list(gold),
        'visited': [list(start)],
        'safe_cells': [list(start)],
        'confirmed_hazards': [],
        'kb_clauses': [],          # serialised as list-of-lists
        'total_steps': 0,
        'percepts': [],
        'status': 'playing',       # playing | won | dead
        'log': [],
        'score': 0,
    }


def get_percepts(game, r, c):
    rows, cols = game['rows'], game['cols']
    pits = [tuple(p) for p in game['pits']]
    wumpus = tuple(game['wumpus']) if game['wumpus'] else None
    neighbors = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append((nr, nc))
    breeze = any(n in pits for n in neighbors)
    stench = wumpus in neighbors if wumpus else False
    glitter = (r, c) == tuple(game['gold'])
    return breeze, stench, glitter


def deserialise_kb(game):
    kb = KnowledgeBase(game['rows'], game['cols'])
    kb.total_steps = game['total_steps']
    kb.clauses = {Clause(lits) for lits in game['kb_clauses']}
    return kb


def serialise_kb(game, kb):
    game['kb_clauses'] = [list(c.literals) for c in kb.clauses]
    game['total_steps'] = kb.total_steps


# ─────────────────────────────────────────────
#  AGENT AUTO-STEP LOGIC
# ─────────────────────────────────────────────

def agent_step(game):
    """Move the agent one step using KB inference. Returns updated game."""
    if game['status'] != 'playing':
        return game

    r, c = game['agent']
    rows, cols = game['rows'], game['cols']

    # Rebuild KB
    kb = deserialise_kb(game)

    # Observe percepts at current cell
    breeze, stench, glitter = get_percepts(game, r, c)
    percepts = []
    if breeze: percepts.append('Breeze')
    if stench: percepts.append('Stench')
    if glitter: percepts.append('Glitter')
    game['percepts'] = percepts

    # Tell KB
    kb.tell_safe(r, c)
    kb.tell_percept(r, c, breeze, stench)

    # Win on gold
    if glitter:
        game['status'] = 'won'
        game['score'] += 1000
        game['log'].append(f'🏆 Found gold at ({r},{c})!')
        serialise_kb(game, kb)
        return game

    # Evaluate neighbors
    neighbors = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append((nr, nc))

    # Prefer unvisited safe cells; fall back to any safe neighbor
    visited = [tuple(v) for v in game['visited']]
    safe_unvisited = []
    safe_visited = []
    inference_log = []

    for nr, nc in neighbors:
        is_safe, steps = kb.ask_safe(nr, nc)
        inference_log.append(f'ASK safe({nr},{nc}): {"✓" if is_safe else "✗"} [{steps} steps]')
        if is_safe:
            if [nr, nc] not in game['safe_cells']:
                game['safe_cells'].append([nr, nc])
            if (nr, nc) not in visited:
                safe_unvisited.append((nr, nc))
            else:
                safe_visited.append((nr, nc))

    game['log'].extend(inference_log[-4:])  # keep log short

    chosen = None
    if safe_unvisited:
        chosen = safe_unvisited[0]
    elif safe_visited:
        chosen = safe_visited[0]
    else:
        # No provably safe move — agent is stuck
        game['log'].append('⚠️ No safe move found — agent stuck.')
        game['status'] = 'stuck'
        serialise_kb(game, kb)
        return game

    # Move
    game['agent'] = list(chosen)
    game['score'] -= 1
    if list(chosen) not in game['visited']:
        game['visited'].append(list(chosen))

    # Check death
    pits = [tuple(p) for p in game['pits']]
    wumpus = tuple(game['wumpus']) if game['wumpus'] else None
    if chosen in pits:
        game['status'] = 'dead'
        game['score'] -= 1000
        game['log'].append(f'💀 Fell into pit at {chosen}!')
    elif chosen == wumpus:
        game['status'] = 'dead'
        game['score'] -= 1000
        game['confirmed_hazards'].append(list(chosen))
        game['log'].append(f'💀 Eaten by Wumpus at {chosen}!')
    else:
        game['log'].append(f'→ Moved to {chosen}')

    serialise_kb(game, kb)
    return game


# ─────────────────────────────────────────────
#  FLASK ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/new', methods=['POST'])
def new_game():
    data = request.get_json(force=True)
    rows = max(3, min(10, int(data.get('rows', 5))))
    cols = max(3, min(10, int(data.get('cols', 5))))
    game = make_game(rows, cols)
    # Initialise KB with start cell safe
    kb = KnowledgeBase(rows, cols)
    kb.tell_safe(0, 0)
    serialise_kb(game, kb)
    return jsonify(game)

@app.route('/api/step', methods=['POST'])
def step():
    game = request.get_json(force=True)
    game = agent_step(game)
    return jsonify(game)

@app.route('/api/reveal', methods=['POST'])
def reveal():
    """Reveal hidden hazards (for end-of-game display)."""
    game = request.get_json(force=True)
    return jsonify(game)

if __name__ == '__main__':
    app.run(debug=True)
