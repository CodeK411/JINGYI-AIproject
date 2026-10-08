"use strict";
import {PolicyEngine} from "./engine.js";
let enginePromise;
const getEngine=()=>enginePromise ||= PolicyEngine.load().catch(error=>{enginePromise=null;throw error;});
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const percentage = value => `${(Number(value) * 100).toFixed(1)}%`;
const regionName = value => ({CN:"中国区",GB:"英国区",ALL:"全球通用"}[value] || value);
const employeeName = value => ({full_time:"正式员工",intern:"实习生",contractor:"外包合同工",secure_role:"涉密岗位",all:"全员"}[value] || value);
const modeName = value => ({full:"完整链路",hybrid_temporal:"混合检索 + 过滤",hybrid:"混合检索",dense:"Dense 基线"}[value] || value);
let metadata = null;
let askSequence = 0;
let compareSequence = 0;
let compared = false;
const examples = {
  travel:{query:"国内出差饭补多少？",region:"CN",employee_type:"full_time",as_of:"2025-06-01"},
  intern:{query:"实习生学习预算多少？",region:"CN",employee_type:"intern",as_of:"2025-06-01"},
  conflict:{query:"客户礼品上限是多少？",region:"CN",employee_type:"full_time",as_of:"2025-06-01"},
  unknown:{query:"公司股票期权归属周期是什么？",region:"CN",employee_type:"full_time",as_of:"2025-06-01"}
};

async function requestJSON(path, body) {
  const engine=await getEngine();
  if(path==="/v1/demo")return engine.info();
  if(path==="/v1/ask")return engine.ask(body);
  if(path==="/v1/compare")return engine.compare(body);
  throw new Error("未知操作。");
}

function loadingHTML(text) {
  return `<div class="panel empty-state" role="status"><div class="empty-mark">V /</div><h2>${escapeHTML(text)}</h2><p>正在检索制度、验证适用性并检查冲突…</p></div>`;
}
function errorHTML(error, action) {
  return `<div class="panel error-state" role="alert"><h2>这次查询未完成</h2><p>${escapeHTML(error.message)}</p><button type="button" data-retry="${action}">重试</button></div>`;
}

function citationButton(id, hits, prefix) {
  const index = hits.findIndex(hit => hit.chunk_id === id);
  if (index < 0) return escapeHTML(`[${id}]`);
  return `<button type="button" class="citation-link" data-citation="${prefix}-${index}" aria-label="查看第 ${index+1} 条引用证据">[${index+1}]</button>`;
}
function answerHTML(response, prefix) {
  return String(response.answer).split(/(\[[^\[\]]+::[^\[\]]+\])/g).map(part => {
    const id = part.startsWith("[") && part.endsWith("]") ? part.slice(1,-1) : null;
    return id && response.citations.includes(id) ? citationButton(id,response.hits,prefix) : escapeHTML(part);
  }).join("");
}

