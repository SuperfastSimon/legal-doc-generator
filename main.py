from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel
import os
import hashlib
import json
from datetime import datetime
from typing import Optional
import stripe

app = FastAPI(title="Legal Doc Generator", version="1.0.0")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

DOC_TYPES = {
    "nda": {"name": "Non-Disclosure Agreement", "price": 599, "description": "Protect your confidential information"},
    "freelance": {"name": "Freelance Contract", "price": 799, "description": "Professional service agreement"},
    "privacy": {"name": "Privacy Policy", "price": 999, "description": "GDPR & CCPA compliant privacy policy"},
    "tos": {"name": "Terms of Service", "price": 999, "description": "Comprehensive terms for your business"},
    "llc": {"name": "LLC Operating Agreement", "price": 1499, "description": "Complete LLC governance document"},
}

orders = {}

def generate_pdf_content(doc_type: str, business_name: str = "[Business Name]") -> str:
    now = datetime.now().strftime('%B %d, %Y')
    templates = {
        "nda": f"""NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of {now} by and between {business_name} ("Disclosing Party") and the undersigned party ("Receiving Party").

1. CONFIDENTIAL INFORMATION
The Receiving Party agrees to hold in strict confidence all information disclosed by the Disclosing Party.

2. OBLIGATIONS
The Receiving Party shall not disclose, publish, or disseminate Confidential Information to any third party without prior written consent.

3. TERM
This Agreement shall remain in effect for a period of two (2) years from the date of execution.

4. GOVERNING LAW
This Agreement shall be governed by applicable law.

SIGNATURE: _____________________ DATE: _____________""",
        "freelance": f"""FREELANCE SERVICE AGREEMENT

This Agreement is entered into as of {now} between {business_name} ("Client") and the Service Provider.

1. SERVICES
Service Provider agrees to perform the services as mutually agreed upon in writing.

2. PAYMENT
Client agrees to pay Service Provider the agreed fee upon completion of milestones.

3. INTELLECTUAL PROPERTY
Upon full payment, all work product becomes property of the Client.

4. INDEPENDENT CONTRACTOR
Service Provider is an independent contractor, not an employee.

5. TERMINATION
Either party may terminate with 14 days written notice.

CLIENT SIGNATURE: _____________________ DATE: _____________
PROVIDER SIGNATURE: _____________________ DATE: _____________""",
        "privacy": f"""PRIVACY POLICY

Last updated: {now}

{business_name} ("we", "us", or "our") operates this service.

1. INFORMATION WE COLLECT
We collect information you provide directly, usage data, and device information.

2. HOW WE USE YOUR INFORMATION
We use collected information to provide and improve our services, process transactions, and communicate with you.

3. DATA SHARING
We do not sell your personal data. We may share with service providers under confidentiality agreements.

4. YOUR RIGHTS (GDPR/CCPA)
You have the right to access, correct, delete, and port your personal data.

5. CONTACT
For privacy inquiries, contact us at privacy@{business_name.lower().replace(' ', '')}.com""",
        "tos": f"""TERMS OF SERVICE

Last updated: {now}

By accessing {business_name}'s services, you agree to these terms.

1. USE OF SERVICE
You agree to use the service lawfully and not to violate any applicable regulations.

2. INTELLECTUAL PROPERTY
All content and materials are property of {business_name}.

3. LIMITATION OF LIABILITY
{business_name} shall not be liable for indirect, incidental, or consequential damages.

4. TERMINATION
We reserve the right to terminate access for violation of these terms.

5. GOVERNING LAW
These terms are governed by applicable law.""",
        "llc": f"""LLC OPERATING AGREEMENT

{business_name}, LLC
Operating Agreement
Dated: {now}

ARTICLE I - ORGANIZATION
The Members hereby form a Limited Liability Company pursuant to applicable state law.

ARTICLE II - MANAGEMENT
The LLC shall be managed by its Members in proportion to their ownership interests.

ARTICLE III - CAPITAL CONTRIBUTIONS
Members shall contribute capital as agreed and recorded in the company books.

ARTICLE IV - PROFIT & LOSS DISTRIBUTION
Profits and losses shall be allocated in proportion to membership interests.

ARTICLE V - TRANSFERS
No member may transfer their interest without written consent of all other members.

ARTICLE VI - DISSOLUTION
The LLC may be dissolved by unanimous written agreement of all Members.

MEMBER SIGNATURE: _____________________ DATE: _____________"""
    }
    return templates.get(doc_type, "Document content not available.")

