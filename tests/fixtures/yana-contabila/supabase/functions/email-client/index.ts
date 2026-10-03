  if (!data) throw new Error('No email account configured');
  const password = await decryptPassword(data.encrypted_password, data.encryption_iv);
  return { ...data, _password: password };
}

function buildImap(acct: any) {
  return new ImapFlow({
    host: acct.imap_host,
    port: acct.imap_port,
    secure: acct.imap_use_ssl,
    auth: { user: acct.username, pass: acct._password },
    logger: false,
    tls: { rejectUnauthorized: false }, // velcont: self-signed accepted
  });
}
function buildSmtp(acct: any) {
  return nodemailer.createTransport({
    host: acct.smtp_host,
    port: acct.smtp_port,
    secure: acct.smtp_use_ssl,
    auth: { user: acct.username, pass: acct._password },
    tls: { rejectUnauthorized: false },
  });
}

// ---------- handlers ----------
async function actionTest(payload: any) {
  // Encrypt before saving — but first verify by attempting login
  const tmp = {
    imap_host: payload.imap_host,
    imap_port: payload.imap_port,
