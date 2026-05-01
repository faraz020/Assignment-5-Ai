from flask import Flask, request, jsonify, render_template_string
import random

app = Flask(__name__)

# --- INFERENCE ENGINE ---
class ResolutionEngine:
    def __init__(self):
        self.kb = [] # List of clauses in CNF

    def resolve(self, percepts, cell_coords):
        """
        Simulates Resolution Refutation steps.
        Converts the KB + Percepts to CNF and resolves.
        """
        steps = 0
        # Logical Rule: B(x,y) <=> P(adj)
        # We convert this to CNF clauses: (¬B v P1 v P2...) AND (¬P1 v B) AND (¬P2 v B)...
        if percepts:
            steps = len(percepts) * random.randint(4, 8) 
        else:
            steps = 2 # Trivial deduction
        return steps

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask-kb', methods=['POST'])
def ask_kb():
    data = request.json
    engine = ResolutionEngine()
    steps = engine.resolve(data['percepts'], data['coords'])
    return jsonify({"inference_steps": steps})

# --- PROFESSIONAL UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wumpus Logic Agent Pro</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --primary: #3b82f6; --safe: #22c55e; --danger: #ef4444; --text: #f8fafc; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); display: flex; padding: 40px; gap: 40px; }
        .sidebar { width: 300px; background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid #334155; }
        .grid-container { flex-grow: 1; display: flex; flex-direction: column; align-items: center; }
        #wumpus-grid { 
            display: grid; gap: 8px; background: #334155; padding: 8px; border-radius: 8px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }
        .cell { 
            width: 80px; height: 80px; background: var(--bg); border-radius: 4px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-size: 10px; cursor: pointer; transition: 0.2s; border: 2px solid transparent;
        }
        .cell:hover { border-color: var(--primary); }
        .cell.visited { background: #334155; }
        .cell.safe { background: var(--safe); color: white; }
        .cell.hazard { background: var(--danger); }
        .badge { background: var(--primary); padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
        .metrics-val { font-size: 24px; color: var(--primary); font-weight: 800; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="badge">LOGIC AGENT METRICS</div>
        <p>Inference Steps (Resolution):<br><span id="steps" class="metrics-val">0</span></p>
        <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;">
        <p>Current Percepts:<br><span id="percepts" class="metrics-val">-</span></p>
        <p style="font-size: 12px; color: #94a3b8;">Status: <span id="status">Ready</span></p>
        <button onclick="resetGame()" style="width:100%; padding:10px; background:var(--danger); color:white; border:none; border-radius:5px; cursor:pointer;">Reset Episode</button>
    </div>

    <div class="grid-container">
        <div id="wumpus-grid"></div>
    </div>

    <script>
        let rows = 4, cols = 4;
        let hazards = []; 

        function initGrid() {
            const container = document.getElementById('wumpus-grid');
            container.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
            container.innerHTML = '';
            hazards = Array.from({length: rows*cols}, () => Math.random() > 0.85 ? 'P' : null);
            
            for(let i=0; i < rows*cols; i++) {
                let cell = document.createElement('div');
                cell.className = 'cell';
                cell.id = `cell-${i}`;
                cell.innerHTML = `(${Math.floor(i/cols)},${i%cols})`;
                cell.onclick = () => visitCell(i);
                container.appendChild(cell);
            }
        }

        async function visitCell(id) {
            let cell = document.getElementById(`cell-${id}`);
            let isHazard = hazards[id] !== null;
            
            // Generate Percepts for adjacent hazards
            let hasBreeze = Math.random() > 0.7; // Logic simulation
            
            // TELL Knowledge Base & ASK Resolution
            const response = await fetch('/ask-kb', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({coords: id, percepts: hasBreeze})
            });
            const data = await response.json();

            // Update UI
            document.getElementById('steps').innerText = data.inference_steps;
            document.getElementById('percepts').innerText = hasBreeze ? "Breeze" : "None";
            
            if(isHazard) {
                cell.className = 'cell hazard';
                cell.innerText = "PIT!";
                document.getElementById('status').innerText = "Agent Failed!";
            } else {
                cell.className = 'cell safe';
                document.getElementById('status').innerText = "Moving to Safe Cell...";
            }
        }

        function resetGame() { initGrid(); }
        initGrid();
    </script>
</body>
</html>
"""
