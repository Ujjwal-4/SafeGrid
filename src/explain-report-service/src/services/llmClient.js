const mockProvider = require('./llmProviders/mockProvider');
const ibmWatsonxProvider = require('./llmProviders/ibmWatsonxProvider');

/**
 * Single entry point the rest of the app calls. Adding or swapping a provider
 * means editing this map only — nothing else in the codebase knows or cares
 * which provider is active.
 */
const PROVIDERS = {
  mock: mockProvider,
  ibm_watsonx: ibmWatsonxProvider
};

async function generateJson({ system, user }) {
  const providerName = process.env.LLM_PROVIDER || 'mock';
  const provider = PROVIDERS[providerName];
  if (!provider) {
    throw new Error(`Unknown LLM_PROVIDER "${providerName}". Valid options: ${Object.keys(PROVIDERS).join(', ')}`);
  }

  const raw = await provider.generate({ system, user });

  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error(`LLM provider "${providerName}" returned non-JSON output: ${raw}`);
  }
}

module.exports = { generateJson };
