import DOMPurify from 'dompurify';
export function safeDocument(content:string):string {
  const cleaned=DOMPurify.sanitize(content,{WHOLE_DOCUMENT:true,ADD_TAGS:['style'],
    FORBID_TAGS:['script','iframe','frame','object','embed','form','input','button','textarea','select','link','meta','base','svg','math','video','audio','source'],
    FORBID_ATTR:['src','srcset','action','formaction','ping','poster','background','target']});
  const doc=new DOMParser().parseFromString(cleaned,'text/html');
  doc.querySelectorAll('[href]').forEach(el=>el.removeAttribute('href'));
  // CSS network channels are also blocked by CSP; remove imports/URLs as defense in depth.
  doc.querySelectorAll('style').forEach(el=>{el.textContent=(el.textContent||'').replace(/@import[^;]*;/gi,'').replace(/url\([^)]*\)/gi,'none');});
  doc.querySelectorAll('[style]').forEach(el=>el.setAttribute('style',(el.getAttribute('style')||'').replace(/url\([^)]*\)/gi,'none')));
  const csp=doc.createElement('meta');csp.httpEquiv='Content-Security-Policy';
  csp.content="default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'";
  doc.head.prepend(csp);
  return '<!doctype html>'+doc.documentElement.outerHTML;
}