function sourceHTML(hit, index, citations, prefix) {
  const cited = citations.includes(hit.chunk_id);
  const signals = Object.entries(hit.signals).filter(([key]) => ["dense","bm25","rrf","rerank","cross_encoder","scope_specificity","authority"].includes(key));
  const labels = {dense:"Dense",bm25:"BM25",rrf:"RRF",rerank:"重排",cross_encoder:"Cross-Encoder",scope_specificity:"范围匹配",authority:"权威权重"};
  return `<details class="source ${cited ? "cited" : ""}" id="${prefix}-${index}" ${cited ? "open" : ""}>
    <summary><span class="source-rank">${index+1}</span><div><div class="source-title">${escapeHTML(hit.title)} ${cited ? '<span class="tag blue">已引用</span>' : ""}</div><div class="source-heading">${escapeHTML(hit.heading)}</div></div><span class="source-plus" aria-hidden="true">+</span></summary>
    <div class="source-tags"><span>v${escapeHTML(hit.version)}</span><span>${escapeHTML(hit.effective_from)} — ${escapeHTML(hit.effective_to || "持续有效")}</span><span>${escapeHTML(hit.regions.map(regionName).join(" / "))}</span><span>${escapeHTML(hit.employee_types.map(employeeName).join(" / "))}</span></div>
    ${(hit.rules || []).length ? `<div class="source-rules"><span class="tiny-label">制度中的结构化规则</span>${hit.rules.map(rule => `<p>${escapeHTML(rule.statement || `${rule.label}: ${rule.value} ${rule.unit || ""}`)}</p>`).join("")}</div>` : ""}
    <div class="source-text">${escapeHTML(hit.text)}</div><div class="source-id">${escapeHTML(hit.chunk_id)}</div>
    <div class="signals">${signals.map(([key,value]) => `<span class="signal">${labels[key]} ${Number(value).toFixed(key === "rrf" ? 4 : 3)}</span>`).join("")}</div>
  </details>`;
}
function evidenceHTML(response,prefix,title="检索证据") {
  return `<section class="panel evidence-panel"><div class="panel-heading"><h2>${title}</h2><span class="step-tag">${response.hits.length} SOURCES</span></div>${response.hits.length ? response.hits.map((hit,index) => sourceHTML(hit,index,response.citations,prefix)).join("") : '<p class="field-help">没有匹配的有效条款。</p>'}</section>`;
}
function conflictsHTML(response) {
  return response.conflicts.map(conflict => `<div class="conflict-box"><strong>${conflict.status === "unresolved" ? "同等优先级制度存在冲突" : "已按适用范围、权威及日期解决冲突"}</strong>候选规则值：${escapeHTML(conflict.values.join(" / "))}<small>${escapeHTML(conflict.rule_key)}</small>${conflict.source_ids.map(id => `<small>来源：${escapeHTML(id)}</small>`).join("")}</div>`).join("");
}
function resultHTML(response,context,prefix,title="制度回答",showTrace=true) {
  const threshold = metadata?.threshold ?? 0.44;
  return `<section class="panel answer-panel ${response.answerable ? "" : "refused"}"><div class="result-heading"><h2>${title}</h2><span class="tag ${response.answerable ? "" : "warning"}">${response.answerable ? "已生成引用" : "需人工确认"}</span></div>
    <div class="query-snapshot">${escapeHTML(context.as_of)} · ${escapeHTML(regionName(context.region))} · ${escapeHTML(employeeName(context.employee_type))} · ${escapeHTML(modeName(response.mode))}</div>
    <div class="answer-text">${answerHTML(response,prefix)}</div>${conflictsHTML(response)}
    <div class="answer-meta"><span>证据分数 <strong>${Number(response.confidence).toFixed(3)}</strong></span><span>拒答阈值 <strong>${Number(threshold).toFixed(2)}</strong></span><span>检索耗时 <strong>${Number(response.latency_ms).toFixed(1)} ms</strong></span><span>有效引用 <strong>${response.citations.length}</strong></span></div>
    ${showTrace ? `<div class="trace">证据分数为启发式评分，并非正确率概率。自由提问可能出现检索错误，请核对原文。</div>` : ""}</section>`;
}

async function ask() {
  const sequence = ++askSequence;
  const context = {query:$("question").value.trim(),as_of:$("as-of").value,region:$("region").value,employee_type:$("employee").value,mode:$("pipeline").value,generator:"extractive",top_k:5};
  if (context.query.length < 2) { $("question").focus(); return; }
  $("ask-submit").disabled=true;
  $("ask-submit").textContent="正在检索…";
  $("ask-results").innerHTML=loadingHTML("正在核对适用制度");
  try {
    const response = await requestJSON("/v1/ask",context);
    if (sequence !== askSequence) return;
    $("ask-results").innerHTML=resultHTML(response,context,"ask-source")+evidenceHTML(response,"ask-source");
    return response;
  } catch(error) {
    if (sequence === askSequence) $("ask-results").innerHTML=errorHTML(error,"ask");
    return {error:error.message};
  } finally {
    if (sequence === askSequence) {$("ask-submit").disabled=false;$("ask-submit").textContent="检索并回答";}
  }
}

