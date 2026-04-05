# Frontend Integration Guide

**For:** SimOracle Next.js Frontend (`/Users/thikay/simoracle/`)
**Backend:** FastAPI analytics engine (`/Users/thikay/simoracle-backend/`)

---

## Backend URL Configuration

### Development
```typescript
// lib/api.ts or config.ts
export const BACKEND_URL = 'http://127.0.0.1:8000/api/v1';
```

### Production (Vercel)
```typescript
export const BACKEND_URL = 'https://simoracle-backend.vercel.app/api/v1';
// Or your custom domain
export const BACKEND_URL = 'https://api.simoracle.com/api/v1';
```

---

## Core API Functions

### 1. Predictions Management

```typescript
// lib/api/predictions.ts
import { BACKEND_URL } from '@/config';

export async function fetchPredictions(
  oracle?: string,
  status?: 'pending' | 'resolved',
  limit: number = 50,
  offset: number = 0
) {
  const params = new URLSearchParams();
  if (oracle) params.append('oracle', oracle);
  if (status) params.append('status', status);
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await fetch(`${BACKEND_URL}/predictions?${params}`);
  if (!response.ok) throw new Error('Failed to fetch predictions');
  return response.json();
}

export async function fetchPredictionReasoning(predictionId: string) {
  const response = await fetch(
    `${BACKEND_URL}/predictions/${predictionId}/reasoning`
  );
  if (!response.ok) throw new Error('Failed to fetch reasoning');
  return response.json();
}
```

### 2. Analytics Queries

```typescript
// lib/api/analytics.ts
export async function fetchWhaleActivity() {
  const response = await fetch(`${BACKEND_URL}/analytics/whale-activity`);
  if (!response.ok) throw new Error('Failed to fetch whale activity');
  return response.json();
}

export async function fetchArbitrageOpportunities() {
  const response = await fetch(`${BACKEND_URL}/analytics/arbitrage`);
  if (!response.ok) throw new Error('Failed to fetch arbitrage opportunities');
  return response.json();
}

export async function fetchInsiderSignals() {
  const response = await fetch(`${BACKEND_URL}/analytics/insider-signals`);
  if (!response.ok) throw new Error('Failed to fetch insider signals');
  return response.json();
}
```

### 3. Market Data

```typescript
// lib/api/markets.ts
export async function fetchOrderbook(marketId: string) {
  const response = await fetch(
    `${BACKEND_URL}/markets/${marketId}/orderbook`
  );
  if (!response.ok) throw new Error('Failed to fetch orderbook');
  return response.json();
}

export async function fetchUserPositions(userId: string) {
  const response = await fetch(
    `${BACKEND_URL}/user/positions?user_id=${userId}`
  );
  if (!response.ok) throw new Error('Failed to fetch positions');
  return response.json();
}
```

### 4. Exports & Reports

```typescript
// lib/api/exports.ts
export async function exportReasoningJSON(oracle?: string) {
  const params = new URLSearchParams();
  if (oracle) params.append('oracle', oracle);
  params.append('format', 'json');

  const response = await fetch(`${BACKEND_URL}/export/reasoning?${params}`);
  if (!response.ok) throw new Error('Failed to export reasoning');
  return response.json();
}

export async function exportReasoningCSV(oracle?: string) {
  const params = new URLSearchParams();
  if (oracle) params.append('oracle', oracle);
  params.append('format', 'csv');
  params.append('limit', '1000');

  const response = await fetch(`${BACKEND_URL}/export/reasoning?${params}`);
  if (!response.ok) throw new Error('Failed to export CSV');
  return response.text();
}

export async function exportAuditTrail(predictionId: string) {
  const response = await fetch(
    `${BACKEND_URL}/export/audit-trail/${predictionId}?include_raw=true`
  );
  if (!response.ok) throw new Error('Failed to export audit trail');
  return response.json();
}
```

### 5. Health Check

```typescript
// lib/api/health.ts
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (!response.ok) return { status: 'down' };
    return response.json();
  } catch (error) {
    return { status: 'down', error: error.message };
  }
}
```

---

## React Component Examples

### Predictions List

```typescript
// components/PredictionsList.tsx
'use client';

import { useEffect, useState } from 'react';
import { fetchPredictions } from '@/lib/api/predictions';

interface Prediction {
  id: string;
  oracle: string;
  event: string;
  probability: number;
  action: string;
  confidence: number;
  timestamp: string;
  outcome?: string;
}

export function PredictionsList({ oracle }: { oracle?: string }) {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchPredictions(oracle)
      .then(data => setPredictions(data.predictions))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [oracle]);

  if (loading) return <div>Loading predictions...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="grid gap-4">
      {predictions.map(pred => (
        <div
          key={pred.id}
          className="border rounded-lg p-4 hover:shadow-lg transition"
        >
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <h3 className="font-bold text-lg">{pred.event}</h3>
              <p className="text-sm text-gray-600">{pred.oracle}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">
                {(pred.probability * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">probability</p>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
            <div>
              <p className="text-gray-600">Action</p>
              <p className="font-semibold">{pred.action}</p>
            </div>
            <div>
              <p className="text-gray-600">Confidence</p>
              <p className="font-semibold">{pred.confidence}/10</p>
            </div>
            <div>
              <p className="text-gray-600">Status</p>
              <p className="font-semibold">
                {pred.outcome ? `✓ ${pred.outcome}` : '⏳ Pending'}
              </p>
            </div>
          </div>

          <button className="mt-3 text-blue-600 text-sm hover:underline">
            View Reasoning
          </button>
        </div>
      ))}
    </div>
  );
}
```

