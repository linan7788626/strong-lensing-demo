/* 纯前端协议。浏览器通过 <script> 加载；测试在 Node 里执行同一份函数。 */
(function (root) {
  const storageKey = "cs_static_tokens";

  function base64url(bytes) {
    const arr = ArrayBuffer.isView(bytes)
      ? new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength)
      : new Uint8Array(bytes);
    let text = "";
    for (const b of arr) text += String.fromCharCode(b);
    return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  function randomString() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return base64url(bytes);
  }

  async function sha256(plain) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(plain));
    return base64url(digest);
  }

  function authorizeUrl(cfg, verifierChallenge, state) {
    const url = new URL(cfg.platformApiBase.replace(/\/$/, "") + "/oauth/authorize");
    url.searchParams.set("client_id", cfg.clientId);
    url.searchParams.set("redirect_uri", cfg.redirectUri);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", cfg.scopes);
    url.searchParams.set("state", state);
    url.searchParams.set("code_challenge", verifierChallenge);
    url.searchParams.set("code_challenge_method", "S256");
    return url.toString();
  }

  function demoRecord() {
    return {
      external_id: "static-demo",
      title: "静态模板示例记录",
      played_at: new Date().toISOString(),
      duration_seconds: 30,
      metrics: { score: 1 },
      summary: "来自 static-app",
      payload: { template: "static-app" },
    };
  }

  async function exchange(cfg, body, storage, fetchImpl) {
    const response = await fetchImpl(cfg.platformApiBase.replace(/\/$/, "") + "/oauth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(body),
    });
    const payload = await response.json();
    if (!response.ok) throw payload;
    storage.setItem(storageKey, JSON.stringify(payload));
    return payload;
  }

  async function finishRedirect(search, storage, cfg, fetchImpl) {
    const params = new URLSearchParams(search);
    const code = params.get("code");
    if (!code) return null;
    const state = params.get("state");
    const expected = storage.getItem("cs_oauth_state");
    const verifier = storage.getItem("cs_pkce_verifier");
    // 门户启动只有 ?code=。本页若还留着上一次「登录」写入的 PKCE，不能把它当成授权回调。
    if (!state) {
      storage.removeItem("cs_pkce_verifier");
      storage.removeItem("cs_oauth_state");
      return exchange(cfg, { grant_type: "launch_code", code, client_id: cfg.clientId }, storage, fetchImpl);
    }
    if (!verifier || state !== expected) {
      throw new Error("state 或 PKCE verifier 不匹配");
    }
    storage.removeItem("cs_pkce_verifier");
    storage.removeItem("cs_oauth_state");
    return exchange(
      cfg,
      {
        grant_type: "authorization_code",
        code,
        redirect_uri: cfg.redirectUri,
        client_id: cfg.clientId,
        code_verifier: verifier,
      },
      storage,
      fetchImpl,
    );
  }

  async function api(cfg, path, storage, fetchImpl, options = {}, allowRefresh = true) {
    const saved = storage.getItem(storageKey);
    const tokens = saved ? JSON.parse(saved) : null;
    if (!tokens?.access_token) throw new Error("尚未登录");
    const request = { ...options };
    const asResponse = Boolean(request.raw);
    delete request.raw;
    const response = await fetchImpl(cfg.platformApiBase.replace(/\/$/, "") + path, {
      ...request,
      headers: { ...(request.headers || {}), Authorization: `Bearer ${tokens.access_token}` },
    });
    if (response.status === 401 && allowRefresh && tokens.refresh_token) {
      await exchange(
        cfg,
        { grant_type: "refresh_token", refresh_token: tokens.refresh_token, client_id: cfg.clientId },
        storage,
        fetchImpl,
      );
      return api(cfg, path, storage, fetchImpl, options, false);
    }
    if (asResponse) {
      if (!response.ok) {
        const text = await response.text();
        let payload = text;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch {
          payload = text;
        }
        throw payload || new Error("请求失败");
      }
      return response;
    }
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) throw payload;
    return payload;
  }

  async function writeDemo(cfg, storage, fetchImpl, file) {
    const me = await api(cfg, "/app/me", storage, fetchImpl);
    await api(cfg, "/app/saves/progress", storage, fetchImpl, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: 1, note: "static-app" }),
    });
    const saves = await api(cfg, "/app/saves", storage, fetchImpl);
    const progress = await api(cfg, "/app/saves/progress", storage, fetchImpl);
    await api(cfg, "/app/saves/scratch", storage, fetchImpl, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ temporary: true }),
    });
    await api(cfg, "/app/saves/scratch", storage, fetchImpl, { method: "DELETE" });
    const savesAfterDelete = await api(cfg, "/app/saves", storage, fetchImpl);
    const form = new FormData();
    form.set("record", JSON.stringify(demoRecord()));
    if (file) form.append("attachments", file, file.name);
    else form.append("attachments", new Blob(["来自 static-app\n"], { type: "text/plain" }), "note.txt");
    const record = await api(cfg, "/app/records", storage, fetchImpl, { method: "POST", body: form });
    const records = await api(cfg, "/app/records", storage, fetchImpl);
    const attachmentId = record.attachments && record.attachments[0] && record.attachments[0].id;
    if (!attachmentId) throw new Error("记录没有附件");
    const downloaded = await api(
      cfg,
      `/app/records/${record.id}/attachments/${attachmentId}`,
      storage,
      fetchImpl,
      { raw: true },
    );
    const attachment = await downloaded.text();
    return { me, saves, progress, savesAfterDelete, record, records, attachment };
  }

  async function logout(cfg, storage, fetchImpl) {
    const raw = storage.getItem(storageKey);
    const tokens = raw ? JSON.parse(raw) : null;
    storage.removeItem(storageKey);
    if (!tokens?.access_token) return null;
    const response = await fetchImpl(cfg.platformApiBase.replace(/\/$/, "") + "/app/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    if (response.status === 204) return null;
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) throw payload || new Error("退出失败");
    return payload;
  }

  root.CsClient = {
    storageKey,
    base64url,
    randomString,
    sha256,
    authorizeUrl,
    demoRecord,
    exchange,
    finishRedirect,
    api,
    writeDemo,
    logout,
  };
})(globalThis);
