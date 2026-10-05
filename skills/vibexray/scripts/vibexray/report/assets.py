"""Inline CSS and JS for report.html. The report loads nothing from the network."""

# One accent: crimson marks what is fake or risky. Navy is real code and structure. Steel
# and mist are context. Crimson #B3261E is 6.6:1 on white, so it also works as text.
CSS = """
:root{--navy:#0B2545;--red:#B3261E;--steel:#4A6FA5;--mist:#C9D3DF;
--ink:#1B1F24;--muted:#5B6470;--line:#DDE3EA;--panel:#F3F5F8}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:var(--ink);
font:17px/1.55 "Helvetica Neue",Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 32px}
a{color:var(--navy)}
code,pre{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px}
code{overflow-wrap:anywhere;word-break:break-word}
pre{margin:8px 0 4px;padding:12px 14px;background:var(--panel);
border-radius:4px;overflow-x:auto;white-space:pre;max-width:100%;line-height:1.45}
pre code{overflow-wrap:normal;word-break:normal}
.hero{padding:56px 0 8px}
h1{font-size:44px;line-height:1.12;color:var(--navy);margin:0 0 14px;letter-spacing:-.01em;
overflow-wrap:anywhere}
.lede{font-size:19px;margin:0 0 26px;max-width:44em}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;margin:8px 0 0}
.stat{min-width:0}
.stat .n{font-size:56px;line-height:1;font-weight:700;color:var(--navy);
font-variant-numeric:tabular-nums}
.stat .n.risk{color:var(--red)}
.stat .n.zero{color:var(--muted)}
.stat .l{font-size:17px;font-weight:700;color:var(--ink);margin-top:8px}
.stat .d{font-size:14px;color:var(--muted);margin-top:2px}
.next{margin:28px 0 0;font-size:19px;max-width:44em}
.toc{display:flex;flex-wrap:wrap;gap:6px 22px;margin:22px 0 0;padding:0;list-style:none;
font-size:15px}
.sec{padding:48px 0 24px;margin-top:24px}
.sec+.sec{margin-top:0}
h2{font-size:30px;line-height:1.2;color:var(--navy);margin:0 0 8px;overflow-wrap:anywhere}
h3{font-size:20px;line-height:1.3;color:var(--navy);margin:28px 0 10px}
.sub{margin:0 0 22px;max-width:44em}
.empty,.callout{margin:0;max-width:44em}
.sub.after{margin-top:16px}
ul,ol{padding:0;margin:0;list-style:none}
.qs .q{display:grid;grid-template-columns:44px minmax(0,1fr);gap:4px 14px;padding:12px 0}
.qn{font-size:26px;line-height:1.1;font-weight:700;color:var(--navy)}
.qt{margin:0;font-size:19px;font-weight:700;color:var(--ink);min-width:0;overflow-wrap:anywhere}
.qw{margin:4px 0 0;color:var(--ink)}
.qf{color:var(--muted)}
.q>div{min-width:0}
.bar{display:flex;height:16px;margin:4px 0 10px;border-radius:2px;overflow:hidden;
background:var(--line)}
.bar span{display:block;min-width:4px}
.b-keep{background:var(--navy)}.b-rewrite{background:var(--steel)}
.b-throwaway{background:var(--red)}.b-check{background:var(--mist)}
.legend{display:flex;flex-wrap:wrap;gap:4px 22px;margin:0 0 26px;font-size:15px}
.legend i{display:inline-block;width:10px;height:10px;margin-right:6px;border-radius:2px}
.lab{min-width:0;margin:0 0 30px}
.lab .files{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:32px}
.lab h3{margin:0;display:flex;align-items:baseline;gap:10px}
.lab h3 .c{font-size:30px;font-variant-numeric:tabular-nums}
.lab.keep h3 .c{color:var(--navy)}.lab.rewrite h3 .c{color:var(--steel)}
.lab.throwaway h3 .c{color:var(--red)}.lab.check h3 .c{color:var(--muted)}
.lab p.m{margin:4px 0 12px;color:var(--muted)}
.files li{padding:6px 0;min-width:0}
.files code{font-size:13.5px}
.files .why{display:block;font-size:14px;color:var(--muted)}
details.more{margin-top:4px}
details.more>summary,.locs summary{cursor:pointer;color:var(--navy);font-size:15px}
details.more>summary{padding:8px 0}
.card{margin:0 0 32px;min-width:0}
.ct{font-size:19px;line-height:1.35;color:var(--ink);margin:0 0 6px;overflow-wrap:anywhere}
.fix{margin:0 0 8px;max-width:48em}
.pri{color:var(--navy)}.pri.high{color:var(--red)}
.fix .src{color:var(--muted)}
.fix .src.unchecked{color:var(--red);font-weight:700}
.locs li{padding:4px 0;min-width:0}
.locs summary{display:flex;flex-wrap:wrap;gap:2px 12px;align-items:baseline;list-style:none}
.locs summary::-webkit-details-marker{display:none}
.locs summary code{color:var(--ink);font-size:13.5px;min-width:0}
.locs summary .show{font-size:14px;white-space:nowrap}
.locs summary .show::before{content:"+ "}
.locs details[open] summary .show::before{content:"- "}
.locs .cl,.locs details[open] .op{display:none}
.locs details[open] .cl{display:inline}
.nw{white-space:nowrap}
.locs .rel{margin:8px 0 0;font-size:14px;color:var(--muted)}
.locs .own{margin:8px 0 0;font-size:14px;color:var(--muted)}
.pages{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}
.page{min-width:0}
.page img{display:block;width:100%;height:auto;border:1px solid var(--line)}
.page h3{margin:12px 0 2px}
.page .k{margin:10px 0 2px;font-size:14px;font-weight:700;color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chips li{background:var(--panel);border-radius:3px;padding:2px 8px;font-size:14px;
overflow-wrap:anywhere;min-width:0}
.errs li{color:var(--red);font-size:14px;overflow-wrap:anywhere}
.none{color:var(--muted);font-size:14px;margin:0}
.chat li{display:grid;grid-template-columns:110px minmax(0,1fr);gap:4px 16px;padding:8px 0}
.chat time{color:var(--muted);font-size:15px;font-variant-numeric:tabular-nums}
.chat p{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}
.chat li>div{min-width:0}
.chat .rep{margin-top:4px;color:var(--muted);font-size:14px}
.todo li{padding:4px 0}
.todo b{font-variant-numeric:tabular-nums;color:var(--navy)}
main{padding-bottom:48px}
@media (max-width:760px){
.wrap{padding:0 18px}
.hero{padding:24px 0 4px}
h1{font-size:30px}
.lede{font-size:17px;margin-bottom:18px}
.stats{gap:12px}
.stat .n{font-size:38px}
.stat .l{font-size:14px;line-height:1.3}
.stat .d{display:none}
.next{margin-top:18px;font-size:17px}
.toc{display:none}
.sec{padding:32px 0 28px;margin-top:24px}
h2{font-size:24px}
.lab .files,.pages{grid-template-columns:minmax(0,1fr)}
.qs .q{grid-template-columns:30px minmax(0,1fr);gap:2px 10px}
.qn{font-size:21px}
.qt{font-size:17px}
.chat li{grid-template-columns:minmax(0,1fr)}
.locs summary,details.more>summary{min-height:44px;align-items:center;display:flex}
pre{white-space:pre-wrap}
pre code{overflow-wrap:anywhere}
}
@page{margin:0.5in}
@media print{
body{font-size:12pt}
h2,h3,.sub,.ct{break-after:avoid;break-inside:avoid}
.bar{break-inside:avoid;break-after:avoid}
.todo,.legend{break-inside:avoid}
details.more>summary{display:none}
.toc{display:none}
.sec{break-inside:auto;padding:20px 0}
.card,.q,.page,.lab{break-inside:avoid}
pre{white-space:pre-wrap;overflow:visible}
.locs summary .show{display:none}
a{color:inherit;text-decoration:none}
}
"""

# Closed <details> do not print, so open all of them first.
JS = (
    "addEventListener('beforeprint',function(){"
    "document.querySelectorAll('details').forEach(function(d){d.open=true})});"
)