async function compare() {
  const sequence = ++compareSequence;
  const context = {query:$("compare-question").value.trim(),date_a:$("date-a").value,date_b:$("date-b").value,region:$("compare-region").value,employee_type:$("compare-employee").value};
  if (context.query.length < 2) {$("compare-question").focus();return;}
  if (context.date_a > context.date_b) {$("compare-results").innerHTML=errorHTML(new Error("较早日期不能晚于较晚日期，请调整日期后重试。"),"compare");return;}
  $("compare-submit").disabled=true;
  $("compare-submit").textContent="正在比较…";
  $("compare-results").innerHTML=loadingHTML("正在比较两个日期的有效规则");
  try {
    const result = await requestJSON("/v1/compare",context);
    if (sequence !== compareSequence) return;
    const changes = Object.entries(result.changed_rules);
    const changeHTML = changes.map(([key,change]) => {
      const label = change.after[0]?.label || change.before[0]?.label || key;
      return `<div class="change-row"><h3>${escapeHTML(label)}</h3>${["before","after"].map((side,index) => `<div class="change-side"><small>${index === 0 ? context.date_a : context.date_b}</small><div class="change-value">${escapeHTML(change[side][0]?.value ?? "无规则")}</div>${change[side].map(rule => `<p>${escapeHTML(rule.statement)}</p>${citationButton(rule.citation_id,index === 0 ? result.evidence_a : result.evidence_b,index === 0 ? "before-source" : "after-source")}`).join("")}</div>`).join("")}</div>`;
    }).join("");
    $("compare-results").innerHTML=`<section class="panel change-panel"><div class="result-heading"><h2>${!result.comparable ? "无法可靠比较" : changes.length ? `${changes.length} 条相关规则发生变化` : "相关规则值没有变化"}</h2><span class="tag ${result.comparable ? "blue" : "warning"}">${result.comparable ? "规则值比较" : "需人工确认"}</span></div><p>${escapeHTML(result.reason)}</p>${changeHTML}</section><div class="comparison-grid"><div class="result-column">${resultHTML(result.answer_a,{...context,as_of:context.date_a},"before-source","较早日期的回答",false)}${evidenceHTML(result.answer_a,"before-source","较早日期的证据")}</div><div class="result-column">${resultHTML(result.answer_b,{...context,as_of:context.date_b},"after-source","较晚日期的回答",false)}${evidenceHTML(result.answer_b,"after-source","较晚日期的证据")}</div></div>`;
    return result;
  } catch(error) { if(sequence === compareSequence) $("compare-results").innerHTML=errorHTML(error,"compare"); }
  finally {if(sequence === compareSequence){$("compare-submit").disabled=false;$("compare-submit").textContent="比较版本";}}
}

