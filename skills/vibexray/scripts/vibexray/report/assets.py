"""Inline CSS and JS for report.html. The report loads nothing from the network."""

# Coral #E07A5F is 2.9:1 on white, so it only fills bars and borders.
# Text that signals risk uses the darker coral #B5472E (5.4:1).
CSS = """
:root{--navy:#1F3A5F;--steel:#4A6FA5;--coral:#E07A5F;--coral-ink:#B5472E;
--coral-wash:#FBEDE8;--green:#5E9C76;--green-ink:#2F6B45;--grey-bar:#A9B1BC;
--ink:#2B2F36;--muted:#5B6470;--line:#DDE2E8;--panel:#F4F6F9}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:var(--ink);
font:17px/1.55 "Helvetica Neue",Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 32px}
a{color:var(--steel)}
code,pre{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px}
code{overflow-wrap:anywhere;word-break:break-word}
pre{margin:8px 0 4px;padding:12px 14px;background:var(--panel);border:1px solid var(--line);
border-radius:4px;overflow-x:auto;white-space:pre;max-width:100%;line-height:1.45}
pre code{overflow-wrap:normal;word-break:normal}
.top{border-bottom:1px solid var(--line)}
.top .wrap{display:flex;flex-wrap:wrap;gap:4px 20px;justify-content:space-between;
align-items:baseline;padding-top:14px;padding-bottom:14px}
.brand{font-weight:700;color:var(--navy)}
.meta{color:var(--muted);font-size:14px;min-width:0;overflow-wrap:anywhere}
.hero{padding:40px 0 8px}
h1{font-size:44px;line-height:1.12;color:var(--navy);margin:0 0 14px;letter-spacing:-.01em;
overflow-wrap:anywhere}
.lede{font-size:19px;margin:0 0 26px;max-width:44em}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
border-top:2px solid var(--navy);border-bottom:1px solid var(--line)}
.stat{padding:16px 20px 18px 0;min-width:0}
.stat+.stat{padding-left:20px;border-left:1px solid var(--line)}
.stat .n{font-size:56px;line-height:1;font-weight:700;color:var(--navy);
font-variant-numeric:tabular-nums}
.stat .n.risk{color:var(--coral-ink)}
.stat .n.zero{color:var(--muted)}
.stat .l{font-size:17px;font-weight:700;color:var(--ink);margin-top:8px}
.stat .d{font-size:14px;color:var(--muted);margin-top:2px}
.next{margin:22px 0 0;padding:14px 18px;background:var(--panel);border-left:4px solid var(--navy)}
.next b{color:var(--navy)}
.toc{display:flex;flex-wrap:wrap;gap:6px 22px;margin:22px 0 0;padding:0;list-style:none;
font-size:15px}
.sec{padding:44px 0 40px;border-top:1px solid var(--line);margin-top:36px}
.sec+.sec{margin-top:0}
h2{font-size:30px;line-height:1.2;color:var(--navy);margin:0 0 8px;overflow-wrap:anywhere}
h3{font-size:20px;line-height:1.3;color:var(--navy);margin:28px 0 10px}
.sub{color:var(--muted);margin:0 0 22px;max-width:44em}
.empty,.callout{margin:0;padding:16px 18px;background:var(--panel);border-radius:4px;max-width:44em}
.sub.after{margin-top:16px}
ul,ol{padding:0;margin:0;list-style:none}
.qs .q{display:grid;grid-template-columns:44px minmax(0,1fr);gap:4px 14px;padding:16px 0;
border-bottom:1px solid var(--line)}
.qs .q:first-child{border-top:1px solid var(--line)}
.qn{font-size:26px;line-height:1.1;font-weight:700;color:var(--steel)}
.qt{margin:0;font-size:19px;font-weight:700;color:var(--ink);min-width:0;overflow-wrap:anywhere}
.qw{margin:4px 0 0;color:var(--ink)}
.qf{margin:6px 0 0;color:var(--muted);font-size:14px}
.q>div{min-width:0}
.bar{display:flex;height:16px;margin:4px 0 10px;border-radius:2px;overflow:hidden;
background:var(--line)}
.bar span{display:block;min-width:4px}
.b-keep{background:var(--green)}.b-rewrite{background:var(--steel)}
.b-throwaway{background:var(--coral)}.b-check{background:var(--grey-bar)}
.legend{display:flex;flex-wrap:wrap;gap:4px 22px;margin:0 0 26px;font-size:15px}
.legend i{display:inline-block;width:10px;height:10px;margin-right:6px;border-radius:2px}
.lab{min-width:0;border-top:4px solid var(--line);padding-top:12px;margin:0 0 30px}
.lab .files{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:32px}
.lab.keep{border-color:var(--green)}.lab.rewrite{border-color:var(--steel)}
.lab.throwaway{border-color:var(--coral)}.lab.check{border-color:var(--grey-bar)}
.lab h3{margin:0;display:flex;align-items:baseline;gap:10px}
.lab h3 .c{font-size:30px;font-variant-numeric:tabular-nums}
.lab.keep h3 .c{color:var(--green-ink)}.lab.throwaway h3 .c{color:var(--coral-ink)}
.lab p.m{margin:4px 0 12px;color:var(--muted)}
.files li{padding:7px 0;border-top:1px solid var(--line);min-width:0}
.files code{font-size:13.5px}
.files .why{display:block;font-size:14px;color:var(--muted)}
details.more{margin-top:4px}
details.more>summary,.locs summary{cursor:pointer;color:var(--steel);font-size:15px}
details.more>summary{padding:8px 0}
.card{border:1px solid var(--line);border-left:4px solid var(--grey-bar);border-radius:4px;
padding:16px 18px;margin:0 0 16px;min-width:0}
.card.high{border-left-color:var(--coral)}.card.medium{border-left-color:var(--steel)}
.tags{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:14px}
.tag{display:inline-block;padding:1px 8px;border-radius:3px;background:var(--panel);
color:var(--navy);font-weight:700}
.tag.high{background:var(--coral-wash);color:var(--coral-ink)}
.tags .cnt{color:var(--muted)}
.tags .src{color:var(--muted)}
.tags .src::before{content:"\\00B7";margin-right:12px}
.tags .src.unchecked{color:var(--coral-ink);font-weight:700}
.ct{font-size:19px;line-height:1.35;color:var(--ink);margin:8px 0 6px;overflow-wrap:anywhere}
.fix{margin:0 0 10px;color:var(--muted);font-size:15px}
.fix b{color:var(--ink)}
.locs li{border-top:1px solid var(--line);padding:6px 0;min-width:0}
.locs summary{display:flex;flex-wrap:wrap;gap:2px 12px;align-items:baseline;list-style:none}
.locs summary::-webkit-details-marker{display:none}
.locs summary code{color:var(--ink);font-size:13.5px;min-width:0}
.locs summary .show{font-size:14px;white-space:nowrap}
.locs summary .show::before{content:"+ "}
.locs details[open] summary .show::before{content:"- "}
.locs .rel{margin:8px 0 0;font-size:14px;color:var(--muted)}
.locs .own{margin:8px 0 0;font-size:14px;color:var(--muted)}
.pages{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}
.page{border:1px solid var(--line);border-radius:4px;padding:14px;min-width:0}
.page img{display:block;width:100%;height:auto;border:1px solid var(--line)}
.page h3{margin:12px 0 2px}
.page .k{margin:10px 0 2px;font-size:14px;font-weight:700;color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chips li{background:var(--panel);border-radius:3px;padding:2px 8px;font-size:14px;
overflow-wrap:anywhere;min-width:0}
.errs li{color:var(--coral-ink);font-size:14px;overflow-wrap:anywhere}
.none{color:var(--muted);font-size:14px;margin:0}
.chat li{display:grid;grid-template-columns:110px minmax(0,1fr);gap:4px 16px;padding:12px 0;
border-top:1px solid var(--line)}
.chat time{color:var(--muted);font-size:15px;font-variant-numeric:tabular-nums}
.chat p{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}
.todo li{padding:4px 0}
.todo b{font-variant-numeric:tabular-nums;color:var(--navy)}
.foot{border-top:1px solid var(--line);margin-top:24px;padding:20px 0 40px;color:var(--muted);
font-size:14px}
@media (max-width:760px){
.wrap{padding:0 18px}
.hero{padding:24px 0 4px}
h1{font-size:30px}
.lede{font-size:17px;margin-bottom:18px}
.stat{padding:12px 10px 12px 0}
.stat+.stat{padding-left:10px}
.stat .n{font-size:38px}
.stat .l{font-size:14px;line-height:1.3}
.stat .d{display:none}
.next{margin-top:16px;padding:12px 14px}
.toc{display:none}
.sec{padding:32px 0 28px;margin-top:24px}
h2{font-size:24px}
.lab .files,.pages{grid-template-columns:minmax(0,1fr)}
.qs .q{grid-template-columns:30px minmax(0,1fr);gap:2px 10px}
.qn{font-size:21px}
.qt{font-size:17px}
.chat li{grid-template-columns:minmax(0,1fr)}
}
@media print{
body{font-size:12pt}
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
