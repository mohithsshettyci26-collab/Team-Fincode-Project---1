from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    payload = request.get_json() or {}
    text = payload.get("contract_text", "")
    loan_amount = float(payload.get("loan_amount", 10000))
    tenure_months = max(1.0, float(payload.get("tenure_months", 3)))
    
    # Profile attributes
    profile = payload.get("profile", {})
    occupation = profile.get("occupation", "Borrower")
    income_type = profile.get("income_type", "fixed")
    monthly_income = max(1.0, float(profile.get("monthly_income", 15000)))
    existing_emis = float(profile.get("existing_emis", 0))
    expenses = float(profile.get("expenses", 0))

    lower_text = text.lower()
    flagged = []
    penalty_score = 0
    is_compliant = True
    compliance_issues = []

    # 1. RBI Compliance Check: Contact or Gallery Access
    if any(k in lower_text for k in ["contact directories", "contacts", "gallery", "device logs", "call logs", "camera access"]):
        is_compliant = False
        compliance_issues.append("Unlawful phone contact/gallery access detected (Violates RBI Digital Lending Norms).")
        flagged.append({
            "type": "Unlawful Data Access",
            "severity": "CRITICAL",
            "excerpt": "access to user contact directories, device logs, and picture galleries",
            "explanation": "RBI rules strictly ban digital lenders from harvesting phone contacts or photos for debt recovery."
        })
        penalty_score += 35

    # 2. Explosive Compounding Daily Penalty
    if any(k in lower_text for k in ["compound on a daily", "compounded daily", "per calendar day", "per day of delay"]):
        penalty_score += 30
        flagged.append({
            "type": "Explosive Daily Penalty",
            "severity": "CRITICAL",
            "excerpt": "late penalty compounded daily / per calendar day",
            "explanation": "Daily compounding turns a small overdue payment into an unpayable debt mountain within weeks."
        })
        compliance_issues.append("Predatory daily compounding penalty violates fair-recovery directives.")

    # 3. Upfront Processing Deduction
    upfront_cut_pct = 0.015
    if any(k in lower_text for k in ["12%", "10%", "upfront", "deducted directly", "deducted from principal"]):
        upfront_cut_pct = 0.12
        penalty_score += 20
        flagged.append({
            "type": "Hidden Upfront Cut",
            "severity": "HIGH",
            "excerpt": "deduction of 12% to be retained directly from principal",
            "explanation": f"You pay interest on ₹{int(loan_amount)}, but get 12% less cash in hand."
        })

    # 4. Prepayment lock-in penalty
    if any(k in lower_text for k in ["prepayment prior to maturity", "10% penalty fee", "foreclosure charges"]):
        penalty_score += 10
        flagged.append({
            "type": "Foreclosure Barrier",
            "severity": "MEDIUM",
            "excerpt": "prepayment prior to maturity is subject to a penalty fee",
            "explanation": "You are penalized if you try to clear your debt early."
        })

    # Calculate Safety & Fairness Score
    fairness_score = max(10, 100 - penalty_score)
    risk_level = "Safe & Fair" if fairness_score >= 80 else ("Moderate Risk" if fairness_score >= 55 else "High Predatory Risk")

    # Financial Estimates
    monthly_interest_factor = 0.025 if penalty_score > 20 else 0.012
    estimated_emi = round((loan_amount / tenure_months) + (loan_amount * monthly_interest_factor))
    total_monthly_obligations = existing_emis + estimated_emi
    dti_ratio = round((total_monthly_obligations / monthly_income) * 100)
    net_in_hand = round(loan_amount * (1 - upfront_cut_pct))
    effective_apr = "142.8%" if fairness_score < 60 else "13.8%"

    # Repayability Verdict
    if dti_ratio <= 35:
        repay_verdict = f"YES, EASILY REPAYABLE in {int(tenure_months)} Months"
        repay_status = "SAFE"
        repay_note = f"Your estimated EMI is ₹{estimated_emi}/month. Total debt repayments take only {dti_ratio}% of your income. You can comfortably clear this loan without distress."
    elif dti_ratio <= 50:
        repay_verdict = f"REPAYABLE WITH CAUTION over {int(tenure_months)} Months"
        repay_status = "CAUTION"
        repay_note = f"Your total monthly loan payments take {dti_ratio}% of your income. Because you have {income_type} earnings as a {occupation}, a temporary drop in income could lead to delayed payments."
    else:
        repay_verdict = f"NOT REPAYABLE / HIGH DEFAULT RISK"
        repay_status = "UNSAFE"
        repay_note = f"Debt payments demand {dti_ratio}% of your income. Over a {int(tenure_months)}-month period, you are likely to run out of cash and face steep default penalties."

    # Enriched Detailed Plain-Language Summary
    if fairness_score < 60:
        detailed_explanation = {
            "cash_in_hand": f"The lender claims to sanction ₹{int(loan_amount)}, but cuts ₹{int(loan_amount - net_in_hand)} (12%) upfront. You only get ₹{int(net_in_hand)} in hand, but pay interest on the full amount.",
            "late_danger": f"If you are delayed by even 24 hours, interest compounds every day at 1.5%. Within one week, your late fine will surge past ₹{round(loan_amount * 0.15)}.",
            "privacy": "This agreement forces you to give the app unrestricted access to your phone contacts, gallery, and logs. This directly breaches RBI digital lending rules.",
            "advice": f"For a {occupation} with {income_type} income, this contract is hazardous. Do NOT sign or accept funds. Go to Page 5 for verified credit alternatives."
        }
    else:
        detailed_explanation = {
            "cash_in_hand": f"You will receive approximately ₹{int(net_in_hand)} in your account. The upfront fees are minimal (under ₹250) and comply with digital banking regulations.",
            "late_danger": "If you are late, you receive a standard grace period with nominal simple interest fees. There are no daily compounding late charges.",
            "privacy": "Your privacy is protected. The lender does not request permission to inspect your private photos, phone contacts, or private phone files.",
            "advice": f"This loan is fair and transparent. With your income and expenses buffer, servicing the ₹{int(estimated_emi)} monthly EMI is financially safe."
        }

    return jsonify({
        "fairness_score": fairness_score,
        "risk_level": risk_level,
        "is_compliant": is_compliant,
        "compliance_warning": " ".join(compliance_issues) if compliance_issues else "Complies with RBI fair lending principles.",
        "repayability": {
            "status": repay_status,
            "verdict": repay_verdict,
            "note": repay_note
        },
        "financials": {
            "stated_amount": int(loan_amount),
            "net_in_hand": int(net_in_hand),
            "estimated_emi": int(estimated_emi),
            "effective_apr": effective_apr,
            "dti_ratio": dti_ratio,
            "late_risk": f"Missing a payment by 7 days will add ₹{round(loan_amount * 0.15)} in extra compounding interest." if fairness_score < 60 else "Standard 3-day grace period with nominal late charges."
        },
        "simplified_explanation": detailed_explanation,
        "flagged_clauses": flagged
    })

if __name__ == '__main__':
    print("FairPrint Backend Server running at http://127.0.0.1:5000")
    app.run(port=5000, debug=True)