### Whale Activity Widget

```typescript
// components/WhaleActivityWidget.tsx
'use client';

import { useEffect, useState } from 'react';
import { fetchWhaleActivity } from '@/lib/api/analytics';

export function WhaleActivityWidget() {
  const [whale, setWhale] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWhaleActivity()
      .then(setWhale)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!whale) return <div>No data</div>;

  const scoreColor = 
    whale.score > 70 ? 'text-red-600' :
    whale.score > 40 ? 'text-yellow-600' :
    'text-green-600';

  return (
    <div className="rounded-lg border p-4 bg-gradient-to-r from-slate-50 to-slate-100">
      <h3 className="font-bold text-lg">🐋 Whale Activity</h3>
      
      <div className={`text-4xl font-bold ${scoreColor} my-2`}>
        {whale.score}
      </div>
      
      <p className="text-sm text-gray-600">{whale.description}</p>

      {whale.signals && whale.signals.length > 0 && (
        <div className="mt-3 space-y-2">
          {whale.signals.slice(0, 3).map((signal: any, i: number) => (
            <div key={i} className="text-xs bg-white p-2 rounded">
              <p className="font-semibold">{signal.description}</p>
              <p className="text-gray-600">Confidence: {signal.confidence}%</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Reasoning Chain Display

```typescript
// components/ReasoningChain.tsx
'use client';

import { useEffect, useState } from 'react';
import { fetchPredictionReasoning } from '@/lib/api/predictions';

