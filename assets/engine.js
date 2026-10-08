/* Browser port of the VeriPolicy CPU/LSA retrieval, reranking and answer pipeline. */
export class PolicyEngine {
  constructor(model,projection,vectors,benchmark) {
    this.model=model;this.projection=projection;this.vectors=vectors;this.benchmark=benchmark;
    this.chunks=model.chunks;this.dimensions=model.dimensions;
    this.vocabulary=new Map(model.vocabulary.map((term,index)=>[term,index]));
    this.ruleTokens=new Map();
    this.chunkTokens=this.chunks.map(chunk=>this.tokenSet(chunk.retrieval_text));
    this.headingTokens=this.chunks.map(chunk=>this.tokenSet(chunk.heading));
  }
  static async load(base=new URL(".",import.meta.url).href.replace(/\/$/,"")) {
    const read=async(file,binary=false)=>{const response=await fetch(`${base}/${file}`);if(!response.ok)throw new Error("检索资源加载失败，请刷新重试。");return binary ? response.arrayBuffer() : response.json();};
    const [model,projection,vectors,benchmark]=await Promise.all([read("model.json"),read("projection.bin",true),read("vectors.bin",true),read("benchmark.json")]);
    return new PolicyEngine(model,new Float64Array(projection),new Float64Array(vectors),benchmark);
  }
  normalize(text){return text.normalize("NFKC").toLowerCase().replace(/\s+/g," ").trim();}
  expand(text){const normalized=this.normalize(text), additions=[];for(const [phrase,aliases] of Object.entries(this.model.aliases))if(normalized.includes(this.normalize(phrase)))additions.push(...aliases);return additions.length ? normalized+" "+[...new Set(additions)].join(" ") : normalized;}
  tokenize(text,expand=false){text=expand ? this.expand(text) : this.normalize(text);const latin=text.match(/[a-z]+(?:[-_][a-z]+)*|\d+(?:\.\d+)?/g)||[],chinese=[];for(const run of text.match(/[\u3400-\u9fff]+/g)||[]){chinese.push(...run);for(let i=0;i<run.length-1;i++)chinese.push(run.slice(i,i+2));if(run.length<=8)chinese.push(run);}return [...latin,...chinese];}
  tokenSet(text,expand=false){return new Set(this.tokenize(text,expand).filter(t=>t.trim().length>1||/^\d+$/.test(t)));}
  overlap(queryTokens,documentTokens){let shared=0;for(const t of queryTokens)if(documentTokens.has(t))shared++;return [shared/Math.max(queryTokens.size,1),shared/Math.max(queryTokens.size+documentTokens.size-shared,1)];}
  denseScores(query){
    const chars=Array.from(query.toLowerCase().replace(/\s{2,}/g," ")),counts=new Map();
    for(let length=2;length<=4;length++)for(let i=0;i<=chars.length-length;i++){const index=this.vocabulary.get(chars.slice(i,i+length).join(""));if(index!==undefined)counts.set(index,(counts.get(index)||0)+1);}
    const vector=new Float64Array(this.dimensions);
    for(const [index,count] of [...counts.entries()].sort((a,b)=>a[0]-b[0])){const weight=(1+Math.log(count))*this.model.idf[index],offset=index*this.dimensions;for(let d=0;d<this.dimensions;d++)vector[d]+=weight*this.projection[offset+d];}
    const norm=Math.hypot(...vector);if(norm)for(let d=0;d<this.dimensions;d++)vector[d]/=norm;
    return this.chunks.map((_,index)=>{let score=0;const offset=index*this.dimensions;for(let d=0;d<this.dimensions;d++)score+=this.vectors[offset+d]*vector[d];return score;});
  }
  bm25Scores(query){const m=this.model.bm25,terms=this.tokenize(this.expand(query),true);return m.frequencies.map((frequency,index)=>{let score=0;const lengthNorm=1-m.b+m.b*m.lengths[index]/Math.max(m.average_length,1);for(const term of terms){const count=frequency[term]||0;if(count)score+=(m.idf[term]||0)*count*(m.k1+1)/(count+m.k1*lengthNorm);}return score;});}
  applicable(chunk,context){return context.as_of>=chunk.effective_from&&(!chunk.effective_to||context.as_of<=chunk.effective_to)&&(chunk.regions.includes("ALL")||chunk.regions.includes(context.region))&&(chunk.employee_types.includes("all")||chunk.employee_types.includes(context.employee_type));}
  specificity(chunk,context){const region=context.region!=="ALL"&&chunk.regions.includes(context.region)?1:chunk.regions.includes("ALL")?.35:0,employee=context.employee_type!=="all"&&chunk.employee_types.includes(context.employee_type)?1:chunk.employee_types.includes("all")?.35:0;return (region+employee)/2;}
  precedence(chunk,context){return [this.specificity(chunk,context),chunk.authority,Date.parse(chunk.effective_from)];}
  comparePriority(a,b){for(let i=0;i<a.length;i++)if(a[i]!==b[i])return b[i]-a[i];return 0;}
  minmax(values){const low=Math.min(...values),high=Math.max(...values);return values.map(v=>high-low<1e-12 ? high>0?1:0 : (v-low)/(high-low));}
  retrieve(context,mode="full",topK=5){
    const useFilter=["hybrid_temporal","full"].includes(mode),allowed=this.chunks.map((_,i)=>i).filter(i=>!useFilter||this.applicable(this.chunks[i],context));if(!allowed.length)return [];
    const dense=this.denseScores(context.query),bm25=this.bm25Scores(context.query),denseRanks={},bm25Ranks={};
    [...allowed].sort((a,b)=>dense[b]-dense[a]).forEach((index,rank)=>denseRanks[index]=rank+1);
    [...allowed].sort((a,b)=>bm25[b]-bm25[a]).forEach((index,rank)=>bm25Ranks[index]=rank+1);
    const score=index=>mode==="dense"?dense[index]:.55/(60+denseRanks[index])+.45/(60+bm25Ranks[index]);
    let hits=[...allowed].sort((a,b)=>score(b)-score(a)).slice(0,mode==="full"?Math.max(topK,25):topK).map((index,rank)=>({chunk:this.chunks[index],index,rank:rank+1,score:score(index),signals:{dense:dense[index],bm25:bm25[index],dense_rank:denseRanks[index],bm25_rank:bm25Ranks[index],rrf:mode==="dense"?0:score(index)}}));
    if(mode==="full"){
      const normalizedDense=this.minmax(hits.map(h=>h.signals.dense)),normalizedSparse=this.minmax(hits.map(h=>h.signals.bm25)),queryTokens=this.tokenSet(context.query,true),normalizedQuery=this.normalize(context.query);
      hits=hits.map((hit,index)=>{
        const [coverage,jaccard]=this.overlap(queryTokens,this.chunkTokens[hit.index]),[headingCoverage]=this.overlap(queryTokens,this.headingTokens[hit.index]);let ruleCoverage=0,phraseBonus=0;
        for(const rule of hit.chunk.rules){const text=[rule.key,rule.label||"",rule.statement||"",(rule.aliases||[]).join(" ")].join(" ");ruleCoverage=Math.max(ruleCoverage,this.overlap(queryTokens,this.tokenSet(text))[0]);if([rule.label||"",...(rule.aliases||[])].some(phrase=>this.normalize(phrase).length>=2&&normalizedQuery.includes(this.normalize(phrase))))phraseBonus=1;}
        const specificity=this.specificity(hit.chunk,context),authority=Math.min(Math.max(hit.chunk.authority/100,0),1),baseRank=1/Math.max(hit.rank,1);
        const score=.20*normalizedDense[index]+.16*normalizedSparse[index]+.12*coverage+.03*jaccard+.06*headingCoverage+.15*ruleCoverage+.15*phraseBonus+.05*specificity+.02*authority+.06*baseRank;
        return {...hit,score,signals:{...hit.signals,coverage,jaccard,heading_coverage:headingCoverage,rule_coverage:ruleCoverage,rule_phrase_bonus:phraseBonus,scope_specificity:specificity,authority,base_rank:baseRank,rerank:score}};
      }).sort((a,b)=>b.score-a.score).slice(0,topK);
    }
    return hits.map((hit,rank)=>({...hit,rank:rank+1}));
  }
  relevantKeys(query,hits){const tokens=this.tokenSet(query,true),scored=[];for(const hit of hits)for(const rule of hit.chunk.rules){const ruleTokens=this.tokenSet(`${rule.key} ${rule.label||rule.key} ${(rule.aliases||[]).join(" ")}`,true);scored.push([this.overlap(tokens,ruleTokens)[0],String(rule.key)]);}scored.sort((a,b)=>b[0]-a[0]||(b[1]>a[1]?1:b[1]<a[1]?-1:0));if(!scored.length||scored[0][0]<=0)return [];return [...new Set(scored.filter(row=>row[0]>=scored[0][0]*.8).map(row=>row[1]))];}
  conflicts(hits,context){const groups=new Map(),conflicts=[],resolved={};for(const hit of hits)for(const rule of hit.chunk.rules){const key=String(rule.key);if(!groups.has(key))groups.set(key,[]);groups.get(key).push({hit,rule});}
    for(const [key,candidates] of groups){const values=[...new Set(candidates.map(c=>String(c.rule.value)))].sort();candidates.sort((a,b)=>this.comparePriority(this.precedence(a.hit.chunk,context),this.precedence(b.hit.chunk,context)));const winner=candidates[0],value=String(winner.rule.value);resolved[key]=[value,winner.hit.chunk.chunk_id];if(values.length<=1)continue;const topPriority=this.precedence(winner.hit.chunk,context),tiedValues=new Set(candidates.filter(c=>this.comparePriority(this.precedence(c.hit.chunk,context),topPriority)===0).map(c=>String(c.rule.value))),unresolved=tiedValues.size>1;conflicts.push({rule_key:key,status:unresolved?"unresolved":"resolved_by_precedence",values,source_ids:candidates.map(c=>c.hit.chunk.chunk_id),selected_source_id:unresolved?null:winner.hit.chunk.chunk_id,reason:unresolved?"Equal-precedence active sources disagree; human review required.":"Selected by scope specificity, authority, then effective date."});if(unresolved)delete resolved[key];}return {conflicts,resolved};
  }
  confidence(hits){if(!hits.length)return 0;const top=hits[0],s=top.signals,dense=Math.max(0,Math.min(1,(s.dense+1)/2)),bm25=1-Math.exp(-Math.max(s.bm25,0)/5),margin=hits.length>1?1-Math.exp(-6*Math.max(0,top.score-hits[1].score)):.5;return Math.max(0,Math.min(1,.22*(s.coverage||0)+.12*dense+.12*bm25+.18*(s.rule_coverage||0)+.20*(s.rule_phrase_bonus||0)+.08*margin+.08*(top.chunk.rules.length?1:0)));}
  serializeHit(hit){const c=hit.chunk;return {rank:hit.rank,score:hit.score,chunk_id:c.chunk_id,doc_id:c.doc_id,title:c.title,heading:c.heading,version:c.version,effective_from:c.effective_from,effective_to:c.effective_to,regions:c.regions,employee_types:c.employee_types,authority:c.authority,rules:c.rules,signals:hit.signals,text:c.text};}
  validate(request){if(typeof request.query!=="string"||request.query.trim().length<2||request.query.length>1000)throw new Error("请输入 2–1000 个字符的问题。");if(!/^\d{4}-\d{2}-\d{2}$/.test(request.as_of)||!Number.isFinite(Date.parse(request.as_of))||new Date(request.as_of).toISOString().slice(0,10)!==request.as_of)throw new Error("请填写有效的查询日期。");if(!["dense","hybrid","hybrid_temporal","full"].includes(request.mode||"full"))throw new Error("未知检索方案。");return {...request,query:request.query.trim(),region:(request.region||"ALL").toUpperCase().trim(),employee_type:(request.employee_type||"all").toLowerCase().trim()};}
  ask(request){const started=performance.now(),context=this.validate(request),mode=context.mode||"full",hits=this.retrieve(context,mode,request.top_k||5),{conflicts,resolved}=this.conflicts(hits,context),confidence=this.confidence(hits),keys=this.relevantKeys(context.query,hits),unresolved=conflicts.some(c=>c.status==="unresolved"&&(!keys.length||keys.includes(c.rule_key)));let answerable=hits.length>0&&confidence>=this.model.threshold&&!unresolved,answer="",citations=[];
    if(!answerable)answer=unresolved?"检测到同等优先级的有效制度存在冲突，系统已停止作答并建议人工确认。":"现有制度中没有找到置信度足够的证据，建议补充问题或转人工确认。";
    else{for(const key of keys){if(!resolved[key])continue;const [value,id]=resolved[key];const hit=hits.find(h=>h.chunk.chunk_id===id),rule=hit?.chunk.rules.find(r=>String(r.key)===key);if(rule){answer=`${rule.statement||`适用值为 ${value}`} [${id}]`;citations=[id];break;}}if(!answer){const top=hits[0],excerpt=top.chunk.text.split(/(?<=[。！？.!?])\s*/).map(s=>s.trim()).filter(Boolean).slice(0,2).join("");answer=`${excerpt} [${top.chunk.chunk_id}]`;citations=[top.chunk.chunk_id];}}
    return {query:context.query,answer,answerable,confidence,citations,hits:hits.map(h=>this.serializeHit(h)),conflicts,latency_ms:performance.now()-started,mode,trace_id:globalThis.crypto?.randomUUID?.().replace(/-/g,"")||`${Date.now()}`};
  }
  compare(request){const {query,date_a,date_b,region="CN",employee_type="full_time"}=request;if(date_a>date_b)throw new Error("较早日期不能晚于较晚日期");const contextA={query,as_of:date_a,region,employee_type,mode:"full"},contextB={...contextA,as_of:date_b},answerA=this.ask(contextA),answerB=this.ask(contextB),hitsA=this.retrieve(contextA),hitsB=this.retrieve(contextB),keys=new Set([...this.relevantKeys(query,hitsA),...this.relevantKeys(query,hitsB)]);
    const collect=(hits,context)=>{const {resolved}=this.conflicts(hits,context),rules={};for(const hit of hits)for(const rule of hit.chunk.rules){const key=String(rule.key);if(keys.has(key)&&resolved[key]?.[0]===String(rule.value)&&resolved[key]?.[1]===hit.chunk.chunk_id)rules[key]=[{value:String(rule.value),citation_id:hit.chunk.chunk_id,statement:rule.statement||"",label:rule.label||key}];}return rules;};
    const rulesA=collect(hitsA,contextA),rulesB=collect(hitsB,contextB),comparable=answerA.answerable&&answerB.answerable&&keys.size>0,changed={};if(comparable)for(const key of [...new Set([...Object.keys(rulesA),...Object.keys(rulesB)])].sort())if((rulesA[key]?.[0]?.value??null)!==(rulesB[key]?.[0]?.value??null))changed[key]={before:rulesA[key]||[],after:rulesB[key]||[]};return {query,date_a,date_b,changed_rules:changed,comparable,reason:comparable?"已按问题相关规则、适用范围及权威优先级比较。":"至少一侧证据不足或存在未决冲突，无法可靠比较。",answer_a:answerA,answer_b:answerB,evidence_a:answerA.hits,evidence_b:answerB.hits};
  }
  info(){return {documents:new Set(this.chunks.map(c=>c.doc_id)).size,chunks:this.chunks.length,threshold:this.model.threshold,dense_backend:"BrowserLSA",reranker:"FeatureReranker",benchmark:this.benchmark};}
}
