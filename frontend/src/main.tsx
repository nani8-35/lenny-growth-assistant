import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {ArrowUp,ArrowUpRight,BookOpen,Check,ChevronRight,Code2,Download,FileText,Menu,MessageSquare,PanelRightClose,Plus,Search,ShieldCheck,Sparkles,Square,X} from 'lucide-react';
import {api,consumeSSE,type Artifact,type Health,type Message,type Session,type Source} from './api';
import {safeDocument} from './safety';
import './styles.css';
const starters=[{tag:'FIND YOUR FOCUS',q:'How should an early-stage team measure product-market fit?',icon:Search},{tag:'BUILD A GROWTH LOOP',q:'What makes a product-led growth strategy work?',icon:Sparkles},{tag:'KEEP PEOPLE COMING BACK',q:'How can we improve retention before investing in acquisition?',icon:BookOpen}];
function Markdown({text}:{text:string}){return <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{img:props=><span>[Image omitted: {props.alt||"external image"}]</span>,a:props=><a {...props} target="_blank" rel="noreferrer noopener"/>}}>{text}</ReactMarkdown></div>}
function SourceCards({sources}:{sources:Source[]}){return <div className="sources">{sources.map(s=><details key={s.id}><summary><span className="source-number">{s.id}</span><span>{s.guest}<small>{s.timestamp_ref||'Transcript excerpt'}</small></span><ChevronRight size={14}/></summary><p>{s.content}</p><a href={/^https?:\/\//.test(s.source_url)?s.source_url:undefined} target="_blank" rel="noreferrer">{s.title} <ArrowUpRight size={12}/></a></details>)}</div>}
function App(){
 const [sessions,setSessions]=useState<Session[]>([]),[active,setActive]=useState<string|null>(null),[messages,setMessages]=useState<Message[]>([]);
 const [artifacts,setArtifacts]=useState<Artifact[]>([]),[artifact,setArtifact]=useState<Artifact|null>(null),[view,setView]=useState<'preview'|'source'>('preview');
 const [health,setHealth]=useState<Health|null>(null),[input,setInput]=useState(''),[provider,setProvider]=useState('ollama'),[mode,setMode]=useState('answer');
 const [busy,setBusy]=useState(false),[status,setStatus]=useState(''),[error,setError]=useState(''),[warning,setWarning]=useState(''),[sidebar,setSidebar]=useState(false),[system,setSystem]=useState(false);
 const abort=useRef<AbortController|null>(null),end=useRef<HTMLDivElement>(null),scroll=useRef<HTMLDivElement>(null),follow=useRef(true),inputRef=useRef<HTMLTextAreaElement>(null);
 const refresh=()=>{api<Session[]>('/sessions').then(setSessions).catch(()=>{});api<Health>('/health').then(setHealth).catch(()=>setHealth(null));};
 useEffect(()=>{refresh();const saved=localStorage.getItem('lenny-session');if(saved)void select(saved);const t=setInterval(refresh,30000);return()=>clearInterval(t)},[]);
 useEffect(()=>{if(follow.current)end.current?.scrollIntoView({behavior:'instant'});},[messages,status]);
 async function select(id:string){if(busy)return;try{const data=await api<{messages:Message[];artifacts:Artifact[]}>('/sessions/'+id);setActive(id);localStorage.setItem('lenny-session',id);setMessages(data.messages);setArtifacts(data.artifacts);setArtifact(data.artifacts.at(-1)||null);setError('');setWarning('');setSidebar(false)}catch(e){setError((e as Error).message)}}
 function newChat(){if(busy)return;setActive(null);localStorage.removeItem('lenny-session');setMessages([]);setArtifacts([]);setArtifact(null);setInput('');setError('');setWarning('');setSidebar(false);inputRef.current?.focus()}
 async function send(question=input){
  if(busy||!question.trim())return;
  setBusy(true);setError('');setWarning('');setStatus('Starting your request');setInput('');follow.current=true;
  let sid=active;let completed=false;const temp='stream-'+Date.now();
  abort.current=new AbortController();
  try{
   if(!sid){const s=await api<Session>('/sessions',{method:'POST',body:JSON.stringify({title:'New conversation',user_metadata:{client:'local-web'}})});sid=s.id;setActive(s.id);localStorage.setItem('lenny-session',s.id)}
   setMessages(m=>[...m,{id:'user-'+Date.now(),role:'user',content:question,sources:[]},{id:temp,role:'assistant',content:'',sources:[],provider,mode}]);
   const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},signal:abort.current.signal,body:JSON.stringify({session_id:sid,message:question,provider,mode})});
   if(!res.ok){const data=await res.json();throw new Error(data.error?.message||'Request failed')}
   if(!res.body)throw new Error('Streaming is unavailable');
   await consumeSSE(res.body,e=>{
    if(e.type==='status')setStatus(e.content);
    if(e.type==='sources')setMessages(m=>m.map(x=>x.id===temp?{...x,sources:e.sources}:x));
    if(e.type==='replace')setMessages(m=>m.map(x=>x.id===temp?{...x,content:e.content}:x));
    if(e.type==='token')setMessages(m=>m.map(x=>x.id===temp?{...x,content:x.content+e.content}:x));
    if(e.type==='warning')setWarning(e.content);
    if(e.type==='artifact'){setArtifacts(a=>[...a,e.artifact]);setArtifact(e.artifact);setView('preview')}
    if(e.type==='error')throw new Error(e.content+(e.request_id?' Request ID: '+e.request_id:''));
    if(e.type==='done'){completed=true;setStatus('Complete');setMessages(m=>m.map(x=>x.id===temp?{...x,id:e.message_id,status:'complete'}:x))}
   });
   if(!completed)throw new Error('The connection ended before the response was saved. Retry your request.');
  }catch(e){const msg=(e as Error).name==='AbortError'?'Generation stopped. Partial text is not a completed answer.':(e as Error).message;setError(msg);setMessages(m=>m.map(x=>x.id===temp?{...x,status:'failed'}:x));}
  finally{setBusy(false);setStatus('');abort.current=null;refresh()}
 }
 function download(){if(!artifact)return;const content=artifact.artifact_type==='html'?safeDocument(artifact.content):artifact.content;const url=URL.createObjectURL(new Blob([content],{type:artifact.artifact_type==='html'?'text/html':'text/markdown'}));const a=document.createElement('a');a.href=url;a.download='lenny-'+artifact.id.slice(0,8)+(artifact.artifact_type==='html'?'.html':'.md');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 const words=artifact?.content.trim().split(/\s+/).length||0;
 return <div className={'app '+(artifact?'with-artifact':'')}>
  {sidebar&&<button className="overlay" aria-label="Close conversations" onClick={()=>setSidebar(false)}/>}
  <aside className={'sidebar '+(sidebar?'open':'')}>
   <a className="brand" href="#" onClick={e=>{e.preventDefault();newChat()}}><span className="brand-mark">L<span>✳</span></span><span>Lenny<span className="brand-sub">GROWTH ASSISTANT</span></span></a>
   <button className="new-chat" onClick={newChat} disabled={busy}><Plus size={17}/> New conversation <span>↗</span></button>
   <div className="sidebar-label">YOUR WORKSPACE</div><div className="session-list">{sessions.length===0?<p className="empty-sessions">Your conversations will live here.</p>:sessions.map(s=><button key={s.id} className={'session '+(s.id===active?'selected':'')} onClick={()=>select(s.id)} disabled={busy}><MessageSquare size={15}/><span>{s.title}</span></button>)}</div>
   <div className="archive-note"><BookOpen size={18}/><div>Wisdom, with receipts.<p>Every answer starts with the archive.</p></div></div>
   <button className="system-button" onClick={()=>{setSystem(!system);refresh()}}><span className={'dot '+(health?.ready?'good':'')}/><span>{health?.ready?'Local workspace ready':'Check system status'}</span><ChevronRight size={14}/></button>
   <div className="profile"><span>Y</span><div>Your workspace<small>Personal · Local deployment</small></div></div>
  </aside>
  <main className="main">
   <header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" aria-label="Open conversations" onClick={()=>setSidebar(true)}><Menu size={20}/></button><span>Workspace</span><ChevronRight size={13}/><strong>{messages.length?'Conversation':'New conversation'}</strong></div><div className="provider"><span className="dot good"/><select aria-label="Model provider" value={provider} disabled={busy} onChange={e=>setProvider(e.target.value)}><option value="ollama">Ollama · Local</option><option value="anthropic">Claude · Cloud</option></select></div></header>
   {system&&<section className="system-panel"><div><strong>System status</strong><button className="icon-button" aria-label="Close system status" onClick={()=>setSystem(false)}><X size={17}/></button></div><dl>{[['PostgreSQL',health?.database?'Connected':'Unavailable'],['Transcript index',`${health?.episodes||0} episodes · ${health?.chunks||0} passages`],['Ollama',health?.ollama?'Connected':'Unavailable'],['Pi agent',health?.agent?'Connected':'Unavailable'],['Cloud key',health?.cloud_configured?'Configured':'Not configured']].map(([k,v])=><React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl><p>Start Docker and Ollama, then run the setup steps in README if a service is missing.</p></section>}
   <div className="chat-scroll" ref={scroll} onScroll={()=>{const e=scroll.current;if(e)follow.current=e.scrollHeight-e.scrollTop-e.clientHeight<100}}>
    {messages.length===0?<section className="welcome"><div className="eyebrow"><span/> THE LENNY GROWTH ASSISTANT</div><h1>Great advice.<br/><em>Your next move.</em></h1><p className="intro">Turn the best minds in product and growth into<br className="desktop-break"/> a clear path forward. Grounded in Lenny’s Podcast.</p><div className="starter-grid">{starters.map(({tag,q,icon:Icon})=><button className="starter" key={tag} onClick={()=>send(q)} disabled={busy}><Icon size={21}/><span className="starter-tag">{tag}</span><strong>{q}</strong><ArrowUpRight className="starter-arrow" size={18}/></button>)}</div><div className="archive-caption"><span className="tiny-lines">▥</span>{health?.episodes?`${health.episodes} episodes indexed`:'Your podcast research workspace'}<span>·</span>Sources you can trace. Ideas you can use.</div></section>:<div className="messages">{messages.map(m=><article key={m.id} className={'message '+m.role}><div className="message-label">{m.role==='assistant'?<><span className="assistant-mark">✳</span> LENNY <span className="message-model">{m.provider==='anthropic'?'Claude':'Ollama'}</span></>:<>YOU</>}</div>{m.content?<Markdown text={m.content}/>:<div className="thinking"><span/><span/><span/></div>}{m.status==='failed'&&<div className="failed-label">Incomplete response</div>}{m.sources?.length>0&&<SourceCards sources={m.sources}/>} {artifacts.filter(a=>a.message_id===m.id).map(a=><button className="artifact-card" key={a.id} onClick={()=>{setArtifact(a);setView('preview')}}><FileText size={19}/><span>{a.title}<small>{a.artifact_type.toUpperCase()} · Open artifact</small></span><ArrowUpRight size={16}/></button>)}</article>)}<div ref={end}/></div>}
   </div>
   <div className="composer-area">{error&&<div role="alert" className="notice error">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}><X size={15}/></button></div>}{warning&&<div className="notice warning">{warning}</div>}{busy&&<div className="live-status" role="status"><span className="pulse"/>{status}</div>}
    <form className="composer" onSubmit={e=>{e.preventDefault();void send()}}><textarea ref={inputRef} aria-label="Ask a product or growth question" placeholder="What are you working through?" value={input} maxLength={8000} disabled={busy} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send()}}}/><div className="composer-bottom"><div className="mode-tabs">{[['answer','Ask',MessageSquare],['essay','Write an essay',Sparkles],['markdown','Document',FileText],['html','HTML',Code2]].map(([value,label,Icon])=>{const I=Icon as typeof MessageSquare;return <button type="button" key={String(value)} className={mode===value?'active':''} aria-pressed={mode===value} disabled={busy} onClick={()=>setMode(String(value))}><I size={14}/>{String(label)}</button>})}</div>{busy?<button type="button" className="send" aria-label="Stop generation" onClick={()=>abort.current?.abort()}><Square size={16}/></button>:<button className="send" aria-label="Send question" disabled={!input.trim()}><ArrowUp size={20}/></button>}</div></form>
    <div className="composer-note"><ShieldCheck size={12}/>{provider==='ollama'?'Local inference. Your questions stay on this machine.':'Cloud mode. Retrieved excerpts and conversation context are sent to Anthropic.'}<span>Verify important claims.</span></div>
   </div>
  </main>
  {artifact&&<aside className="artifact-pane"><header><div><span className="eyebrow">YOUR ARTIFACT</span><h2>{artifact.title}</h2></div><button className="icon-button" aria-label="Close artifact" onClick={()=>setArtifact(null)}><PanelRightClose size={19}/></button></header><div className="artifact-toolbar"><div><button className={view==='preview'?'active':''} onClick={()=>setView('preview')}>Preview</button><button className={view==='source'?'active':''} onClick={()=>setView('source')}>Source</button></div><button className="icon-button" aria-label="Download artifact" onClick={download}><Download size={17}/></button></div><div className="artifact-content">{view==='source'?<pre>{artifact.content}</pre>:artifact.artifact_type==='html'?<iframe title="Isolated HTML artifact preview" sandbox="" referrerPolicy="no-referrer" srcDoc={safeDocument(artifact.content)}/>:<Markdown text={artifact.content}/>}</div><footer><Check size={13}/>{artifact.artifact_type==='html'?'Isolated static preview · Scripts blocked':`${words.toLocaleString()} words · Markdown document`}</footer></aside>}
 </div>
}
createRoot(document.getElementById('root')!).render(<App/>);
