import {describe,it,expect} from 'vitest';
import {safeDocument} from './safety';
import {consumeSSE} from './api';
describe('untrusted artifact isolation',()=>{
 it('removes active content and blocks outbound channels',()=>{
  const html=safeDocument('<script>parent.document.body.innerHTML="owned"</script><img src="https://evil.test" onerror="alert(1)"><form action="https://evil.test"><input></form><iframe src="https://evil.test"></iframe><style>@import "https://evil.test";body{background:url(https://evil.test)}</style><h1>Safe heading</h1>');
  const doc=new DOMParser().parseFromString(html,'text/html');
  expect(doc.querySelectorAll('script,iframe,form,input,[onerror],[src]').length).toBe(0);
  expect(html).not.toContain('https://evil.test');
  expect(html).toContain("script-src 'none'");expect(html).toContain('Safe heading');
 });
 it('strips navigation and handles malformed HTML',()=>{const html=safeDocument('<a href="javascript:alert(1)">link</a><svg onload="alert(1)"></svg><meta http-equiv="refresh" content="0;url=https://evil.test">');expect(html).not.toContain('javascript:');expect(html).not.toContain('refresh');expect(html).not.toContain('<svg');});
});
it('SSE parser handles split UTF-8 and frame boundaries',async()=>{
 const bytes=new TextEncoder().encode('data: {"type":"token","content":"Café 🌱"}\n\ndata: {"type":"done"}\n\n');
 const stream=new ReadableStream<Uint8Array>({start(controller){for(let i=0;i<bytes.length;i+=3)controller.enqueue(bytes.slice(i,i+3));controller.close()}});
 const events:any[]=[];await consumeSSE(stream,e=>events.push(e));expect(events).toEqual([{type:'token',content:'Café 🌱'},{type:'done'}]);
});
