    const err = await resp.text();
    throw new Error(`Pairing eșuat: ${resp.status} ${err}`);
  }
  const data = await resp.json();
  await saveConfig({ device_token: data.device_token, device_id: data.device_id });
  console.log(`\n✅  Conectat! Token salvat în ${CONFIG_PATH}\n`);
  return data.device_token;
}

// ─── Command executors ─────────────────────────────────────────
async function execCommand(type, params) {
  const t0 = Date.now();
  switch (type) {
    case "fs_read": {
      const max = params.max_bytes ?? 200000;
      const buf = await fs.readFile(params.path);
      const truncated = buf.length > max;
      const content = buf.subarray(0, max).toString("utf8");
      return { content, truncated, total_bytes: buf.length, duration_ms: Date.now() - t0 };
    }
    case "fs_write": {
      await fs.mkdir(path.dirname(params.path), { recursive: true });
      await fs.writeFile(params.path, params.content, "utf8");
      return { written: true, path: params.path, bytes: Buffer.byteLength(params.content), duration_ms: Date.now() - t0 };
    }
    case "fs_list": {
      const entries = await fs.readdir(params.path, { withFileTypes: true });
      return {
        path: params.path,
        entries: entries.map((e) => ({
          name: e.name,
