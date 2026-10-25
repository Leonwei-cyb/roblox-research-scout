# Query pack: Multiple ChatGPT web workers \(browser-session orchestration, not API-only\)

Problem-first GitHub search, one bounded run. Not full GitHub coverage: GitHub search returns at most 15 results per query here, ranked by GitHub's own relevance.

- Run: 2026-10-25T11:52:04Z (local)
- API calls: 47 total (graphql 7, rest 40)
- Distinct repos found: 236; inspected: 12

## Rediscovery check (known repos were NOT used as search input)

- Xalzeroph/Charterion: found by queries s1, not inspected
- megamen32/chatgpt-multi: found by queries s1, not inspected
- paritoshv/multi-llm-web-orchestrator: **not found** by this run

## Ranked candidates

| # | Repo @ SHA | Mode | Pack verdict | Score | Why |
|---:|---|---|---|---:|---|
| 1 | [SillySerpent/Dichrome](https://github.com/SillySerpent/Dichrome/tree/8fac1617d1352f62ecf1e32f3ccc8afe690946b6) @ 8fac161 | mixed | needs-test | 115 | drives browser sessions but also calls model APIs; check which path Leon would reuse. browser automation dependency: @​playwright/test; browser extension manifest targets chat sites \(manifest.json\); references chat web ap |
| 2 | [TED-H-com/multi-ai-chat](https://github.com/TED-H-com/multi-ai-chat/tree/1e90319bb4a62d3366739e23701cda5732d5f2b8) @ 1e90319 | browser-session | needs-test | 105 | browser-session orchestration evidence found; needs a pinned source-level reuse test. browser extension manifest targets chat sites \(public/manifest.json\); references chat web apps: chat.openai.com, chatgpt.com, claude.a |
| 3 | [axtonliu/ai-roundtable](https://github.com/axtonliu/ai-roundtable/tree/210a212f8c9111cea01201187fa94d1c9ad54338) @ 210a212 | browser-session | needs-test | 100 | browser-session orchestration evidence found; needs a pinned source-level reuse test. browser extension manifest targets chat sites \(manifest.json\); references chat web apps: chat.openai.com, chatgpt.com, claude.ai, gemi |
| 4 | [creosB/AI-Side-Panel-Extension](https://github.com/creosB/AI-Side-Panel-Extension/tree/e3935eb3342523f9a1bf259edda8f80dd8bc5fdd) @ e3935eb | browser-session | reject | 95 | no license: all rights reserved, ideas only, no code reuse. browser extension manifest targets chat sites \(Source/manifest.json\); references chat web apps: chat.openai.com, chatgpt.com, claude.ai, gemini.google.com; cont |
| 5 | [Veverke/bAInder](https://github.com/Veverke/bAInder/tree/ed22774951480303c8abfd79a6eb882b793c7411) @ ed22774 | browser-session | needs-test | 95 | browser-session orchestration evidence found; needs a pinned source-level reuse test. browser automation dependency: @​playwright/test; browser extension manifest targets chat sites \(manifest.json\); references chat web ap |
| 6 | [NateBJones-Projects/OB1](https://github.com/NateBJones-Projects/OB1/tree/238df6cefd307745d1fe49d10b96797903bf25ac) @ 238df6c | browser-session | needs-test | 90 | browser-session orchestration evidence found; needs a pinned source-level reuse test. browser extension manifest targets chat sites \(integrations/chrome-capture-extension/manifest.json\); references chat web apps: chat.op |
| 7 | [Robbings/chatgpt-graph-navigator](https://github.com/Robbings/chatgpt-graph-navigator/tree/a616cefd3fb6764ad25f0d50417fbebe14156660) @ a616cef | browser-session | reject | 90 | no license: all rights reserved, ideas only, no code reuse. browser extension manifest targets chat sites \(manifest.json\); references chat web apps: chat.openai.com, chatgpt.com; content scripts on chat sites |
| 8 | [keyonzeng/prompt\_ark](https://github.com/keyonzeng/prompt_ark/tree/8d4c1b36fd11bc0cf653c3b95cbca276c9c95ccb) @ 8d4c1b3 | mixed | reject | 85 | no license: all rights reserved, ideas only, no code reuse. browser extension manifest targets chat sites \(manifest.json\); references chat web apps: chat.openai.com, chatgpt.com, claude.ai, gemini.google.com; content scr |
| 9 | [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/6c16b23f1bacd0fdf240bb5141ef45e59e82c306) @ 6c16b23 | mixed | needs-test | 85 | drives browser sessions but also calls model APIs; check which path Leon would reuse. browser automation dependency: playwright; authenticated web session wording |
| 10 | [totec448-spec/chat-on-steroids](https://github.com/totec448-spec/chat-on-steroids/tree/a35ecb40b4bc217b23668f71f36d432bc32a0861) @ a35ecb4 | mixed | needs-test | 85 | drives browser sessions but also calls model APIs; check which path Leon would reuse. browser extension manifest targets chat sites \(extension/manifest.json\); references chat web apps: chat.openai.com, chatgpt.com; conte |
| 11 | [ollama/ollama](https://github.com/ollama/ollama/tree/d44c2581904a98430e348d89cc2af1529b1808a0) @ d44c258 | unknown | reject | 50 | no evidence of browser-session orchestration in README, manifests or key source. no signals |
| 12 | [kyrolabs/awesome-agents](https://github.com/kyrolabs/awesome-agents/tree/1c896ce92780416ce937c330d8205ee52a78d112) @ 1c896ce | unknown | reject | 40 | no license: all rights reserved, ideas only, no code reuse. no signals |

## Searches

- pack:multi-chatgpt-web-workers:a:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:a:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:b:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:b:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:c:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:c:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:d:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:d:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:e:strict: ok (15 results)
- pack:multi-chatgpt-web-workers:e:relaxed: ok (15 results)
- pack:multi-chatgpt-web-workers:f:strict: deferred search budget low
- pack:multi-chatgpt-web-workers:f:relaxed: deferred search budget low
- pack:multi-chatgpt-web-workers:g:strict: deferred search budget low
- pack:multi-chatgpt-web-workers:g:relaxed: deferred search budget low
- pack:multi-chatgpt-web-workers:s1:source: ok (50 results)
- pack:multi-chatgpt-web-workers:s2:source: ok (50 results)
- pack:multi-chatgpt-web-workers:s3:source: ok (50 results)

Verdicts are pack-specific. Only a tested review in findings/reviews can make anything adopt.
