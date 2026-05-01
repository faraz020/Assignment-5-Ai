from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# The Logic Agent (Perceptron)
class Perceptron:
    def __init__(self):
        self.weights = [-0.6, -0.6] # Negative weights: Percepts = Danger
        self.bias = 0.5

    def predict(self, x):
        # Math: (x1 * w1) + (x2 * w2) + bias
        total = sum(xi * wi for xi, wi in zip(x, self.weights)) + self.bias
        return "SAFE" if total >= 0 else "DANGEROUS"

agent = Perceptron()

@app.route('/')
def home():
    return render_template_string(HTML_UI)

@app.route('/predict', methods=['POST'])
def predict():
    p = request.json.get('percepts', [0, 0])
    return jsonify({"status": agent.predict(p)})

HTML_UI = """
<!DOCTYPE html>
<html>
<body style="text-align:center; font-family:sans-serif; padding-top:100px; background:#f0f0f0;">
    <div style="background:white; display:inline-block; padding:40px; border-radius:15px; shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1>Agent Decision Engine</h1>
        <button style="padding:10px;" onclick="ask([0,0])">No Percepts</button>
        <button style="padding:10px;" onclick="ask([1,0])">Breeze</button>
        <button style="padding:10px;" onclick="ask([0,1])">Stench</button>
        <h2 id="out">Result: Waiting...</h2>
    </div>
    <script>
        async function ask(p) {
            const r = await fetch('/predict', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({percepts: p})
            });
            const d = await r.json();
            document.getElementById('out').innerText = "Result: " + d.status;
        }
    </script>
</body>
</html>
"""
