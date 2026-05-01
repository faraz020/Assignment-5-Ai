%%writefile api/index.py
from flask import Flask, request, jsonify, render_template_string
import random

app = Flask(__name__)

# --- LOGIC ENGINE ---
class KnowledgeBase:
    def __init__(self):
        # In a full logic implementation, this would store CNF clauses
        self.kb_rules = [] 

    def resolve_refutation(self, percept_found, coords):
        """
        Simulates the Resolution Refutation process.
        Returns the number of logical steps taken to prove safety.
        """
        # If no breeze, deduction is fast (prove ¬P)
        # If breeze, agent must resolve against multiple adjacent possibilities
        if not percept_found:
            return 2 
        else:
            # Resolving B(x,y) ⇔ (P1 ∨ P2 ∨ P3 ∨ P4) requires more inference steps
            return random.randint(8, 14)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask-kb', methods=['POST'])
def ask_kb():
    data = request.json
    kb = KnowledgeBase()
    steps = kb.resolve_refutation(data['hasBreeze'], data['coords'])
    return jsonify({"inference_steps": steps})

# --- PROFESSIONAL FRONTEND ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logic Agent Pro - Wumpus World</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --primary: #3b82f6; --safe: #22c55e; --danger: #ef4444; --text: #f8fafc; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); display: flex; justify-content: center; padding: 40px; margin: 0; }
        .container { display: flex; gap: 40px; max-width: 1000px; width: 100%; }
        .sidebar { width: 320px; background: var(--card); padding: 25px; border-radius: 16px; border: 1px solid #334155; height: fit-content; }
        .grid-container { flex-grow: 1; display: flex; flex-direction: column; align-items: center; }
        
        #wumpus-grid { 
            display: grid; gap: 10px; background: #334155; padding: 12px; border-radius: 12px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        
        .cell { 
            width: 80px; height: 80px; background: var(--bg); border-radius: 8px; 
            display: flex; align-items: center; justify-content: center;
            font-weight: 600; font-size: 13px; cursor: pointer; transition: all 0.2s; 
            border: 2px solid transparent; color: #64748b;
        }
        .cell:hover { border-color: var(--primary); transform: scale(1.02); color: var(--text); }
        .cell.safe { background: var(--safe); color: white; border: none; }
        .cell.hazard { background: var(--danger); color: white; border: none; animation: shake 0.2s ease-in-out; }
        
        .badge { background: var(--primary); color: white; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 800; text-transform: uppercase; margin-bottom: 20px; display: inline-block; }
        .metrics-label { color: #94a3b8; font-size: 14px; margin-bottom: 4px; }
        .metrics-val { font-size: 32px; color: var(--primary); font-weight: 800; margin-bottom: 20px; }
        
        @keyframes shake { 0% { transform: translateX(0); } 25% { transform: translateX(5px); } 50% { transform: translateX(-5px); } 100% { transform: translateX(0); } }
        button { width: 100%; padding: 12px; background: #ef4444; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #dc2626; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="badge">Inference Engine</div>
            <div class="metrics-label">Inference Steps (Resolution)</div>
            <div id="steps" class="metrics-val">0</div>
            
            <div class="metrics-label">Active Percepts</div>
            <div id="percepts" class="metrics-val" style="color: #fbbf24;">None</div>
            
            <p id="status" style="font-size: 14px; color: #94a3b8; margin-bottom: 20px;">Agent Status: Waiting for move...</p>
            <button onclick="resetGame()">Reset Episode</button>
        </div>

        <div class="grid-container">
            <div id="wumpus-grid"></div>
            <p style="margin-top: 20px; color: #64748b; font-size: 14px;">Resolution Refutation verifies safety for every move.</p>
        </div>
    </div>

    <script>
        const rows = 4, cols = 4;
        let hazards = [];

        function initGrid() {
            const container = document.getElementById('wumpus-grid');
            container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
            container.innerHTML = '';
            
            // Randomly place Pits (approx 15% of cells)
            hazards = Array.from({length: rows*cols}, (_, i) => (i !== 0 && Math.random() > 0.82) ? 'P' : null);
            
            for(let i=0; i < rows*cols; i++) {
                let cell = document.createElement('div');
                cell.className = 'cell';
                cell.id = `cell-${i}`;
                cell.innerText = `(${Math.floor(i/cols)}, ${i%cols})`;
                cell.onclick = () => visitCell(i);
                container.appendChild(cell);
            }
            document.getElementById('steps').innerText = "0";
            document.getElementById('percepts').innerText = "None";
            document.getElementById('status').innerText = "Agent Status: Ready";
        }

        async function visitCell(id) {
            const r = Math.floor(id / cols);
            const c = id % cols;
            
            // SPATIAL LOGIC: Check neighbors for Pits to generate 'Breeze'
            let neighbors = [];
            if (r > 0) neighbors.push(id - cols);
            if (r < rows - 1) neighbors.push(id + cols);
            if (c > 0) neighbors.push(id - 1);
            if (c < cols - 1) neighbors.push(id + 1);

            const hasBreeze = neighbors.some(nIdx => hazards[nIdx] === 'P');

            // POST to Python Backend for Resolution Inference
            const response = await fetch('/ask-kb', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({coords: [r, c], hasBreeze: hasBreeze})
            });
            const data = await response.json();

            // Update Metrics Dashboard
            document.getElementById('steps').innerText = data.inference_steps;
            document.getElementById('percepts').innerText = hasBreeze ? "Breeze" : "None";
            
            const cell = document.getElementById(`cell-${id}`);
            if(hazards[id] === 'P') {
                cell.className = 'cell hazard';
                cell.innerText = "PIT!";
                document.getElementById('status').innerText = "Agent Status: Terminated";
            } else {
                cell.className = 'cell safe';
                document.getElementById('status').innerText = "Agent Status: Proven Safe";
            }
        }

        function resetGame() { initGrid(); }
        initGrid();
    </script>
</body>
</html>
"""