export function ReasoningChain({ predictionId }: { predictionId: string }) {
  const [reasoning, setReasoning] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPredictionReasoning(predictionId)
      .then(setReasoning)
      .finally(() => setLoading(false));
  }, [predictionId]);

  if (loading) return <div>Loading reasoning...</div>;
  if (!reasoning) return <div>No reasoning available</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Causal Chain</h2>

      {reasoning.causal_chain.map((step: any, i: number) => (
        <div
          key={i}
          className="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50 rounded"
        >
          <div className="flex justify-between items-center">
            <p className="font-semibold">{step.model}</p>
            <p className="text-xs text-gray-600">{step.timestamp}</p>
          </div>

          <div className="mt-2 space-y-2 text-sm">
            <div>
              <p className="text-gray-600">Primary Catalyst</p>
              <p className="font-medium">{step.catalyst_primary}</p>
            </div>

            {step.catalyst_secondary && (
              <div>
                <p className="text-gray-600">Secondary Catalyst</p>
                <p className="font-medium">{step.catalyst_secondary}</p>
              </div>
            )}

            {step.confidence_driver && (
              <div>
                <p className="text-gray-600">Confidence Driver</p>
                <p className="font-medium">{step.confidence_driver}</p>
              </div>
            )}

            {step.data_sources && step.data_sources.length > 0 && (
              <div>
                <p className="text-gray-600">Sources</p>
                <ul className="list-disc list-inside text-xs">
                  {step.data_sources.map((src: string, j: number) => (
                    <li key={j}>{src}</li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-xs font-semibold text-blue-600">
              Status: {step.consensus_status}
            </p>
          </div>
        </div>
      ))}

      <div className="bg-gray-100 p-3 rounded text-sm">
        <p className="font-semibold">Model Consensus: {reasoning.model_consensus}</p>
        <p className="text-gray-600 mt-1">{reasoning.reasoning_summary}</p>
      </div>
    </div>
  );
}
```

### Arbitrage Opportunities

```typescript
// components/ArbitrageOpportunities.tsx
'use client';

import { useEffect, useState } from 'react';
import { fetchArbitrageOpportunities } from '@/lib/api/analytics';

export function ArbitrageOpportunities() {
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchArbitrageOpportunities()
      .then(data => setOpportunities(data.opportunities || []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading opportunities...</div>;
  if (opportunities.length === 0) return <div>No arbitrage opportunities</div>;

  return (
    <div className="space-y-3">
      <h3 className="font-bold text-lg">💰 Arbitrage Opportunities</h3>

      {opportunities.map((opp: any) => (
        <div
          key={`${opp.platform1}-${opp.platform2}`}
          className="border rounded p-3 bg-green-50"
        >
          <div className="flex justify-between items-center">
            <p className="font-semibold">
              {opp.platform1} vs {opp.platform2}
            </p>
            <p className="text-green-600 font-bold">{opp.spread_pct.toFixed(2)}%</p>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm mt-2">
            <div>
              <p className="text-gray-600">{opp.platform1}</p>
              <p className="font-semibold">${opp.price1.toFixed(4)}</p>
            </div>
            <div>
              <p className="text-gray-600">{opp.platform2}</p>
              <p className="font-semibold">${opp.price2.toFixed(4)}</p>
            </div>
          </div>

          <p className="text-xs text-gray-600 mt-2">
            Est. Profit: ${opp.estimated_profit_usd.toFixed(2)}
          </p>
          <p className="text-xs text-gray-600">
            Action: {opp.action}
          </p>
        </div>
      ))}
    </div>
  );
}
```

---

## Page Integration

### Dashboard Page (`app/page.tsx` or `app/dashboard/page.tsx`)

```typescript
'use client';

import { PredictionsList } from '@/components/PredictionsList';
import { WhaleActivityWidget } from '@/components/WhaleActivityWidget';
import { ArbitrageOpportunities } from '@/components/ArbitrageOpportunities';

export default function Dashboard() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
      {/* Main content */}
      <div className="lg:col-span-2">
        <h1 className="text-3xl font-bold mb-6">Live Predictions</h1>
        <PredictionsList />
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        <WhaleActivityWidget />
        <ArbitrageOpportunities />
      </div>
    </div>
  );
}
```

### Predictions Detail Page (`app/predictions/[id]/page.tsx`)

```typescript
'use client';

import { useParams } from 'next/navigation';
import { fetchPredictions } from '@/lib/api/predictions';
import { ReasoningChain } from '@/components/ReasoningChain';
import { useState, useEffect } from 'react';

export default function PredictionDetail() {
  const params = useParams();
  const predictionId = params.id as string;
  const [prediction, setPrediction] = useState<any>(null);

  useEffect(() => {
    // In real code, fetch specific prediction
    fetchPredictions().then(data => {
      const pred = data.predictions.find((p: any) => p.id === predictionId);
      setPrediction(pred);
    });
  }, [predictionId]);

  if (!prediction) return <div>Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-2">{prediction.event}</h1>
      <p className="text-gray-600 mb-6">
        {prediction.oracle} • {prediction.timestamp}
      </p>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <div>
          <p className="text-gray-600">Probability</p>
          <p className="text-3xl font-bold">
            {(prediction.probability * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-gray-600">Confidence</p>
          <p className="text-3xl font-bold">{prediction.confidence}/10</p>
        </div>
      </div>

      <ReasoningChain predictionId={predictionId} />
    </div>
  );
}
```

---

## Environment Setup

### `.env.local` (Frontend)

```env
# Backend URL
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000/api/v1

# Or for production
# NEXT_PUBLIC_BACKEND_URL=https://api.simoracle.com/api/v1
```

### Update `config.ts`

```typescript
export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000/api/v1';
```

---

## Error Handling

```typescript
// lib/api/errors.ts
export class BackendError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'BackendError';
  }
}

export async function fetchWithErrorHandling(url: string) {
  const response = await fetch(url);
  
  if (!response.ok) {
    const error = await response.json();
    throw new BackendError(
      response.status,
      error.detail || error.error || 'Unknown error'
    );
  }
  
  return response.json();
}
```

---

## Polling & Real-Time (Future)

### WebSocket Support (After Week 1)

```typescript
// lib/api/websocket.ts
export function connectPredictionStream(onUpdate: (pred: any) => void) {
  const ws = new WebSocket('ws://127.0.0.1:8000/ws/predictions');
  
  ws.onmessage = (event) => {
    const prediction = JSON.parse(event.data);
    onUpdate(prediction);
  };
  
  return ws;
}
```

---

## Testing API Calls

```bash
# Terminal
curl http://localhost:8000/api/v1/predictions

# Or in browser console
fetch('http://localhost:8000/api/v1/predictions')
  .then(r => r.json())
  .then(data => console.log(data.predictions))
```

---

## Troubleshooting

### CORS Errors
```
Access to fetch at 'http://localhost:8000/api/v1/predictions' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Fix:** Backend CORS is enabled for all origins. Check:
1. Backend is running: `curl http://localhost:8000/`
2. URL is correct in frontend config

### "Cannot GET /api/v1"

**Fix:** Make sure to include `/api/v1` prefix in all URLs. Backend routes are at `/api/v1/predictions`, not `/predictions`.

### Network Timeout

**Fix:** Backend takes 10+ seconds to start up. Wait for:
```
✨ SimOracle Backend is running!
```

---

## Performance Tips

1. **Cache predictions** in React state to avoid re-fetching
2. **Debounce analytics queries** (no need to fetch every keystroke)
3. **Paginate predictions** (use limit=50, offset=0)
4. **Export as CSV** for large reports (faster than JSON)

---

## Next Steps

1. Copy API functions from this guide into `/Users/thikay/simoracle/lib/api/`
2. Create React components for predictions, whale activity, arbitrage
3. Update dashboard to use real data
4. Test with backend running on http://localhost:8000
5. Deploy backend to Vercel before production launch

---

**Frontend Code Ready ✅**
**Backend Code Ready ✅**
**Integration Guide Complete ✅**

Ready to wire together and launch!
