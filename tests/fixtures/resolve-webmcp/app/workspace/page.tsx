'use client';

import Link from 'next/link';
import { useState } from 'react';
import { toolMeta } from '@/lib/tool-defs';

type Activity = {
  tool: string;
  status: 'running' | 'done' | 'waiting' | 'error';
  detail: string;
};

const phases = ['Investigate', 'Explain', 'Confirm', 'Act'];

function normalizeResult(value: any) {
  if (typeof value === 'string') {
    try { return JSON.parse(value); } catch { return { raw: value }; }
  }
  return value ?? {};
}

const toolLabels: Record<string, string> = {
  get_order: 'Order record',
  get_shipping_status: 'Shipping evidence',
  check_delivery_issue: 'Issue analysis',
  check_support_eligibility: 'Policy check',
  create_support_case: 'Create support case',
  demo_agent: 'Demo simulation',
};

export default function Workspace() {
  const [problem, setProblem] = useState('My order says it was delivered yesterday, but I never received it.');
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [error, setError] = useState('');
  const [caseId, setCaseId] = useState<string | null>(null);
  const [phase, setPhase] = useState(0);
  const [evidence, setEvidence] = useState<{ order: any; shipping: any; issue: any; eligibility: any } | null>(null);
  const [demoRunning, setDemoRunning] = useState(false);

  const add = (a: Activity) => setActivities(v => [...v, a]);

  const executeNamed = async (name: string, input: Record<string, unknown>) => {
    if (typeof document === 'undefined' || !document.modelContext?.executeTool || !document.modelContext?.getTools) {
      throw new Error('WebMCP is unavailable. Enable WebMCP testing in Chrome and reload the page.');
    }
    const tools = await document.modelContext.getTools();
    const tool = tools.find((t: any) => t.name === name);
    if (!tool) throw new Error(`WebMCP tool not found: ${name}`);
    return normalizeResult(await document.modelContext.executeTool(tool, JSON.stringify(input)));
  };

  const runStep = async (tool: string, detail: string, input: Record<string, unknown>) => {
    add({ tool, status: 'running', detail: 'Calling the registered WebMCP tool…' });
    const result = await executeNamed(tool, input);
    setActivities(v => v.map((x, i) => i === v.length - 1 && x.tool === tool ? { ...x, status: 'done', detail } : x));
    return result;
  };

  const investigate = async () => {
    setRunning(true);
    setDone(false);
    setConfirmed(false);
    setCaseId(null);
    setError('');
    setActivities([]);
    setEvidence(null);
    setPhase(0);
    try {
      const order = await runStep('get_order', 'Order #1024 loaded · delivered · $129.99', { order_id: '1024' });
      setPhase(0);
      await new Promise(r => setTimeout(r, 250));
      const shipping = await runStep('get_shipping_status', 'Delivered 14:32 · signed by Front Desk · Building lobby', { order_id: '1024' });
      setPhase(1);
      await new Promise(r => setTimeout(r, 250));
      const issue = await runStep('check_delivery_issue', 'Delivery discrepancy analysis completed · customer report compared with shipment facts', { order_id: '1024', customer_report: problem });
      await new Promise(r => setTimeout(r, 250));
      const eligibility = await runStep('check_support_eligibility', 'Eligible for delivery investigation · confirmation required', { order_id: '1024', issue_type: issue.issue_type || 'delivered_but_not_received' });
      setEvidence({ order, shipping, issue, eligibility });
      setDone(true);
      setPhase(2);
      add({ tool: 'create_support_case', status: 'waiting', detail: 'State-changing action is paused until a human explicitly confirms.' });
    } catch (e: any) {
      setError(e.message || 'Investigation failed');
      setActivities(v => {
        const last = v[v.length - 1];
        if (last?.status === 'running') return v.map((x, i) => i === v.length - 1 ? { ...x, status: 'error', detail: e.message || 'Tool execution failed' } : x);
        return v;
      });
    } finally {
      setRunning(false);
    }
  };

  const confirm = async () => {
    setError('');
    try {
      if (!evidence) throw new Error('Run the investigation first.');
      const prep = await fetch('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'prepare' }),
      }).then(r => r.json());
      if (!prep.confirmation_token) throw new Error('Could not prepare confirmation');
      const created = await executeNamed('create_support_case', {
        confirmation_token: prep.confirmation_token,
        customer_id: 'C1001',
        order_id: '1024',
        issue_type: 'delivery_investigation',
        description: 'Customer reports a delivered package was not received.',
      });
      if (!created?.id) throw new Error(created?.error || 'Case creation failed');
      setCaseId(created.id);
      setConfirmed(true);
      setPhase(3);
      setActivities(v => v.map(x => x.tool === 'create_support_case' ? { ...x, status: 'done', detail: `Case #${created.id} created through WebMCP · investigation pending` } : x));
    } catch (e: any) {
      setError(e.message || 'Confirmation failed');
    }
  };

  const reset = async () => {
    await fetch('/api/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'reset' }),
    });
    setActivities([]);
    setDone(false);
    setConfirmed(false);
    setCaseId(null);
    setError('');
    setEvidence(null);
    setPhase(0);
  };

  const runDemo = async () => {
    setDemoRunning(true);
    setActivities([]);
    setError('');
    setDone(false);
    setConfirmed(false);
    setCaseId(null);
    setPhase(0);
    const demoSteps: { phase: number; detail: string; status?: Activity['status'] }[] = [
      { phase: 0, detail: 'Order #1024 loaded · delivered · $129.99' },
      { phase: 0, detail: 'Delivered 14:32 · signed by Front Desk · Building lobby' },
      { phase: 1, detail: 'Delivery discrepancy analysis completed' },
      { phase: 1, detail: 'Eligible for delivery investigation · confirmation required' },
      { phase: 2, detail: 'State-changing action paused · waiting for human confirmation', status: 'waiting' },
    ];
    for (let i = 0; i < demoSteps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 650));
      const step = demoSteps[i];
      setPhase(step.phase);
      setActivities(prev => [...prev, { tool: ['get_order', 'get_shipping_status', 'check_delivery_issue', 'check_support_eligibility', 'create_support_case'][i], status: step.status || 'done', detail: step.detail }]);
    }
    setDone(true);
    setDemoRunning(false);
  };

  const issue = evidence?.issue;
  const completedCalls = activities.filter(a => a.status === 'done').length;
  const activeLabel = running ? 'Agent is investigating' : demoRunning ? 'Demo is playing' : confirmed ? 'Action completed' : done ? 'Human decision required' : 'Ready for investigation';

  return (
    <main className="resolveShell">
      <style jsx global>{`
        :root { color-scheme: light; }
        * { box-sizing: border-box; }
        body { margin: 0; background: #f5f6f8; color: #111827; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        button, textarea { font: inherit; }
        .resolveShell { min-height: 100vh; padding: 28px 34px 42px; background: radial-gradient(circle at 76% -10%, rgba(91,76,255,.10), transparent 30%), #f5f6f8; }
        .topNav { max-width: 1540px; margin: 0 auto 24px; display:flex; align-items:center; justify-content:space-between; }
        .brand { display:flex; align-items:center; gap:13px; font-weight:800; letter-spacing:-.03em; }
        .brandMark { width:34px; height:34px; border-radius:10px; display:grid; place-items:center; background:#151a28; color:#fff; box-shadow:0 7px 18px rgba(17,24,39,.18); }
        .brandSub { color:#687386; font-size:14px; font-weight:600; }
        .connection { display:flex; align-items:center; gap:9px; padding:9px 13px; border:1px solid #e4e7ec; border-radius:999px; background:rgba(255,255,255,.78); color:#536071; font-size:12px; font-weight:700; }
        .liveDot { width:7px; height:7px; border-radius:50%; background:#22a06b; box-shadow:0 0 0 4px rgba(34,160,107,.10); }
        .hero { max-width:1540px; margin:0 auto 18px; display:flex; justify-content:space-between; gap:24px; align-items:flex-end; }
        .eyebrow { color:#6d7484; font-size:11px; font-weight:800; letter-spacing:.15em; text-transform:uppercase; margin-bottom:9px; }
        .hero h1 { margin:0; font-size:clamp(32px,4vw,48px); line-height:1; letter-spacing:-.055em; }
        .hero p { margin:13px 0 0; color:#697587; font-size:15px; }
        .actions { display:flex; gap:9px; flex-wrap:wrap; justify-content:flex-end; }
        .btn { border:1px solid #e1e5eb; border-radius:12px; min-height:44px; padding:0 16px; background:#fff; color:#222938; font-weight:750; cursor:pointer; transition:.18s ease; box-shadow:0 1px 1px rgba(17,24,39,.03); }
        .btn:hover:not(:disabled) { transform:translateY(-1px); box-shadow:0 7px 18px rgba(17,24,39,.08); }
        .btn:disabled { opacity:.55; cursor:not-allowed; }
        .btnPrimary { color:#fff; border-color:#151a28; background:#151a28; box-shadow:0 9px 24px rgba(21,26,40,.18); }
        .btnDemo { border-color:#d9d4ff; background:#f7f5ff; color:#4e43c8; }
        .statusBar { max-width:1540px; margin:0 auto 14px; padding:12px 15px; display:flex; justify-content:space-between; align-items:center; gap:12px; border:1px solid #e5e8ee; border-radius:14px; background:rgba(255,255,255,.72); }
        .statusMain { display:flex; align-items:center; gap:10px; font-size:13px; font-weight:750; }
        .statusIcon { width:25px; height:25px; display:grid; place-items:center; border-radius:8px; background:#f0f1f5; }
        .statusMeta { color:#8791a0; font-size:12px; }
        .phaseBar { max-width:1540px; margin:0 auto 18px; display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
        .phase { min-height:56px; padding:10px 13px; border:1px solid #e2e6ec; border-radius:14px; background:rgba(255,255,255,.78); display:flex; align-items:center; gap:11px; color:#8b94a4; }
        .phase span { width:28px; height:28px; border-radius:50%; display:grid; place-items:center; background:#f0f2f6; font-size:12px; font-weight:850; }
        .phase b { font-size:13px; }
        .phase.current { color:#4d43c7; border-color:#cfc9ff; background:#fbfaff; box-shadow:inset 0 0 0 1px rgba(92,76,255,.04); }
        .phase.current span { color:#fff; background:#5b50df; box-shadow:0 0 0 5px rgba(91,80,223,.10); }
        .phase.complete { color:#247a5b; border-color:#cce8dc; background:#fbfefc; }
        .phase.complete span { color:#247a5b; background:#e5f6ed; }
        .grid { max-width:1540px; margin:0 auto; display:grid; grid-template-columns:minmax(260px,.82fr) minmax(480px,1.55fr) minmax(300px,.95fr); gap:14px; align-items:stretch; }
        .card { border:1px solid #e4e7ec; border-radius:18px; background:rgba(255,255,255,.91); box-shadow:0 10px 35px rgba(20,27,45,.035); overflow:hidden; }
        .cardPad { padding:20px; }
        .cardHead { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px; }
        .cardTitle { font-size:11px; font-weight:850; letter-spacing:.13em; color:#717b8b; }
        .count { font-size:11px; font-weight:800; color:#8b94a4; padding:5px 8px; border-radius:999px; background:#f4f5f7; }
        .requestHero { padding:16px; border-radius:14px; background:linear-gradient(135deg,#f8f7ff,#f8fafc); border:1px solid #e9e7fb; }
        .requestText { margin:0; font-size:18px; line-height:1.42; letter-spacing:-.02em; font-weight:650; }
        .textarea { width:100%; min-height:104px; resize:vertical; margin-top:10px; padding:12px 13px; border:1px solid #e1e5eb; border-radius:12px; background:#fff; color:#334155; outline:none; font-size:13px; line-height:1.45; }
        .textarea:focus { border-color:#aaa2ff; box-shadow:0 0 0 3px rgba(91,80,223,.09); }
        .roleList { display:grid; gap:10px; margin-top:17px; }
        .role { display:grid; grid-template-columns:auto 1fr; gap:9px; align-items:start; font-size:12px; color:#687587; line-height:1.35; }
        .badge { display:inline-flex; align-items:center; justify-content:center; min-width:62px; padding:5px 8px; border-radius:999px; font-size:10px; letter-spacing:.05em; font-weight:850; }
        .badgeRead { color:#3f48a7; background:#eef0ff; }
        .badgeAction { color:#a44b18; background:#fff0e5; }
        .customerMeta { margin-top:18px; padding-top:15px; border-top:1px solid #edf0f3; display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .metaItem span { display:block; color:#9199a7; font-size:10px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:4px; }
        .metaItem strong { font-size:12px; }
        .timeline { min-height:100%; }
        .timelineList { position:relative; display:grid; gap:7px; }
        .timelineList:before { content:""; position:absolute; left:15px; top:18px; bottom:18px; width:1px; background:#e5e8ee; }
        .activity { position:relative; display:grid; grid-template-columns:32px 1fr; gap:10px; padding:11px 10px; border:1px solid #edf0f4; border-radius:13px; background:#fff; }
        .activity:hover { border-color:#dfe3ea; background:#fdfdff; }
        .activityNode { position:relative; z-index:1; width:31px; height:31px; display:grid; place-items:center; border-radius:10px; background:#f1f3f6; color:#657084; font-size:12px; font-weight:900; }
        .activityNode.done { color:#25785b; background:#e8f7ef; }
        .activityNode.waiting { color:#a85d18; background:#fff1e5; }
        .activityNode.error { color:#b93838; background:#ffe9e9; }
        .activityTop { display:flex; justify-content:space-between; gap:10px; align-items:center; }
        .toolName { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px; font-weight:800; color:#202838; }
        .toolLabel { margin-left:7px; color:#a0a7b3; font-size:10px; font-weight:650; }
        .activityStatus { font-size:9px; text-transform:uppercase; letter-spacing:.08em; font-weight:850; white-space:nowrap; }
        .success { color:#2a8765; } .warn { color:#aa641e; } .error { color:#ba3e3e; }
        .activityBody { margin-top:5px; color:#6e7888; font-size:11px; line-height:1.4; }
        .empty { min-height:380px; display:grid; place-items:center; text-align:center; padding:30px; color:#7b8595; }
        .emptyInner { max-width:280px; }
        .emptyIcon { width:48px; height:48px; margin:0 auto 14px; display:grid; place-items:center; border-radius:16px; background:linear-gradient(145deg,#f0efff,#f8f8ff); color:#5b50df; font-size:21px; box-shadow:0 9px 24px rgba(91,80,223,.10); }
        .empty strong { display:block; color:#222a38; font-size:14px; margin-bottom:6px; }
        .empty span { font-size:12px; line-height:1.45; }
        .recommendHero { padding:16px; border-radius:14px; background:linear-gradient(145deg,#f8f7ff,#fff); border:1px solid #e7e4ff; }
        .recommendTitle { display:flex; justify-content:space-between; gap:10px; align-items:center; }
        .recommendTitle strong { font-size:17px; letter-spacing:-.025em; }
        .recommendCopy { margin:10px 0 14px; color:#6b7687; font-size:12px; line-height:1.5; }
        .evidence { display:grid; gap:8px; }
        .evidenceRow { display:flex; justify-content:space-between; gap:10px; padding:8px 0; border-top:1px solid #edf0f3; font-size:11px; }
        .evidenceRow span:first-child { color:#8a93a1; }
        .evidenceRow strong { color:#273142; }
        .confirmBox { margin-top:12px; padding:14px; border:1px solid #f1dfcf; border-radius:14px; background:#fffaf5; }
        .confirmTitle { color:#9c4d17; font-size:11px; font-weight:850; letter-spacing:.08em; text-transform:uppercase; }
        .confirmBox p { margin:7px 0 12px; color:#7a6d61; font-size:11px; line-height:1.45; }
        .confirmButtons { display:flex; gap:8px; }
        .confirmButtons .btn { flex:1; min-height:38px; padding:0 10px; font-size:11px; }
        .successPanel { display:grid; gap:6px; }
        .successPanel strong { color:#207353; font-size:12px; }
        .successPanel span { color:#738080; font-size:11px; }
        .caseLink { color:#4c42c4; text-decoration:none; font-size:11px; font-weight:800; }
        .proof { max-width:1540px; margin:14px auto 0; display:grid; grid-template-columns:1.2fr 1fr; gap:14px; }
        .proofCard { padding:18px 20px; }
        .proofHeadline { margin-top:7px; font-size:15px; font-weight:800; letter-spacing:-.02em; }
        .proofSub { margin-top:5px; color:#8a93a1; font-size:11px; }
        .proofFlow { display:flex; align-items:center; justify-content:flex-end; gap:7px; flex-wrap:wrap; }
        .proofPill { padding:10px 12px; border:1px solid #e7e9ee; border-radius:12px; background:#fafbfc; font-size:11px; font-weight:800; color:#3d4757; }
        .proofArrow { color:#a1a9b5; font-weight:900; }
        .tools { max-width:1540px; margin:14px auto 0; }
        .toolWrap { display:flex; flex-wrap:wrap; gap:6px; margin-top:9px; }
        .toolChip { padding:6px 8px; border:1px solid #e4e7ec; border-radius:8px; background:#fff; color:#6e7787; font:10px ui-monospace,SFMono-Regular,Menlo,monospace; }
        .errorBox { max-width:1540px; margin:12px auto 0; padding:11px 13px; border-radius:11px; border:1px solid #f1caca; background:#fff4f4; color:#a53b3b; font-size:12px; }
        @media (max-width: 1120px) { .grid { grid-template-columns:1fr; } .proof { grid-template-columns:1fr; } .proofFlow { justify-content:flex-start; } .hero { align-items:flex-start; flex-direction:column; } .actions { justify-content:flex-start; } }
        @media (max-width: 700px) { .resolveShell { padding:18px 12px 28px; } .phaseBar { grid-template-columns:1fr 1fr; } .statusBar { align-items:flex-start; flex-direction:column; } .topNav { margin-bottom:18px; } }
      `}</style>

      <nav className="topNav">
        <div className="brand"><span className="brandMark">R</span><span>Resolve</span><span className="brandSub">Human-Agent Support</span></div>
        <div className="connection"><span className="liveDot" /> WebMCP · Connected</div>
      </nav>

      <header className="hero">
        <div>
          <div className="eyebrow">WEBMCP AGENT REHEARSAL · ORDER #1024</div>
          <h1>Investigation workspace</h1>
          <p>The agent investigates with structured business tools. You decide what changes.</p>
        </div>
        <div className="actions">
          <button className="btn" onClick={reset}>Reset demo</button>
          <button className="btn btnPrimary" onClick={investigate} disabled={running || demoRunning}>{running ? 'Agent investigating…' : 'Run agent investigation'}</button>
          <button className="btn btnDemo" onClick={runDemo} disabled={demoRunning || running}>{demoRunning ? 'Demo running…' : '▶ Demo Mode'}</button>
        </div>
      </header>

      <div className="statusBar">
        <div className="statusMain"><span className="statusIcon">✦</span>{activeLabel}</div>
        <div className="statusMeta">{completedCalls} completed calls · {activities.length} total events · shared state protected</div>
      </div>

      <div className="phaseBar">
        {phases.map((p, i) => (
          <div className={'phase ' + (i < phase ? 'complete' : i === phase ? 'current' : '')} key={p}>
            <span>{i < phase ? '✓' : i + 1}</span><b>{p}</b>
          </div>
        ))}
      </div>

      <div className="grid">
        <section className="card cardPad">
          <div className="cardHead"><div className="cardTitle">CUSTOMER REQUEST</div><span className="count">ORDER #1024</span></div>
          <div className="requestHero"><p className="requestText">{problem}</p></div>
          <textarea className="textarea" value={problem} onChange={e => setProblem(e.target.value)} disabled={running || demoRunning} />
          <div className="roleList">
            <div className="role"><span className="badge badgeRead">AGENT</span><span>Find facts, compare evidence and check policy.</span></div>
            <div className="role"><span className="badge badgeAction">HUMAN</span><span>Approve actions that change the shared state.</span></div>
          </div>
          <div className="customerMeta">
            <div className="metaItem"><span>Customer</span><strong>John Smith</strong></div>
            <div className="metaItem"><span>Account</span><strong>C1001</strong></div>
            <div className="metaItem"><span>Order value</span><strong>$129.99</strong></div>
            <div className="metaItem"><span>Reported</span><strong>Not received</strong></div>
          </div>
        </section>

        <section className="card cardPad timeline">
          <div className="cardHead"><div><div className="cardTitle">AGENT ACTIVITY TIMELINE</div><div style={{fontSize:'11px',color:'#98a0ad',marginTop:4}}>Live tool calls · structured inputs · structured results</div></div><span className="count">{activities.length} events</span></div>
          {activities.length === 0 ? (
            <div className="empty"><div className="emptyInner"><div className="emptyIcon">✦</div><strong>Ready for an agent run</strong><span>Run the scenario to execute the registered WebMCP tools for real.</span></div></div>
          ) : (
            <div className="timelineList">
              {activities.map((a, i) => (
                <div className="activity" key={i}>
                  <div className={'activityNode ' + a.status}>{a.status === 'done' ? '✓' : a.status === 'waiting' ? 'Ⅱ' : a.status === 'error' ? '!' : '·'}</div>
                  <div>
                    <div className="activityTop">
                      <div><span className="toolName">{a.tool}</span><span className="toolLabel">{toolLabels[a.tool] || 'WebMCP tool'}</span></div>
                      <span className={'activityStatus ' + (a.status === 'done' ? 'success' : a.status === 'error' ? 'error' : 'warn')}>{a.status === 'done' ? 'Completed' : a.status === 'waiting' ? 'Awaiting human' : a.status === 'error' ? 'Failed' : 'Running'}</span>
                    </div>
                    <div className="activityBody">{a.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card cardPad">
          <div className="cardHead"><div className="cardTitle">AGENT RECOMMENDATION</div><span className="count">{done ? 'READY' : 'PENDING'}</span></div>
          {!done ? (
            <div className="empty" style={{minHeight:380}}><div className="emptyInner"><div className="emptyIcon">◎</div><strong>No recommendation yet</strong><span>The agent will explain the support path after its WebMCP investigation.</span></div></div>
          ) : (
            <>
              <div className="recommendHero">
                <div className="recommendTitle"><strong>Delivery investigation</strong><span className="badge badgeAction">STATE-CHANGING</span></div>
                <p className="recommendCopy">{issue?.issue_detected ? 'The order is marked delivered, but the customer reports non-receipt. Evidence indicates a delivery discrepancy, so a support investigation is eligible.' : 'The available evidence does not support a delivery discrepancy.'}</p>
                <div className="evidence">
                  <div className="evidenceRow"><span>Order status</span><strong>Delivered</strong></div>
                  <div className="evidenceRow"><span>Delivery evidence</span><strong>Front Desk</strong></div>
                  <div className="evidenceRow"><span>Support policy</span><strong>Eligible</strong></div>
                </div>
              </div>
              <div className="confirmBox">
                <div className="confirmTitle">Human confirmation required</div>
                <p>Creating a support case changes shared business state. Resolve will not perform this action without your approval.</p>
                {!confirmed ? (
                  <div className="confirmButtons"><button className="btn" onClick={() => setPhase(2)}>Not now</button><button className="btn btnPrimary" onClick={confirm}>Review & confirm →</button></div>
                ) : (
                  <div className="successPanel"><strong>✓ Case #{caseId} created through WebMCP</strong><span>Investigation pending · action recorded in audit log.</span><Link className="caseLink" href={`/cases/${caseId}`}>Open case #{caseId} →</Link></div>
                )}
              </div>
            </>
          )}
        </section>
      </div>

      {error && <div className="errorBox">⚠ {error}</div>}

      <section className="proof">
        <div className="card proofCard"><div className="cardTitle">THE WEBMCP PROOF</div><div className="proofHeadline">Business-capability calls, not brittle page clicks.</div><div className="proofSub">The agent works through named capabilities while consequential changes remain under human control.</div></div>
        <div className="card proofCard"><div className="proofFlow"><span className="proofPill">04 investigation calls</span><span className="proofArrow">+</span><span className="proofPill">01 human-confirmed action</span><span className="proofArrow">→</span><span className="proofPill">01 support case</span></div></div>
      </section>

      <section className="tools"><div className="card proofCard"><div className="cardTitle">REGISTERED WEBMCP TOOLS</div><div className="toolWrap">{toolMeta.map(t => <span key={t.name} className="toolChip">{t.name}</span>)}</div></div></section>
    </main>
  );
}
