import express from 'express';
import { createAgentSession, AuthStorage, ModelRegistry, DefaultResourceLoader, SessionManager, SettingsManager } from '@mariozechner/pi-coding-agent';
import { buildPrompt, providerModel } from './prompts.mjs';
const app = express();
app.use(express.json({limit:'256kb'}));
app.get('/health', (_req,res)=>res.json({cloud_configured:Boolean(process.env.ANTHROPIC_API_KEY),gemini_configured:Boolean(process.env.GEMINI_API_KEY),ollama_model:process.env.OLLAMA_MODEL||'lenny-growth:8b',agent_sdk:'Pi Coding Agent 0.73.1'}));
app.post('/generate', async(req,res)=>{
  let session, timer;
  try {
    const {provider, mode, message, sources, history} = req.body;
    if (typeof message !== 'string' || message.length>8000 || !Array.isArray(sources) || sources.length>6 || !Array.isArray(history)) return res.status(400).json({error:'Invalid generation request'});
    const model=providerModel(provider);
    if (provider==='gemini') {
      const systemPrompt=`${buildPrompt(mode)}\n\nThe only valid source identifiers for this request are: ${sources.map(source=>`[${source.id}]`).join(', ')}. Never create another identifier. If no supplied source supports a claim, omit the claim or abstain.`;
      const response=await fetch('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',{
        method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${process.env.GEMINI_API_KEY}`},
        signal:AbortSignal.timeout(Number(process.env.MODEL_TIMEOUT||240)*1000),
        body:JSON.stringify({model:model.id,messages:[{role:'system',content:systemPrompt},{role:'user',content:JSON.stringify({question:message,conversation:history,transcript_excerpts:sources})}],max_tokens:2048,stream:false}),
      });
      let content;
      if (response.ok) {
        const payload=await response.json();
        content=payload?.choices?.[0]?.message?.content;
      }
      if (typeof content!=='string'||!content.trim()) {
        content=`I could not complete a Gemini synthesis right now. Here are the most relevant archive passages for this question:\n\n${sources.slice(0,3).map(source=>`### ${source.title} [${source.id}]\n${source.content.slice(0,700)}`).join('\n\n')}`;
      }
      res.setHeader('Content-Type','application/x-ndjson');res.setHeader('Cache-Control','no-cache');
      res.write(JSON.stringify({type:'token',content})+'\n');res.end(JSON.stringify({type:'done'})+'\n');return;
    }
    const authStorage=AuthStorage.inMemory();
    authStorage.setRuntimeApiKey(provider,provider==='ollama'?'ollama':provider==='gemini'?process.env.GEMINI_API_KEY:process.env.ANTHROPIC_API_KEY);
    const modelRegistry=ModelRegistry.inMemory(authStorage);
    const settingsManager=SettingsManager.inMemory({compaction:{enabled:false},retry:{enabled:false,provider:{timeoutMs:Number(process.env.MODEL_TIMEOUT||240)*1000,maxRetries:0,maxRetryDelayMs:60000}}});
    const resourceLoader=new DefaultResourceLoader({cwd:process.cwd(),agentDir:'/tmp/lenny-agent-isolated',settingsManager,
      noExtensions:true,noSkills:true,noPromptTemplates:true,noThemes:true,noContextFiles:true,
      systemPromptOverride:()=>`${buildPrompt(mode)}\n\nThe only valid source identifiers for this request are: ${sources.map(source=>`[${source.id}]`).join(', ')}. Never create another identifier. If no supplied source supports a claim, omit the claim or abstain.`,appendSystemPromptOverride:()=>[],agentsFilesOverride:()=>({agentsFiles:[]})});
    await resourceLoader.reload();
    ({session}=await createAgentSession({model,authStorage,modelRegistry,settingsManager,resourceLoader,
      tools:[],noTools:'all',thinkingLevel:'off',sessionManager:SessionManager.inMemory()}));
    res.setHeader('Content-Type','application/x-ndjson');
    res.setHeader('Cache-Control','no-cache');
    res.flushHeaders();
    let failure=false; let draft="";
    const emit=(item)=>{if(!res.destroyed) res.write(JSON.stringify(item)+'\n');};
    session.subscribe(event=>{
      if(event.type==='message_update'&&event.assistantMessageEvent.type==='text_delta') {draft+=event.assistantMessageEvent.delta;emit({type:'token',content:event.assistantMessageEvent.delta});}
      if(event.type==='message_end'&&event.message.role==='assistant'&&['error','aborted'].includes(event.message.stopReason)) failure=true;
    });
    res.on('close',()=>{if(!res.writableEnded) void session?.abort();});
    timer=setTimeout(()=>{failure=true;void session.abort();},Number(process.env.MODEL_TIMEOUT||240)*1000);
    await session.prompt(JSON.stringify({question:message,conversation:history,transcript_excerpts:sources}),{expandPromptTemplates:false});
    for(let attempt=0;attempt<2&&!failure;attempt++){
      const count=draft.split(/\s+/).filter(Boolean).length;
      const missing=!/\[S\d+\]/.test(draft)&&!/do not have sufficient|not enough information|cannot answer/i.test(draft);
      const length=mode==='essay'&&(count<1100||count>1400);
      if(!missing&&!length)break;
      emit({type:'status',content:'Checking citations and document length'});
      emit({type:'replace',content:''});draft='';
      await session.prompt(`Revise your previous response. ${missing?'Every factual paragraph must end with an exact source identifier in square brackets, for example [S1]. Do not merely name sources.':''} ${length?`The previous draft had ${count} words. Produce 1,250 words, between 1,100 and 1,400. Expand substantive analysis of supplied evidence, never invent facts.`:''} Output only the complete revised response. If the evidence does not support the request, explicitly say you do not have sufficient information in Lenny's podcast archive.`,{expandPromptTemplates:false});
    }
    if(failure) emit({type:'error',content:'Model unavailable, timed out, or interrupted'});
    else emit({type:'done'});
    res.end();
  } catch(error) {
    console.error(JSON.stringify({event:'agent_error',type:error.constructor.name}));
    if(res.headersSent) res.end(JSON.stringify({type:'error',content:'Model generation failed'})+'\n');
    else res.status(503).json({error:'Model configuration or service unavailable'});
  } finally {clearTimeout(timer);session?.dispose();}
});
app.listen(Number(process.env.PORT||3001),process.env.HOST||'127.0.0.1',()=>console.log(JSON.stringify({event:'agent_started',port:Number(process.env.PORT||3001)})));
