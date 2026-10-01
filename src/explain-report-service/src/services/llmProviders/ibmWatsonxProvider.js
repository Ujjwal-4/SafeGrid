const fetch = require('node-fetch');

/**
 * Real IBM watsonx.ai adapter, using IBM Cloud IAM token exchange followed by
 * the watsonx.ai text-generation endpoint. This is IBM's standard, publicly
 * documented GenAI API shape.
 *
 * IMPORTANT: this file was written from IBM's public API docs, not verified
 * against a live call, because this environment has no network path to any
 * ibm.com host. Before switching LLM_PROVIDER=ibm_watsonx in production,
 * run one real request against your project and confirm the response shape
 * still matches `parseResponseText` below — IBM has changed this payload
 * shape across API versions before.
 *
 * Credentials are read ONLY from environment variables (IBM_API_KEY,
 * IBM_PROJECT_ID) — never hard-code a key here or commit one.
 */

let cachedToken = null;
let cachedTokenExpiry = 0;

async function getIamToken(apiKey) {
  if (cachedToken && Date.now() < cachedTokenExpiry - 30_000) {
    return cachedToken;
  }

  const res = await fetch('https://iam.cloud.ibm.com/identity/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
    body: new URLSearchParams({
      grant_type: 'urn:ibm:params:oauth:grant-type:apikey',
      apikey: apiKey
    })
  });

  if (!res.ok) {
    throw new Error(`IBM IAM token exchange failed: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();
  cachedToken = data.access_token;
  cachedTokenExpiry = Date.now() + (data.expires_in || 3600) * 1000;
  return cachedToken;
}

function parseResponseText(data) {
  // watsonx.ai /ml/v1/text/generation returns { results: [{ generated_text }] }
  const text = data && data.results && data.results[0] && data.results[0].generated_text;
  if (!text) throw new Error(`Unexpected watsonx.ai response shape: ${JSON.stringify(data)}`);
  return text.trim();
}

async function generate({ system, user }) {
  const apiKey = process.env.IBM_API_KEY;
  const projectId = process.env.IBM_PROJECT_ID;
  const baseUrl = process.env.IBM_URL || 'https://us-south.ml.cloud.ibm.com';
  const modelId = process.env.IBM_MODEL_ID || 'ibm/granite-13b-instruct-v2';

  if (!apiKey || !projectId) {
    throw new Error(
      'IBM_API_KEY and IBM_PROJECT_ID must be set in the environment to use LLM_PROVIDER=ibm_watsonx'
    );
  }

  const token = await getIamToken(apiKey);

  const res = await fetch(`${baseUrl}/ml/v1/text/generation?version=2024-05-01`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      model_id: modelId,
      project_id: projectId,
      input: `${system}\n\n${user}`,
      parameters: {
        decoding_method: 'greedy',
        max_new_tokens: 400,
        repetition_penalty: 1.1
      }
    })
  });

  if (!res.ok) {
    throw new Error(`watsonx.ai generation call failed: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();
  return parseResponseText(data);
}

module.exports = { generate };