function renderEvaluation() {
  if (!metadata) {$("eval-results").innerHTML=errorHTML(new Error("评测报告尚未加载，请重试。"),"metadata");return;}
  const report = metadata.benchmark;
  const baseline = report.results.find(row => row.mode === "dense");
  const full = report.results.find(row => row.mode === "full");
  const labels = {dense:"LSA Dense 基线",hybrid:"Dense + BM25 + RRF",hybrid_temporal:"+ 时间 / 地区 / 人群过滤",full:"+ 可解释特征重排"};
  $("eval-results").innerHTML=`<div class="kpi-grid"><div class="panel kpi"><div class="kpi-label">第一条证据命中率 · Hit@1</div><div class="kpi-value">${percentage(full["hit@1"])}<small>完整链路</small></div><div class="kpi-note">相较基线增加 ${((full["hit@1"]-baseline["hit@1"])*100).toFixed(1)} 个百分点</div></div><div class="panel kpi"><div class="kpi-label">错版本 / 错范围 · Top-1</div><div class="kpi-value">${percentage(full["stale_or_wrong_scope@1"])}<small>测试集</small></div><div class="kpi-note">基线 ${percentage(baseline["stale_or_wrong_scope@1"])}，过滤后 ${percentage(full["stale_or_wrong_scope@1"])}</div></div><div class="panel kpi"><div class="kpi-label">相关规则值准确率</div><div class="kpi-value">${percentage(full.rule_value_accuracy)}</div><div class="kpi-note">基于可回答问题中的检索规则值评估</div></div></div>
    <section class="panel benchmark-panel"><div class="panel-heading"><h2>同一测试集上的消融实验</h2><span class="tag blue">CPU / LSA PROFILE</span></div><div class="table-scroll"><table><thead><tr><th>检索链路</th><th>Hit@1</th><th>Hit@3</th><th>MRR@10</th><th>错版本 / 范围</th><th>拒答准确率</th></tr></thead><tbody>${report.results.map(row => `<tr class="${row.mode === "full" ? "best-row" : ""}"><td>${labels[row.mode]}</td><td><div class="bar-cell">${percentage(row["hit@1"])}<div class="bar-track"><div class="bar-fill" style="width:${Number(row["hit@1"])*100}%"></div></div></div></td><td>${percentage(row["hit@3"])}</td><td>${Number(row["mrr@10"]).toFixed(3)}</td><td>${percentage(row["stale_or_wrong_scope@1"])}</td><td>${percentage(row.answerability_accuracy)}</td></tr>`).join("")}</tbody></table></div><div class="benchmark-note"><p>数据来源：仓库已有的 <code>artifacts/eval/metrics.json</code>，页面展示已保存的实验结果，不会即时重新评测。</p><p>${report.dev_queries} 条开发问题用于阈值校准，${report.test_queries} 条测试问题用于报告指标；其中 ${full.answerable_queries} 条可回答问题用于检索指标。基准使用 ${metadata.documents} 份虚构制度，不代表真实企业语料效果。</p><p>这组结果来自 LSA 与特征重排。Qwen 神经模型及 Agent 最终回答没有在这组指标中评测。</p></div></section>
    <div class="method-grid"><div class="method"><span>01 / RETRIEVE</span><h3>混合检索</h3><p>LSA 捕捉语义表达，BM25 保留制度名与精确词，RRF 合并排序。</p></div><div class="method"><span>02 / FILTER</span><h3>先判断适用性</h3><p>按查询日期、地区和员工类型过滤，排除已失效和不适用条款。</p></div><div class="method"><span>03 / VERIFY</span><h3>核对冲突与证据</h3><p>按范围、权威及生效时间解析规则；同级冲突或证据不足时拒答。</p></div><div class="method"><span>04 / TRACE</span><h3>保留引用与来源</h3><p>当前演示使用抽取式回答，可查看原文、版本、检索分数和 trace。</p></div></div>`;
}

async function loadMetadata() {
  try {
    metadata = await requestJSON("/v1/demo");
    $("doc-count").textContent=metadata.documents;
    $("chunk-count").textContent=`${metadata.chunks} 个结构化片段`;
    $("runtime").textContent="浏览器实时检索 · LSA";
    renderEvaluation();
  } catch(error) {$("runtime").textContent="服务连接失败";$("eval-results").innerHTML=errorHTML(error,"metadata");}
}