LANDING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Legal Doc Generator - Instant Legal Documents</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; }
  .hero { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0a0a0f 0%, #0a1a2e 50%, #0a0f1a 100%); padding: 40px 20px; }
  h1 { font-size: 2.8rem; font-weight: 800; background: linear-gradient(90deg, #3b82f6, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px; text-align: center; }
  .subtitle { font-size: 1.1rem; color: #9ca3af; margin-bottom: 48px; text-align: center; }
  .docs { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; margin-bottom: 40px; }
  .doc { background: rgba(255,255,255,0.05); border: 1px solid rgba(59,130,246,0.3);
    border-radius: 14px; padding: 24px; width: 200px; text-align: center; cursor: pointer; transition: all 0.3s; }
  .doc:hover, .doc.selected { border-color: #3b82f6; background: rgba(59,130,246,0.1); transform: translateY(-3px); }
  .doc h3 { font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; }
  .doc .price { font-size: 1.3rem; font-weight: 800; color: #3b82f6; margin-bottom: 6px; }
  .doc p { font-size: 0.75rem; color: #9ca3af; }
  .btn { background: linear-gradient(90deg, #3b82f6, #06b6d4); color: white; border: none;
    font-size: 1.05rem; font-weight: 700; padding: 14px 44px; border-radius: 10px; cursor: pointer; margin-top: 8px; }
  input[type=text] { background: rgba(255,255,255,0.07); border: 1px solid rgba(59,130,246,0.3);
    border-radius: 8px; padding: 10px 16px; color: #e0e0e0; font-size: 0.95rem; width: 300px; margin-bottom: 16px; }
</style>
</head>
<body>
<div class="hero">
  <h1>⚖️ Legal Docs in Seconds</h1>
  <p class="subtitle">Instant, professional legal documents — no lawyer needed</p>
  <div class="docs" id="docList">
    <div class="doc selected" onclick="selectDoc('nda', 5.99, this)">
      <h3>NDA</h3><div class="price">$5.99</div><p>Non-Disclosure Agreement</p>
    </div>
    <div class="doc" onclick="selectDoc('freelance', 7.99, this)">
      <h3>Freelance</h3><div class="price">$7.99</div><p>Service Agreement</p>
    </div>
    <div class="doc" onclick="selectDoc('privacy', 9.99, this)">
      <h3>Privacy Policy</h3><div class="price">$9.99</div><p>GDPR/CCPA Compliant</p>
    </div>
    <div class="doc" onclick="selectDoc('tos', 9.99, this)">
      <h3>Terms of Service</h3><div class="price">$9.99</div><p>Full ToS document</p>
    </div>
    <div class="doc" onclick="selectDoc('llc', 14.99, this)">
      <h3>LLC Agreement</h3><div class="price">$14.99</div><p>Operating Agreement</p>
    </div>
  </div>
  <form action="/create-checkout" method="POST">
    <input type="hidden" id="docInput" name="doc_type" value="nda">
    <input type="text" name="business_name" placeholder="Your business name (optional)" /><br>
    <button type="submit" class="btn" id="buyBtn">Get My NDA — $5.99</button>
  </form>
</div>
<script>
  let selectedDoc = 'nda', selectedPrice = 5.99, selectedName = 'NDA';
  function selectDoc(doc, price, el) {
    selectedDoc = doc; selectedPrice = price;
    document.querySelectorAll('.doc').forEach(d => d.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('docInput').value = doc;
    const names = {nda:'NDA',freelance:'Freelance Contract',privacy:'Privacy Policy',tos:'Terms of Service',llc:'LLC Agreement'};
    document.getElementById('buyBtn').textContent = 'Get My ' + names[doc] + ' \u2014 $' + price.toFixed(2);
  }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def landing(): return HTMLResponse(content=LANDING_HTML)

@app.get("/health")
def health(): return {"status": "ok", "service": "Legal Doc Generator", "version": "1.0.0"}

@app.post("/create-checkout")
async def create_checkout(request: Request):
    form = await request.form()
    doc_type = form.get("doc_type", "nda")
    business_name = form.get("business_name", "Your Business") or "Your Business"
    if doc_type not in DOC_TYPES:
        doc_type = "nda"
    doc = DOC_TYPES[doc_type]
    try:
        if not STRIPE_SECRET_KEY:
            order_id = hashlib.sha256(f"demo_{doc_type}_{datetime.now()}".encode()).hexdigest()[:16]
            orders[order_id] = {"doc_type": doc_type, "business_name": business_name, "status": "paid_demo", "created": datetime.now().isoformat()}
            return RedirectResponse(url=f"{BASE_URL}/success?order_id={order_id}", status_code=303)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price_data": {
                "currency": "usd",
                "product_data": {"name": doc["name"], "description": doc["description"]},
                "unit_amount": doc["price"]
            }, "quantity": 1}],
            mode="payment",
            success_url=f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/",
            metadata={"doc_type": doc_type, "business_name": business_name}
        )
        order_id = hashlib.sha256(session.id.encode()).hexdigest()[:16]
        orders[order_id] = {"stripe_session_id": session.id, "doc_type": doc_type, "business_name": business_name, "status": "pending", "created": datetime.now().isoformat()}
        return RedirectResponse(url=session.url, status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload)
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            doc_type = session.get("metadata", {}).get("doc_type", "nda")
            business_name = session.get("metadata", {}).get("business_name", "Your Business")
            order_id = hashlib.sha256(session["id"].encode()).hexdigest()[:16]
            content = generate_pdf_content(doc_type, business_name)
            orders[order_id] = {"doc_type": doc_type, "business_name": business_name, "status": "delivered", "content": content, "created": datetime.now().isoformat()}
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/success", response_class=HTMLResponse)
async def success(session_id: str = "", order_id: str = ""):
    if session_id and not order_id:
        order_id = hashlib.sha256(session_id.encode()).hexdigest()[:16]
    if order_id in orders and orders[order_id].get("status") in ["delivered", "paid_demo"]:
        if "content" not in orders[order_id]:
            doc_type = orders[order_id].get("doc_type", "nda")
            business_name = orders[order_id].get("business_name", "Your Business")
            orders[order_id]["content"] = generate_pdf_content(doc_type, business_name)
            orders[order_id]["status"] = "delivered"
    return HTMLResponse(content=f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Your Document is Ready!</title>
    <style>body{{background:#0a0a0f;color:#e0e0e0;font-family:'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;flex-direction:column;gap:16px;padding:40px;}}
    h1{{background:linear-gradient(90deg,#3b82f6,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.2rem;}}
    .doc-box{{background:rgba(59,130,246,0.07);border:1px solid rgba(59,130,246,0.3);border-radius:12px;padding:24px;max-width:700px;width:100%;white-space:pre-wrap;font-family:monospace;font-size:0.85rem;color:#cbd5e1;}}
    a{{color:#3b82f6;}}</style></head>
    <body><h1>📄 Your Document is Ready!</h1>
    <p>Order ID: <code>{order_id}</code></p>
    <div class="doc-box">{orders.get(order_id, {}).get('content', 'Processing...')}</div>
    <p><a href="/order/{order_id}/download">Download as .txt</a></p>
    </body></html>
    """)

@app.get("/order/{order_id}")
def get_order(order_id: str):
    o = orders.get(order_id)
    if not o: raise HTTPException(status_code=404, detail="Order not found")
    return {k: v for k, v in o.items() if k != "content"}

@app.get("/order/{order_id}/download")
def download_doc(order_id: str):
    o = orders.get(order_id)
    if not o: raise HTTPException(status_code=404, detail="Order not found")
    content = o.get("content", "Document not ready yet.")
    return Response(content=content, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="{o["doc_type"]}.txt"'})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
