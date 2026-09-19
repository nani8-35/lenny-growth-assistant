import test from 'node:test';
import assert from 'node:assert/strict';
import {providerModel,buildPrompt} from './prompts.mjs';
test('local routing stays local and supports model override',()=>{const m=providerModel('ollama',{OLLAMA_MODEL:'test',OLLAMA_BASE_URL:'http://local:11434'});assert.equal(m.id,'test');assert.equal(m.baseUrl,'http://local:11434/v1');assert.equal(providerModel('ollama',{}).id,'lenny-growth:8b');});
test('missing cloud credential fails without fallback',()=>assert.throws(()=>providerModel('anthropic',{}),/not configured/));
test('Gemini uses the OpenAI-compatible endpoint',()=>{const m=providerModel('gemini',{GEMINI_API_KEY:'test'});assert.equal(m.id,'gemini-3.6-flash');assert.equal(m.baseUrl,'https://generativelanguage.googleapis.com/v1beta/openai');});
test('unknown provider rejected',()=>assert.throws(()=>providerModel('arbitrary',{}),/Unknown/));
test('all skills share grounding and HTML forbids execution',()=>{for(const mode of ['answer','essay','markdown','html']) assert.match(buildPrompt(mode),/ONLY the supplied/);assert.match(buildPrompt('answer'),/Never invent a citation/);assert.match(buildPrompt('html'),/No JavaScript/);assert.match(buildPrompt('essay'),/1,250/);});
