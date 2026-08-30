export const VECTORS = [
  {
    slug: 'prompt-injection',
    name: 'Prompt Injection',
    short: 'Checkout decision',
    stage: 'Autonomous shopping & checkout',
    accent: 'red' as const,
    stack: 'Qwen3-8B (local) + Gemini 2.5 Flash strategist, MAP-Elites, PyTorch GNN',
  },
  {
    slug: 'token-replay',
    name: 'Token Replay',
    short: 'Consent & token issuance',
    stage: 'Agentic token authorization',
    accent: 'blue' as const,
    stack: 'LightGBM, scikit-learn, reference Zero-Trust Runtime Verifier',
  },
  {
    slug: 'merchant-fraud',
    name: 'Merchant Fraud',
    short: 'Onboarding',
    stage: 'Merchant onboarding review',
    accent: 'amber' as const,
    stack: 'CTGAN (PyTorch), Keras Blue-Team MLP, differentiable surrogate',
  },
  {
    slug: 'graph-fraud',
    name: 'Graph Fraud',
    short: 'Post-transaction settlement',
    stage: 'Mule networks & cross-rail laundering',
    accent: 'violet' as const,
    stack: 'PyTorch Geometric (HGTConv), NetworkX, Gemini 2.5 Flash strategist',
  },
]

export type Accent = (typeof VECTORS)[number]['accent']