function navigate(view) {
  const headings = {
    ask:["制度问答","让制度回答，经得起追溯。","选择适用条件，查找有效制度，并核对每条回答的来源。"],
    compare:["版本对比","同一个问题，不同时间的依据。","分别检索两侧有效制度，只比较与问题相关的规则变化。"],
    eval:["评测结果","每一层改进，都有实验依据。","查看混合检索、适用性过滤与重排在同一测试集上的表现。"]
  };
  for(const section of document.querySelectorAll(".view")) section.hidden=section.id !== `view-${view}`;
  for(const button of document.querySelectorAll("[data-view]")) {
    const active=button.dataset.view === view;button.classList.toggle("active",active);
    if(active) button.setAttribute("aria-current","page");else button.removeAttribute("aria-current");
  }
  $("breadcrumb").textContent=headings[view][0];$("page-title").textContent=headings[view][1];$("page-description").textContent=headings[view][2];
  window.scrollTo({top:0,behavior:"instant"});
  if(view === "compare" && !compared){compared=true;compare();}
  if(view === "eval") renderEvaluation();
}
$("ask-form").addEventListener("submit",event => {event.preventDefault();ask();});
$("compare-form").addEventListener("submit",event => {event.preventDefault();compare();});
$("pipeline").addEventListener("change",() => {
  $("mode-help").textContent=["dense","hybrid"].includes($("pipeline").value) ? "实验基线：会包含过期或不适用制度。页面使用当前服务的拒答阈值，不用于复现各方案校准指标。" : "按日期、地区与人群筛选，再根据相关性与权威重排。";
});
document.addEventListener("click",event => {
  const nav=event.target.closest("[data-view]");if(nav) navigate(nav.dataset.view);
  const sample=event.target.closest("[data-example]");if(sample){const context=examples[sample.dataset.example];$("question").value=context.query;$("as-of").value=context.as_of;$("region").value=context.region;$("employee").value=context.employee_type;$("pipeline").value="full";$("pipeline").dispatchEvent(new Event("change"));ask();}
  const citation=event.target.closest("[data-citation]");if(citation){const source=$(citation.dataset.citation);if(source){source.open=true;source.scrollIntoView({behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",block:"center"});source.querySelector("summary").focus();}}
  const retry=event.target.closest("[data-retry]");if(retry) ({ask,compare,metadata:loadMetadata}[retry.dataset.retry])();
});
loadMetadata();
ask();

if(document.modelContext?.registerTool){
  const lifecycle=new AbortController();
  const properties={query:{type:"string",minLength:2,maxLength:1000},region:{type:"string",enum:["CN","GB","ALL"]},employee_type:{type:"string",enum:["full_time","intern","contractor","secure_role","all"]}};
  const validateScope=input=>{
    if(input.region&&!properties.region.enum.includes(input.region))throw new Error("未知地区");
    if(input.employee_type&&!properties.employee_type.enum.includes(input.employee_type))throw new Error("未知员工类型");
  };
  const registrations=[{
    name:"query_policy",title:"查询适用制度",description:"按日期、地区与员工类型检索制度，并更新网页中的回答和证据。",annotations:{readOnlyHint:false,untrustedContentHint:true},
    inputSchema:{type:"object",properties:{...properties,as_of:{type:"string",pattern:"^\\d{4}-\\d{2}-\\d{2}$"}},required:["query","as_of"],additionalProperties:false},
    async execute(input){validateScope(input);(await getEngine()).validate(input);navigate("ask");$("question").value=input.query;$("as-of").value=input.as_of;$("region").value=input.region||"CN";$("employee").value=input.employee_type||"full_time";$("pipeline").value="full";$("pipeline").dispatchEvent(new Event("change"));const result=await ask();if(!result||result.error)throw new Error(result?.error||"查询被新的操作替代");return {answer:result.answer,answerable:result.answerable,citations:result.citations};}
  },{
    name:"compare_policy_versions",title:"比较制度版本",description:"检索两个日期的有效制度，比较相关规则值并更新网页中的两侧证据。",annotations:{readOnlyHint:false,untrustedContentHint:true},
    inputSchema:{type:"object",properties:{...properties,date_a:{type:"string",pattern:"^\\d{4}-\\d{2}-\\d{2}$"},date_b:{type:"string",pattern:"^\\d{4}-\\d{2}-\\d{2}$"}},required:["query","date_a","date_b"],additionalProperties:false},
    async execute(input){validateScope(input);const engine=await getEngine();engine.validate({...input,as_of:input.date_a});engine.validate({...input,as_of:input.date_b});if(input.date_a>input.date_b)throw new Error("较早日期不能晚于较晚日期");compared=true;navigate("compare");$("compare-question").value=input.query;$("date-a").value=input.date_a;$("date-b").value=input.date_b;$("compare-region").value=input.region||"CN";$("compare-employee").value=input.employee_type||"full_time";const result=await compare();if(!result)throw new Error("版本比较未完成");return {comparable:result.comparable,changed_rules:result.changed_rules};}
  }];
  for(const tool of registrations){try{Promise.resolve(document.modelContext.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}}
  window.addEventListener("pagehide",()=>lifecycle.abort(),{once:true});
}
